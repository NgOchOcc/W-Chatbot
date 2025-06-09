import json

from flask import Blueprint

addition_blueprint = Blueprint("addition", __name__)


@addition_blueprint.app_context_processor
def inject_functions():
    return {
        "json_dumps": json.dumps,
    }
