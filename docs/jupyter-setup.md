# Jupyter setup

## Create user jupyter

```shell
sudo adduser jupyter
# make sure jupyter user can run sudo command

sudo su jupyter
cd ~
```

## Install conda and libs

```shell
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
sh Miniconda3-latest-Linux-x86_64.sh
```

## Create a new conda env
```shell
conda create -n jupyterhub python=3.12
conda activate jupyterhub

conda install -c conda-forge nodejs configurable-http-proxy
conda install -c conda-forge jupyterlab jupyterhub
```

## Start jupyterhub

```shell
jupyterhub --generate-config

sudo env "PATH=$PATH" ~/miniconda3/envs/jupyterhub/bin/jupyterhub -f jupyterhub_config.py
```