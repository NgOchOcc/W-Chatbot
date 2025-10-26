import os

from setuptools import setup

version = "0.0.1"
name = "weschatbot"
author = "Westaco"
author_email = "manh.tran@westaco.com"
description = ""
license_ = "Westaco"
packages = [x[0].replace("./", "").replace("/", ".") for x in
            filter(lambda x: x[2].__contains__("__init__.py") and not x[2].__contains__("tests"), os.walk("./"))]

setup(
    name=name,
    version=version,
    packages=packages,
    url='',
    license=license_,
    author=author,
    author_email=author_email,
    description=description,
    include_package_data=True,
    package_data={
        "weschatbot": ["weschatbot/www/templates/**/*.html"]
    },
    install_requires=[
        "importlib_metadata==8.5.0",
        "cookiecutter==2.6.0",
        "click==8.2.1",
        "flask==3.1.1",
        "sqlalchemy==2.0.41",
        "gunicorn==23.0.0",
        "flask_wtf==1.2.2",
        "mysqlclient==2.2.7",
        "PyJWT==2.10.1",
        "redis==6.2.0",
        "aiomysql==0.2.0",
        "alembic==1.16.2",
        "fastapi-csrf-protect==1.0.3",
        "python-multipart==0.0.20",
        "flask_login==0.6.3",
        "marker-pdf==1.8.2",
        "markitdown==0.1.2",
        "build==1.2.2",
        "llama-index==0.12.52",
        "llama-index-embeddings-huggingface==0.5.5",
        "llama-index-vector-stores-milvus==0.8.7",
        "celery==5.5.3",
        "pymilvus==2.5.10",
        "pyrate-limiter==3.9.0",
        "fastapi==0.115.12"
    ]
)
