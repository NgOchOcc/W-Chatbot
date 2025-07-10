from weschatbot.models.user import Role
from weschatbot.utils.db import provide_session


class RBACService:
    @staticmethod
    @provide_session
    def get_role(role_id, session=None):
        role = session.query(Role).filter_by(id=role_id).one_or_none()
        return role.to_dict(session=session) if role else None

    @staticmethod
    @provide_session
    def get_permissions(role_id, session=None):
        permissions = RBACService.get_object_permissions(role_id, session=session)
        return [permission.to_dict(session=session) for permission in permissions]

    @staticmethod
    @provide_session
    def get_object_permissions(role_id, session=None):
        role = session.query(Role).filter_by(id=role_id).one_or_none()
        return role.permissions
