import bp_solver
import bp_nn
import numpy as np
import matplotlib.pyplot as plt
import bp_nn_2

def bp_sol(model, betas, error = 1e-6,
           val_rand=0.1,
           max_iter = 1000):
    fe_bp = []
    ener_bp = []
    m_bp = []
    m_i_bp = []
    BP_tree = bp_solver.BP_solver(model) 

    for beta in betas:

        BP_tree.converge(beta, error = error,
                         max_iter=max_iter, val_rand=0.1)
        fe_bp.append(BP_tree.F)
        ener_bp.append(BP_tree.E_mean)
        m_bp.append(BP_tree.M_mean)
        m_i_bp.append(BP_tree.M_i)
    
    return {
        "betas":betas,
        "fe":np.array(fe_bp),
        "E": np.array(ener_bp),
        "M": np.array(m_bp),
        "M_i": np.array(m_i_bp)
    }

def nn_sol(model, betas, bias = True, z2 = False, x_hat_clip = False,
          stats = 10000, lr = 0.01,
          max_step=1000,
          batch_size=1000,
          opt = "adam", nn_use = bp_nn.bp_nn):
    fe_nn = []
    ener_nn = []
    m_nn = []
    m_i_nn = []
    net = nn_use(model.N, model, bias, z2=z2, 
                    x_hat_clip=x_hat_clip )
    for beta in betas:

        net.train(beta = beta, lr=lr, max_step=max_step, 
                  batch_size=batch_size,
                 opt = opt)
        F = +1e100
        E = 0
        M = 0
        M_i = 0
        S = 0
        F_std = 0
        #for ss in range(stats):
        net.compute_stat(beta, batch_size = stats, print_=False)
            #if net.F < F:
                #print(F, net.F)
        F = net.F
        E = net.E
        M = net.M
        M_i = net.M_i
        S = net.S
        F_std = net.F_std
        #net.compute_stat(beta, batch_size = 10000, print_=True)
        fe_nn.append(F)
        ener_nn.append(E)
        m_nn.append(M)
        m_i_nn.append(M_i)
        #print("\r", end="")
        print("\rfe: {0:.3f} std_fe: {1:.2E} M: {2:.3f} S: {3:.3f} E: {4:.3f}".format(F,
                                                    F_std,
                                                    M,
                                                    S,
                                                    E,),)
        #print()
    return {
        "betas": betas,
        "fe": np.array(fe_nn),
        "E": np.array(ener_nn),
        "M": np.array(m_nn),
        "M_i": np.array(m_i_nn)
    }

def nn_sol_normed(model, betas, bias = True, z2 = False, x_hat_clip = False,
          stats = 100, lr = 0.01,
          max_step=1000,
          batch_size=1000,
          opt = "adam"):
    fe_nn = []
    ener_nn = []
    m_nn = []
    m_i_nn = []
    net = bp_nn.bp_nn_normed(model.N, model, bias)
    for beta in betas:

        net.train(beta = beta, lr=lr, max_step=max_step, 
                  batch_size=batch_size,
                 opt = opt)
        F = +1e100
        E = 0
        M = 0
        M_i = 0
        S = 0
        F_std = 0
        for ss in range(stats):
            net.compute_stat(beta, batch_size = 10000, print_=False)
            if net.F < F:
                #print(F, net.F)
                F = net.F
                E = net.E
                M = net.M
                M_i = net.M_i
                S = net.S
                F_std = net.F_std
        #net.compute_stat(beta, batch_size = 10000, print_=True)
        fe_nn.append(F)
        ener_nn.append(E)
        m_nn.append(M)
        m_i_nn.append(M_i)
        #print("\r", end="")
        print("\rfe: {0:.3f} std_fe: {1:.2E} M: {2:.3f} S: {3:.3f} E: {4:.3f}".format(F,
                                                    F_std,
                                                    M,
                                                    S,
                                                    E,),)
        print()
        
    return {
        "betas": betas,
        "fe": np.array(fe_nn),
        "E": np.array(ener_nn),
        "M": np.array(m_nn),
        "M_i": np.array(m_i_nn)
    }


def exact_sol(model, betas):
    fe_ex = []
    ener_ex = []
    m_ex = []
    m_i_ex = []
    for beta in betas:
        model.exact(beta)
        fe_ex.append(model.free_energy)
        ener_ex.append(model.E_mean)
        m_ex.append(model.M_mean)
        m_i_ex.append(model.M_i_mean)
    return {
        "betas": betas,
        "fe": np.array(fe_ex),
        "E": np.array(ener_ex),
        "M": np.array(m_ex),
        "M_i": np.array(m_i_ex)
    }

        
def plot_quantity(label, res_ex, others, init_=0):
    plt.figure(figsize=(10,5))
    ax1 = plt.subplot(221,)
    plt.plot(res_ex["betas"][init_:], res_ex[label][init_:], label = "exact")
    for other in others:
        plt.plot(other["betas"][init_:], other[label][init_:],"o", label=other["name"],)
    plt.legend()
    ax2 = plt.subplot(222)
    for other in others:
        plt.plot(other["betas"][init_:], (other[label][init_:] - res_ex[label][init_:]), "o",
                 label=other["name"])
    plt.legend()
    ax2.set_title("absolute error")

    ax3 = plt.subplot(223)
    for other in others:
        plt.plot(other["betas"][init_:], 100 * abs(other[label][init_:] - res_ex[label][init_:]) / abs(res_ex[label][init_:] +1e-6), "o",
                 label=other["name"])
    ax3.set_title("percentage error")
    plt.legend()
    return plt

def plot_quantity_sum(label, res_ex, others, init_=0):
    plt.figure(figsize=(10,5))
    ax1 = plt.subplot(121,)
    
    for other in others:
        ax1.plot(other["betas"][init_:], abs(other[label][init_:] - res_ex[label][init_:]).sum(axis=1)/len(other[label]), "o",
                 label=other["name"])
    ax1.legend()
    
    ax2 = plt.subplot(122,)
    for other in others:
        ax2.plot(other["betas"][init_:], 100*abs(other[label][init_:] - res_ex[label][init_:]).sum(axis=1)/len(other[label]) / res_ex[label][init_:].sum(axis=1), "o",
                 label=other["name"])
    ax2.set_title("percentage error")
    ax2.legend()
    return plt
