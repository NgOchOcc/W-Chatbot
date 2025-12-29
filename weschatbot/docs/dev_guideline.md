# DEV guideline

### Base image

```shell
cd base_image
docker build -t chatbot-base:0.0.3 .
cd ..
```

### Application image

```shell
docker build -t westaco-chatbot:0.0.3 .
```

### Start chatbot-ui

#### Network

```shell
docker network create -d bridge westaco_chatbot
```

#### Volumes

```shell
docker volume create weschatbot_uploads_volume
docker volume create weschatbot_models_volume
docker volume create weschatbot_converted_volume
docker volume create weschatbot_datalab_models_volume
```

#### Start mysql

```shell
docker run --network westaco_chatbot --name westaco-mysql -p 3306:3306 -p 33060:33060 -e MYSQL_ROOT_PASSWORD=Adcef#1234 -d mysql:8.0.40-debian --default-authentication-plugin=mysql_native_password

# wait in couples of minutes
docker exec -it westaco-mysql mysql -u root -pAdcef#1234 -e "create database chatbot;"

docker run --rm --network westaco_chatbot \
  --name westaco-init-db \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  westaco-chatbot:0.0.2 \
  alembic upgrade head
```

#### Start redis

```shell
docker run --network westaco_chatbot --name westaco-redis -d redis
```

#### Start milvus

```shell
cd milvus
docker compose up -d
```

#### Start applications

##### Chatbot UI

```shell
docker run -d -p 3000:3000 \
  --restart=always \
  --name westaco-chatbot-ui \
  --network westaco_chatbot \
  --env-file .env \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__REDIS__HOST=westaco-redis \
  -e WESCHATBOT__REDIS__PORT=6379 \
  -e WESCHATBOT__VLLM__BASE_URL=http://westaco-chatbot-vllm:9292 \
  -e WESCHATBOT__VLLM__MODEL=AlphaGaO/Qwen3-14B-GPTQ \
  -e WESCHATBOT__JWT__COOKIE_SAMESITE=lax \
  -e WESCHATBOT__JWT__COOKIE_SECURE=false \
  --network milvus \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_converted_volume:/srv/weschatbot/converted \
  -v weschatbot_models_volume:/root/.cache/huggingface \
  westaco-chatbot:0.0.3 \
  weschatbot chatbot start bind=0.0.0.0:3000 worker_class=uvicorn.workers.UvicornWorker workers=4
```

##### Management

```shell
docker run -d -p 9090:5000 \
  --restart=always \
  --name westaco-chatbot-management \
  --network westaco_chatbot \
  --env-file .env \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__REDIS__HOST=westaco-redis \
  -e WESCHATBOT__REDIS__PORT=6379 \
  -e WESCHATBOT__CELERY__BROKER_URL=redis://westaco-redis:6379/2 \
  -e WESCHATBOT__CELERY__BACKEND_URL=redis://westaco-redis:6379/3 \
  --network milvus \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_converted_volume:/srv/weschatbot/converted \
  westaco-chatbot:0.0.3 \
  weschatbot management start bind=0.0.0.0:5000 timeout=120 workers=4
```

##### Worker

```shell
docker run -d --gpus all \
  --restart=always \
  --name westaco-chatbot-worker \
  --network westaco_chatbot \
  --env-file .env \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__REDIS__HOST=westaco-redis \
  -e WESCHATBOT__REDIS__PORT=6379 \
  -e WESCHATBOT__CELERY__BROKER_URL=redis://westaco-redis:6379/2 \
  -e WESCHATBOT__CELERY__BACKEND_URL=redis://westaco-redis:6379/3 \
  --network milvus \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_converted_volume:/srv/weschatbot/converted \
  -v weschatbot_datalab_models_volume:/root/.cache/datalab/models/ \
  westaco-chatbot:0.0.2 \
  weschatbot worker start
```

##### VLLM

###### chat completions

```shell
docker run -d --gpus all \
    -p 9292:9292 \
    --restart=always \
    --name westaco-chatbot-vllm \
    --network westaco_chatbot \
    --env-file .env \
    -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
    -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
    -e WESCHATBOT__REDIS__HOST=westaco-redis \
    -e WESCHATBOT__REDIS__PORT=6379 \
    -v weschatbot_models_volume:/root/.cache/huggingface \
    westaco-chatbot:0.0.3 \
    python -m vllm.entrypoints.openai.api_server \
    --model AlphaGaO/Qwen3-14B-GPTQ \
    --max-model-len 5500 \
    --gpu-memory-utilization 0.75 \
    --port 9292
```

###### embed

```shell
docker run -d --gpus all \
  -p 9290:9290 \
  --restart=always \
  --name westaco-chatbot-vllm-embed \
  --network westaco_chatbot \
  --env-file .env \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__REDIS__HOST=westaco-redis \
  -e WESCHATBOT__REDIS__PORT=6379 \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_models_volume:/root/.cache/huggingface \
  westaco-chatbot:0.0.3 \
  python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-Embedding-0.6B \
  --max-model-len 2048 \
  --gpu-memory-utilization 0.2 \
  --task embed \
  --port 9290 \
  --tensor-parallel-size 1 \
  --enforce-eager
```