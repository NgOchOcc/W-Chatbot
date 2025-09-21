# How to contribute

## Run docker service

### MySQL

```shell
docker run --name local-mysql -p 3306:3306 -p 33060:33060 -e MYSQL_ROOT_PASSWORD=Adcef#1234 -d mysql:8.0.40-debian --default-authentication-plugin=mysql_native_password

# wait couples of minutes
docker exec -it local-mysql mysql -u root -pAdcef#1234 -e "create database chatbot;"
```

### Redis

```shell
docker run --name local-redis -d redis
```

### Milvus

```shell
cd milvus
docker compose up -d
```

### Init db

```shell
alembic update head
```

### Start chat ui
```shell
python weschatbot/__main__.py chatbot start
```