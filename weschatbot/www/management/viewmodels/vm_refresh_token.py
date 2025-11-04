from weschatbot.www.management.model_vm import ViewModel


class ViewModelRefreshToken(ViewModel):
    list_fields = ["id", "user_id", "user", "ip_address", "expires_at", "revoked", "modified_date"]
    detail_fields = ["id", "user_id", "user", "ip_address", "expires_at", "revoked", "token", "modified_date",
                     "user_agent_raw",
                     "accept_language"]
    search_fields = ["user_id"]
    update_fields = ["revoked"]

    disabled_view_models = ["add"]
