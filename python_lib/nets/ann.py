import torch
import torch.nn as nn
import numpy as np
import time


def compute_stats(x, loss, log_prob, energy, beta, model, step=0, ifprint=True, times={}):
    # x = x.to("cpu")
    tt = time.time()
    with torch.no_grad():
        loss = loss.cpu().detach().numpy()
        log_prob = log_prob.cpu().detach().numpy()
        energy = energy.cpu().detach().numpy()
        N = model.N
        free_energy_mean = loss.mean() / (beta * N)
        free_energy_std = loss.std() / (beta * N)
        entropy_mean = -log_prob.mean() / N
        energy_mean = energy.mean() / N
        energy_min = energy.min() / N
        mag = x.mean(dim=0).cpu().detach().numpy()
        mag_mean = torch.abs(x.mean(dim=1)).mean(dim=0)
        mag_mean = mag_mean.cpu().detach().numpy().item()
        q = torch.histogram((x@x.T).flatten().cpu()/N,
                            bins=100, range=(-1, 1))[0]
        if ifprint:
            str_p = f"\rstep: {step} {beta:.5f} fe: {free_energy_mean:.3f} +- {free_energy_std:.5f}, E: {energy_mean:.3f}, E_min: {energy_min:.10f}, S: {entropy_mean:.3f}, M: {mag_mean:.3}"
            times["stats"] = time.time() - tt
            for kk in times:
                str_p += f" {kk} : {times[kk]:.2}"
            print(
                str_p,
                end="",
            )

    return {
        "beta": beta,
        "free_energy_mean": free_energy_mean,
        "free_energy_std": free_energy_std,
        "entropy_mean": entropy_mean,
        "energy_mean": energy_mean,
        "energy_min": energy_min,
        "mag": mag,
        "mag_mean": mag_mean,
        "q": q
    }


