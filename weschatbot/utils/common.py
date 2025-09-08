import json


def create_object_from_class_name(full_class_name, params):
    class_name = full_class_name.split(".")[-1]
    module_name = ".".join(full_class_name.split(".")[:-1])
    params = json.loads(params)
    module = __import__(module_name, fromlist=[class_name])
    klass = getattr(module, class_name)
    obj = klass(**params)
    return obj


def get_function_by_fullname(fullname):
    module_name = ".".join(fullname.split(".")[:-1])
    func_name = fullname.split(".")[-1]
    return get_function_by_name(module_name, func_name)


def get_function_by_name(module_name, func_name):
    module = __import__(module_name, fromlist=[func_name])
    return getattr(module, func_name, None)


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
