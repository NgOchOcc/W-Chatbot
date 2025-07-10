import json

from flask import Blueprint

from weschatbot.services.rbac_service import RBACService
from weschatbot.utils.db import create_session

addition_blueprint = Blueprint("addition", __name__)


@addition_blueprint.app_context_processor
def inject_functions():
    return {
        "json_dumps": json.dumps,
        "user_permissions": RBACService.get_permissions,
        "user_role": RBACService.get_role,
    }