class ANN(nn.Module):
    """Abstract class for a autoregressive neural networks."""

    def __init__(
        self,
        model,
        net,
        dtype=torch.float32,
        device="cpu",
        eps=1e-10,
        print_num_params=True
    ):
        """Initialize the class. 
        model: the model class [the model class should have the method energy(x)]
        net: the single autoregressive conditional neural network
        device: the device to run the model
        eps: the small number to avoid log(0)
        print_num_params: print the number of parameters
        """
        # print(model)
        super().__init__()
        self.N = model.N
        self.model = model
        self.net = net
        # self.input_mask = input_mask
        self.dtype = dtype
        self.device = device
        self.eps = eps
        if print_num_params:
            self.print_num_params(train=True)
            self.print_num_params(train=False)

    def print_num_params(self, train=True):
        num_p = self.num_params(train)
        if train:
            print(f"Total Trainable Params: {num_p}")
        else:
            print(f"Total Params: {num_p}")

    def num_params(self, train=True):
        params = self.parameters()
        if train:
            return sum(p.numel() for p in params if p.requires_grad)
        else:
            return sum(p.numel() for p in params)

    def parameters(self):
        return self.net.parameters()

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        return self.net(x)

    def prob_sample(self, x, x_hat):
        with torch.no_grad():
            mask = (x + 1) / 2
            p_sample = (x_hat**mask) * ((1 - x_hat) ** (1 - mask))
            p_sample = torch.exp(torch.log(p_sample).sum(dim=1))
        return p_sample

    def sample(self, batch_size):
        x = torch.zeros([batch_size, self.N],
                        device=self.device, dtype=self.dtype)
        x_hat = torch.zeros([batch_size, self.N],
                            device=self.device, dtype=self.dtype)
        with torch.no_grad():
            for n_i in range(self.N):
                # mask_n_i = self.input_mask[n_i, :]
                # input_x = mask_n_i * x
                x_hat[:, n_i] = self.forward(x)[:, n_i]
                x[:, n_i] = torch.bernoulli(x_hat[:, n_i]) * 2 - 1
        return x, x_hat

    def _log_prob(self, x, x_hat):
        mask = (x + 1) / 2
        log_prob = torch.log(x_hat + self.eps) * mask + torch.log(
            1 - x_hat + self.eps
        ) * (1 - mask)
        log_prob = log_prob.view(log_prob.shape[0], -1).sum(dim=1)
        return log_prob

    def log_prob(self, x):
        x = x.view(x.shape[0], -1)
        x_hat = self.forward(x)
        log_prob = self._log_prob(x, x_hat)
        return log_prob

    def compute_stats(self, beta, batch_size=10000, print_=True, batch_iter=1):
        stats_list = []
        for bb in range(batch_iter):
            with torch.no_grad():
                x, x_hat = self.sample(batch_size)
                log_prob = self._log_prob(x, x_hat)
                energy = self.model.energy(x)
                loss = log_prob + beta * energy
                stats = compute_stats(x, loss, log_prob,
                                      energy, beta, self.model, ifprint=print_)
                stats_list.append(stats)
            res_stats = self.avg_stats_(stats_list, batch_iter=batch_iter)
        return res_stats

    def avg_stats_(self, stats_list, batch_iter=1):
        keys_list = stats_list[0].keys()
        res_stats = {}
        for kk in keys_list:
            if kk == "q":
                temp = [elem[kk] for elem in stats_list]
                res_stats[kk] = torch.stack(temp).mean(dim=0)
            elif "std" in kk:
                temp = np.array([elem[kk]*elem[kk]
                                for elem in stats_list]).sum()
                res_stats[kk] = np.sqrt(temp/batch_iter)
            elif kk == "energy_min":
                res_stats[kk] = np.array([elem[kk]
                                         for elem in stats_list]).min()
            else:
                res_stats[kk] = np.array([elem[kk]
                                         for elem in stats_list]).mean()
        return res_stats

    def train(
        self,
        lr=1e-3,
        opt="adam",
        beta=1,
        max_step=10000,
        batch_size=1000,
        std_fe_limit=1e-4,
        batch_iter=1,
        ifprint=True,
        exact=False,
        set_optim=True
    ):

        if set_optim:
            params = self.parameters()
            if opt == "SGD":
                optimizer = torch.optim.SGD(params, lr=lr)
            elif opt == "sgdm":
                optimizer = torch.optim.SGD(params, lr=lr, momentum=0.9)
            elif opt == "rmsprop":
                optimizer = torch.optim.RMSprop(params, lr=lr, alpha=0.99)
            elif opt == "adam":
                optimizer = torch.optim.Adam(params, lr=lr)
            elif opt == "adam0.5":
                optimizer = torch.optim.Adam(params, lr=lr, betas=(0.5, 0.999))
            else:
                print("optimizer not found, setted Adam")
                optimizer = torch.optim.Adam(params, lr=lr)
            self.optimizer = optimizer

        optimizer = self.optimizer
        optimizer.zero_grad()
        stats_list = []
        stats_iter_done = 0
        fe_run = []
        fe_std_run = []
        times = {}
        for step in range(0, max_step + batch_iter):
            optimizer.zero_grad()
            start_t = time.time()
            with torch.no_grad():
                samples, x_hat = self.sample(batch_size)
            times["sample_t"] = time.time() - start_t
            log_prob = self.log_prob(samples)
            times["log_prob"] = time.time() - start_t - times["sample_t"]
            with torch.no_grad():
                energy = self.model.energy(samples)
                loss = log_prob + beta * energy
            times["loss"] = time.time() - start_t - times["sample_t"] - \
                times["log_prob"]

            loss_reinforce = torch.mean((loss - loss.mean()) * log_prob)
            loss_reinforce.backward()
            optimizer.step()
            times["optimizer"] = time.time() - start_t - times["sample_t"] - \
                times["log_prob"] - times["loss"]
            stats = compute_stats(samples, loss, log_prob, energy,
                                  beta, self.model, step=step, ifprint=ifprint, times=times)
            fe_run.append(stats["free_energy_mean"])
            fe_std_run.append(stats["free_energy_std"])
            if step >= max_step or stats["free_energy_std"] < std_fe_limit:
                stats_list.append(stats)
                stats_iter_done += 1
            if stats["free_energy_std"] < std_fe_limit and stats_iter_done >= batch_iter:
                break
        # print(stats_list, step)
        res_stats = self.avg_stats_(stats_list, batch_iter=batch_iter)
        res_stats["fe_run"] = fe_run
        res_stats["fe_std_run"] = fe_std_run

        return res_stats

    def train_with_samples(
        self,
        samples,
        lr=1e-3,
        opt="adam",
        beta=1,
        max_step=10000,
        batch_fraction=1,
        std_fe_limit=1e-4,
        batch_iter=1,
        ifprint=True,
        exact=False,
        set_optim=True,
    ):

        if set_optim:
            params = self.parameters()
            if opt == "SGD":
                optimizer = torch.optim.SGD(params, lr=lr)
            elif opt == "sgdm":
                optimizer = torch.optim.SGD(params, lr=lr, momentum=0.9)
            elif opt == "rmsprop":
                optimizer = torch.optim.RMSprop(params, lr=lr, alpha=0.99)
            elif opt == "adam":
                optimizer = torch.optim.Adam(params, lr=lr)
            elif opt == "adam0.5":
                optimizer = torch.optim.Adam(params, lr=lr, betas=(0.5, 0.999))
            else:
                print("optimizer not found, setted Adam")
                optimizer = torch.optim.Adam(params, lr=lr)
            self.optimizer = optimizer

        optimizer = self.optimizer
        optimizer.zero_grad()
        stats_list = []
        stats_iter_done = 0
        fe_run = []
        fe_std_run = []
        times = {}
        ss_num = int(samples.shape[0] / batch_fraction)
        for step in range(0, max_step + batch_iter):
            idx = torch.randperm(samples.shape[0])[:ss_num]
            sample_ss = samples[idx]
            optimizer.zero_grad()
            start_t = time.time()
            times["sample_t"] = time.time() - start_t
            log_prob = self.log_prob(sample_ss)
            times["log_prob"] = time.time() - start_t - times["sample_t"]
            with torch.no_grad():
                samples_net, x_hat = self.sample(ss_num)
                energy = self.model.energy(samples_net)
                log_prob_net = self.log_prob(samples_net)
                loss = log_prob_net + beta * energy
            times["loss"] = time.time() - start_t - times["sample_t"] - \
                times["log_prob"]

            loss_reinforce = -torch.mean(log_prob)
            loss_reinforce.backward()
            optimizer.step()
            times["optimizer"] = time.time() - start_t - times["sample_t"] - \
                times["log_prob"] - times["loss"]
            stats = compute_stats(samples_net, loss, log_prob_net, energy,
                                  beta, self.model, step=step, ifprint=ifprint, times=times)
            fe_run.append(stats["free_energy_mean"])
            fe_std_run.append(stats["free_energy_std"])
            if step >= max_step or stats["free_energy_std"] < std_fe_limit:
                stats_list.append(stats)
                stats_iter_done += 1
            if stats["free_energy_std"] < std_fe_limit and stats_iter_done >= batch_iter:
                break
        # print(stats_list, step)
        res_stats = self.avg_stats_(stats_list, batch_iter=batch_iter)
        res_stats["fe_run"] = fe_run
        res_stats["fe_std_run"] = fe_std_run

        return res_stats
