FROM nvidia/cuda:12.0.0-cudnn8-devel-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip

RUN pip install fastapi uvicorn \
    && pip install 'uvicorn[standard]' \
    && pip install fastapi uvicorn transformers sentence-transformers pymilvus
