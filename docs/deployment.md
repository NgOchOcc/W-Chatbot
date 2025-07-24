# Deployment

## Build

### Base image

```shell
cd base_image
docker build -t chatbot-base:0.0.1 .
cd ..
```

### Application image

```shell
docker build -t westaco-chatbot:0.0.1 .
```

### Start chatbot-ui

#### Network

```shell
docker network create -d bridge westaco_chatbot
```

#### Start mysql
```shell
docker run --network westaco_chatbot --name westaco-mysql -p 3306:3306 -p 33060:33060 -e MYSQL_ROOT_PASSWORD=Adcef#1234 -d mysql:8.0.40-debian --default-authentication-plugin=mysql_native_password

# wait in couples of minutes
docker exec -it westaco-mysql mysql -u root -pAdcef#1234 -e "create database chatbot;"

docker run --rm --network westaco_chatbot \
  --name westaco-init-db \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  westaco-chatbot:0.0.1 \
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
docker run -d -p 8000:8000 \
  --restart=always \
  --name westaco-chatbot-ui \
  --network westaco_chatbot \
  --env-file .env \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__REDIS__HOST=westaco-redis \
  -e WESCHATBOT__REDIS__PORT=6379 \
  --network milvus \
  westaco-chatbot:0.0.1 \
  weschatbot chatbot start
```

##### Management
```shell
docker run -d -p 5000:5000 \
  --restart=always \
  --name westaco-chatbot-management \
  --network westaco_chatbot \
  --env-file .env \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__DB__ASYNC_SQL_ALCHEMY_CONN=mysql+aiomysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  -e WESCHATBOT__REDIS__HOST=westaco-redis \
  -e WESCHATBOT__REDIS__PORT=6379 \
  --network milvus \
  westaco-chatbot:0.0.1 \
  weschatbot management start bind=0.0.0.0:5000
```