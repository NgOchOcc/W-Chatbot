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
    install_requires=[
        "importlib_metadata==8.5.0",
        "cookiecutter==2.6.0",
        "click==8.1.7",
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
        "build==1.2.2",
        "aiohttp==3.9.1"
    ]
)
