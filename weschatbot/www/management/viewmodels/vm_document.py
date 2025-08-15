from weschatbot.www.management.model_vm import ViewModel


class ViewModelDocument(ViewModel):
    list_fields = ["id", "name", "path", "is_used", "status"]
    update_fields = ["name", "is_used", "status"]
    add_fields = ["name", "path", "status"]
    detail_fields = ["id", "name", "path", "is_used", "status"]
    search_fields = ["name", "path", "status"]

    field_types = {
        "path": "file_upload"
    }
