# H2ARNN 
## Pairwise interacting systems (H2) AutoRegressive Neural Network

This repository contains a python package to train Autoregressive Neural Networks (arnn) to learn to generate according to the classical Boltzmann distribution of a generic pairwise interacting spins system.  The architectures of the autoregressive neural newtorks implemented so far are the MADE architecture, the CW architecture, the SK-krsb architecture. New architectures can be easily added.
This repository contains the code used to generate the images and results presented in the paper: 

 > The autoregressive neural network architecture of the Boltzmann distribution of pairwise interacting spins systems.
 >
 > Indaco Biazzo [[arXiv:2302.08347](https://arxiv.org/abs/2302.08347)]


## Requirements
Tested with python 3.10.4 and:
- matplotlib==3.5.2
- networkx==2.8.4
- numpy==1.23.3
- pandas==1.4.4
- scipy==1.9.1
- torch==1.13.1

[see requirements.txt]

## Usage
- Look at the notebook `simple_example.ipynb`

## Files
- `python_lib` [the main code of the package] 
- `results` [the code to reproduce results and image of the [paper]()] 

## Results
- In the directory `results/SK/` type `./run_many_sk.sh` to produce the data for the SK model. 
- In the directory `results/CW/` type `./run_many_cw.sh` to produce the data for the CW model. 
- The data for the MonteCarlo experiment is produced by the notebook `./results/SK/SK_MC.ipynb` 
- The images can be created running the notebooks:
    1. `./results/SK/SK_plots.ipynb`
    2. `./results/CW/CW_plots.ipynb`

## Citation
If you use the code please cite the paper:


Biazzo, Indaco. *"The autoregressive neural network architecture of the Boltzmann distribution of pairwise interacting spins systems."* arXiv preprint [[arXiv:2302.08347](https://arxiv.org/abs/2302.08347)] (2023).

## License
- MIT License. See the LICENSE file for details.
