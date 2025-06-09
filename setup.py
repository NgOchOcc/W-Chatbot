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
        "build==1.2.2"
    ]
)
