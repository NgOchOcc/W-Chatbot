from weschatbot.www.management.model_vm import ViewModel


class ViewModelDocument(ViewModel):
    list_fields = ["id", "name", "path", "is_used"]
    update_fields = ["name", "is_used"]
    add_fields = ["name", "path"]
    detail_fields = ["id", "name", "path", "is_used"]
    search_fields = ["name", "path"]

    field_types = {
        "path": "file_upload"
    }
