from flask import url_for
from sqlalchemy import inspect

from weschatbot.utils.db import provide_session


def outside_url_for(end_point, **kwargs):
    def wrap_url_for(*args, **params):
        return url_for(end_point, **{**kwargs, **params})

    return wrap_url_for


def is_relationship(model_class, field):
    for rel in inspect(model_class).relationships:
        if rel.key == field:
            match rel.direction.name:
                case "MANYTOONE":
                    res = "relationship_one"
                case "MANYTOMANY":
                    res = "relationship_many"
                case "ONETOMANY":
                    res = "relationship_many"
                case _:
                    res = None
            return res
    return False


def relationship_class(model_class, field):
    for rel in inspect(model_class).relationships:
        if rel.key == field:
            return rel.mapper.class_
    return None


@provide_session
def relationship_data(model_class, session=None):
    res = session.query(model_class).all()
    return [x.to_dict(session) for x in res]


def get_auto_field_types(model_class, fields, overwrite_field_types):
    res = {}
    for field in fields:
        res[field] = is_relationship(model_class, field) or type(getattr(model_class, field).type).__name__.lower()
    res.update(overwrite_field_types)
    return res


def inheritors(klass):
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses
