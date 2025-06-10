# Deployment

## Build

### Base image

```shell
cd base_image
docker build -t chatbot-base:0.0.1 .
```

### Application image

```shell
docker build -t westaco-chatbot:0.0.1 .
```

### Start chatbot-ui

## Network

```shell
docker network create -d bridge westaco_chatbot
```

#### Start milvus

```shell
cd milvus
docker compose up -d
```

#### Start application

```shell
docker run -d --rm -p 8000:8000 \
  --name westaco-chatbot-ui \
  --network westaco_chatbot \
  --env-file .env \
  --network milvus \
  westaco-chatbot:0.0.1 \
  weschatbot chatbot start
```