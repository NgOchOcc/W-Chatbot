FROM nvidia/cuda:12.0.0-cudnn8-devel-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip python-is-python3 pkg-config libmysqlclient-dev

RUN apt-get install -y python3-venv

RUN pip install --upgrade pip setuptools wheel

RUN pip install marker-pdf==1.8.2 markitdown==0.1.2