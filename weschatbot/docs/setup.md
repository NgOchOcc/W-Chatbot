# Setup Dev Environment


```shell
# jupyter
docker run -d \
  --name jupyter-notebook \
  --network westaco_chatbot \
  --network milvus \
  -p 8888:8888 \
  -v /home/manh/code/notebooks:/home/jovyan/work \
  jupyter/base-notebook

# mysql
docker run --network westaco_chatbot \
  --name local-mysql \
  -p 3306:3306 \
  -p 33060:33060 \
  -e MYSQL_ROOT_PASSWORD=Adcef#1234 \
  -d \
  mysql:8.0.40-debian \
  --default-authentication-plugin=mysql_native_password
```

## Open ports
* 9091
* 3306
* 8888
* 8000
