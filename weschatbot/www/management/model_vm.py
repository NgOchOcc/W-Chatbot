import hashlib
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from functools import reduce, wraps
from typing import Optional

from flask import Blueprint, request, abort, render_template, redirect, flash
from flask_login import current_user
from werkzeug.datastructures import FileStorage

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.services.rbac_service import RBACService
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session
from weschatbot.www.management.utils import get_auto_field_types, is_relationship, relationship_class, \
    relationship_data, outside_url_for

logger = logging.getLogger(__name__)


@provide_session
def permissions_by_user(user_id, session=None):
    res = RBACService.get_object_permissions(current_user.role.id, session=session)
    return res


class UploadError(Exception):
    pass


def save_upload_file(
        upload_file: FileStorage,
        dest_folder: str,
        *,
        max_size: int = config.getint("core", "upload_max_file_size"),
        chunk_size: int = 64 * 1024
) -> str:
    if not upload_file or not getattr(upload_file, "filename", None):
        raise UploadError("No file provided")

    filename = secure_filename(upload_file.filename)
    if not filename:
        raise UploadError("Invalid filename")

    content_length = getattr(upload_file, "content_length", None)
    if content_length is not None and content_length > max_size:
        raise UploadError("Content-Length exceeds limit")

    tmp_path: Optional[str] = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp_path = tmp.name
        total = 0

        while True:
            chunk = upload_file.stream.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > max_size:
                tmp.close()
                os.unlink(tmp_path)
                raise UploadError("File size exceeds limit")
            tmp.write(chunk)

        tmp.flush()
        tmp.close()

        os.makedirs(dest_folder, exist_ok=True)
        dest_path = os.path.join(dest_folder, filename)

        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while True:
                new_name = f"{base}_{counter}{ext}"
                new_path = os.path.join(dest_folder, new_name)
                if not os.path.exists(new_path):
                    dest_path = new_path
                    break
                counter += 1

        os.replace(tmp_path, dest_path)
        tmp_path = None
        return dest_path

    except UploadError:
        raise
    except Exception as exc:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise UploadError("Internal error while saving file") from exc


def check_permission(permission):
    def check_func(func):
        @wraps(func)
        def wrap(self_object, *args, **kwargs):
            if current_user.role.name == "admin":
                return func(self_object, *args, **kwargs)
            view_model_name = self_object.__class__.__name__
            required_permission = f"{view_model_name.lower()}.{permission}"
            permissions = permissions_by_user(current_user.id)

            all_permission = list(
                filter(lambda x: required_permission in x.name and x.name.endswith(".all"), permissions))
            if all_permission:
                return func(self_object, *args, **kwargs)

            existed_permission = list(filter(lambda x: required_permission in x.name, permissions))
            if existed_permission:
                return func(self_object, *args, **kwargs)
            return abort(403)

        return wrap

    return check_func


def secure_filename(file_name):
    ext = file_name.rsplit(".")[-1:][0]
    std_file_name = "_".join(file_name.rsplit(".")[:-1]).replace(" ", "_")
    hash_part = hashlib.sha256(
        bytes(f"{std_file_name}.{uuid.uuid4().hex}", "UTF-8")).hexdigest()
    return f"{std_file_name}.{hash_part}.{ext}"


class Field:
    def __init__(self, name, _type):
        self.name = name
        self.type = _type

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type
        }


class UpdateValue:
    def __init__(self, value):
        self.value = value

    def is_updated(self):
        return True


class NoUpdate(UpdateValue):
    def __init__(self):
        super().__init__(None)

    def is_updated(self):
        return False


class Pagination:
    def __init__(self, page=1, page_size=20, total=0):
        self.page = page
        self.page_size = page_size
        self.total = total

    def to_dict(self):
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total
        }


class SubViewModel(LoggingMixin):
    def __init__(self, view_model_class):
        self.view_model_class = view_model_class
        self.register()

    def register(self):
        pass

    def to_dict(self):
        pass


class ListViewModel(SubViewModel):
    list_fields = []
    field_types = {}
    items = []

    search_url_func = None
    search_fields = []
    keyword = None

    detail_url_func = None
    update_url_func = None
    add_url_func = None
    delete_url_func = None

    pagination = Pagination()

    model_class = None

    def register(self):
        self.model_class = self.view_model_class.model_class
        self.list_fields = self.view_model_class.list_fields
        self.search_url_func = self.view_model_class.search_url_func
        self.search_fields = self.view_model_class.search_fields
        self.keyword = self.view_model_class.keyword
        self.detail_url_func = self.view_model_class.detail_url_func
        self.update_url_func = self.view_model_class.update_url_func
        self.add_url_func = self.view_model_class.add_url_func
        self.delete_url_func = self.view_model_class.delete_url_func
        self.pagination = self.view_model_class.pagination
        self.field_types = self.view_model_class.field_types

    def map_item(self, item):
        item.detail_url = self.detail_url_func(item_id=item.id)
        item.update_url = self.update_url_func and self.update_url_func(item_id=item.id) or None
        item.delete_url = self.delete_url_func and self.delete_url_func(item_id=item.id) or None

        res = {}
        for field in [*self.list_fields, "detail_url", "update_url", "delete_url"]:
            res[field] = getattr(item, field)
        return res

    def to_dict(self):
        self.field_types = get_auto_field_types(self.model_class, self.list_fields, self.field_types)

        return {
            "add_url": self.add_url_func and self.add_url_func(),
            "list_fields": self.list_fields,
            "data_types": self.field_types,
            "items": [self.map_item(x) for x in self.items],
            "search_url": self.search_url_func(),
            "keyword": self.keyword,
            "pagination": self.pagination.to_dict(),
            "title": f"List {self.model_class.__name__}",
        }


class AddViewModel(SubViewModel):
    add_fields = []
    field_types = {}
    model_class = None
    select_funcs = {}

    def register(self):
        self.model_class = self.view_model_class.model_class
        self.add_fields = self.view_model_class.add_fields
        self.field_types = self.view_model_class.field_types
        self.select_funcs = self.view_model_class.select_funcs

    @provide_session
    def to_dict(self, session=None):
        self.field_types = get_auto_field_types(self.model_class, self.add_fields, self.field_types)
        relationships = {}
        select_items = {}

        for field in self.add_fields:
            relationship = is_relationship(self.model_class, field)
            match relationship:
                case "relationship_one":
                    model_relationship = relationship_class(self.model_class, field)
                    relationships[field] = relationship_data(model_relationship, session)
                case "relationship_many":
                    model_relationship = relationship_class(self.model_class, field)
                    relationships[field] = relationship_data(model_relationship, session)
                case _:
                    pass

            match self.field_types[field]:
                case "select":
                    func = self.select_funcs[field]
                    items = func()
                    select_items[field] = items
                case _:
                    pass

        return {
            "add_fields": self.add_fields,
            "data_types": self.field_types,
            "title": f"Add {self.model_class.__name__}",
            "relationships": relationships,
            "select_items": select_items
        }


class UpdateViewModel(SubViewModel):
    disabled_update_fields = []
    update_fields = []
    item = None
    model_class = None
    field_types = {}
    select_funcs = {}

    def item_name(self):
        return self.item.name

    def __init__(self, view_model_class):
        super().__init__(view_model_class)

    def register(self):
        self.model_class = self.view_model_class.model_class
        self.update_fields = self.view_model_class.update_fields
        self.disabled_update_fields = self.view_model_class.disabled_update_fields
        self.field_types = self.view_model_class.field_types
        self.select_funcs = self.view_model_class.select_funcs

    @provide_session
    def to_dict(self, session=None):
        item = {}
        relationships = {}
        select_items = {}

        self.field_types = get_auto_field_types(self.model_class, [*self.update_fields, *self.disabled_update_fields],
                                                self.field_types)

        for field in [*self.update_fields, *self.disabled_update_fields]:
            relationship = is_relationship(self.model_class, field)
            match relationship:
                case "relationship_one":
                    item[field] = getattr(self.item, field) is not None and getattr(self.item, field).to_dict() or {}

                    model_relationship = relationship_class(self.model_class, field)
                    relationships[field] = relationship_data(model_relationship, session)
                case "relationship_many":
                    item[field] = list(map(lambda x: x.to_dict(session), getattr(self.item, field)))
                    model_relationship = relationship_class(self.model_class, field)
                    relationships[field] = relationship_data(model_relationship, session)
                case _:
                    item[field] = getattr(self.item, field)

            match self.field_types[field]:
                case "select":
                    func = self.select_funcs[field]
                    items = func()
                    select_items[field] = items
                case _:
                    pass
        return {
            "relationships": relationships,
            "select_items": select_items,
            "disabled_update_fields": self.disabled_update_fields,
            "update_fields": self.update_fields,
            "item": item,
            "data_types": self.field_types,
            "title": f"Update {self.model_class.__name__}",
        }


class DeleteViewModel(SubViewModel):
    item = None
    model_class = None

    def item_name(self):
        return self.item.name

    def register(self):
        self.model_class = self.view_model_class.model_class

    def to_dict(self):
        return {
            "title": f"Delete {self.model_class.__name__}",
            "item": self.item.to_dict()
        }


class DetailViewModel(SubViewModel):
    actions = {}
    detail_fields = []
    item = None
    model_class = None
    field_types = {}

    def item_name(self):
        return self.item.name

    def register(self):
        self.model_class = self.view_model_class.model_class
        self.detail_fields = self.view_model_class.detail_fields
        self.actions = self.view_model_class.actions
        self.field_types = self.view_model_class.field_types

    def map_item(self):
        res = {}
        for field in self.detail_fields:
            res[field] = getattr(self.item, field)
        return res

    def to_dict(self):
        acts = {}
        for act in self.actions:
            acts[act] = self.actions[act](item_id=self.item.id)

        self.field_types = get_auto_field_types(self.model_class, self.detail_fields, self.field_types)

        return {
            "actions": acts,
            "detail_fields": self.detail_fields,
            "data_fields": self.field_types,
            "item": self.map_item(),
            "title": f"Details of {self.model_class.__name__}",
        }


class ViewModel(LoggingMixin):
    model_class = None

    disabled_update_fields = []
    disabled_view_models = []
    update_fields = []

    actions = {}
    detail_fields = []
    search_fields = []
    add_fields = []

    list_fields = []

    item = None
    items = []

    search_url_func = None
    detail_url_func = None
    update_url_func = None
    add_url_func = None
    delete_url_func = None

    keyword = None

    pagination = Pagination()

    template_folder = "templates"
    static_folder = "static"

    bp: Blueprint = None
    list_view_model: ListViewModel = None

    list_template = ""
    detail_template = ""
    update_template = ""
    delete_template = ""
    add_template = ""
    field_types = {}
    select_funcs = {}

    def __init__(self, model_class,
                 auth,
                 add_view_model=AddViewModel,
                 update_view_model=UpdateViewModel,
                 list_view_model=ListViewModel,
                 delete_view_model=DeleteViewModel,
                 detail_view_model=DetailViewModel,
                 list_template="management/list_view.html",
                 detail_template="management/detail_view.html",
                 update_template="management/update_view.html",
                 delete_template="management/delete_view.html",
                 add_template="management/add_view.html"):
        self.model_class = model_class
        self.__class__.bp = Blueprint(self.__class__.__name__, __name__,
                                      url_prefix=f"{self.__class__.__name__}",
                                      template_folder=self.template_folder, static_folder=self.static_folder)

        if not self.add_enabled():
            self.add_url_func = None
        else:
            self.add_url_func = self.add_url_func or outside_url_for(".add_item")

        self.search_url_func = outside_url_for(".list_items")
        self.detail_url_func = self.detail_enabled() and outside_url_for(".detail_item")
        self.update_url_func = self.update_enabled() and outside_url_for(".update_item")
        self.delete_url_func = self.delete_enabled() and outside_url_for(".delete_item")

        self.list_view_model = list_view_model(self)
        self.add_view_model = add_view_model(self)
        self.update_view_model = update_view_model(self)
        self.delete_view_model = delete_view_model(self)
        self.detail_view_model = detail_view_model(self)

        self.list_template = list_template
        self.detail_template = detail_template
        self.update_template = update_template
        self.delete_template = delete_template
        self.add_template = add_template
        self.auth = auth

    def enabled(self, view_model):
        return view_model not in self.disabled_view_models

    def add_enabled(self):
        return self.enabled("add")

    def update_enabled(self):
        return self.enabled("update")

    def delete_enabled(self):
        return self.enabled("delete")

    def list_enabled(self):
        return self.enabled("list")

    def detail_enabled(self):
        return self.enabled("detail")

    def register(self, flask_app_or_bp):
        if self.list_enabled():
            self.bp.route("/list", methods=["GET"])(self.auth(self.list_items))
        if self.add_enabled():
            self.bp.route("/add", methods=["GET", "POST"])(self.auth(self.add_item))
        if self.update_enabled():
            self.bp.route("/<int:item_id>/update", methods=["GET", "POST"])(self.auth(self.update_item))
        if self.delete_enabled():
            self.bp.route("/<int:item_id>/delete", methods=["GET", "POST"])(self.auth(self.delete_item))
        if self.detail_enabled():
            self.bp.route("/<int:item_id>", methods=["GET"])(self.auth(self.detail_item))

        flask_app_or_bp.register_blueprint(self.bp)

    @provide_session
    @check_permission("list")
    def list_items(self, session=None):
        keyword = request.args.get("keyword", None)
        page = max(int(request.args.get("page", 1)), 1)
        page_size = int(request.args.get("page_size", 20))

        query = session.query(self.model_class)
        if keyword:
            query = query.filter(reduce(lambda r, x: r | x,
                                        [getattr(self.model_class, field).like(f"%{keyword}%") for field in
                                         self.search_fields]))

        query = query.order_by(self.model_class.id.desc())
        total = query.count()
        query = query.offset((page - 1) * page_size).limit(page_size)
        items = query.all()

        res = self.list_view_model
        res.items = items
        res.keyword = keyword
        res.pagination = Pagination(page, page_size, total)

        return render_template(self.list_template, model=json.dumps(res.to_dict(), default=str),
                               title=f"List of {self.model_class.__name__}"), 200

    @provide_session
    def add_item_post(self, callback=lambda item: None, session=None):
        kwargs = {}

        for field in self.add_fields:
            kwargs[field] = request.form.get(field, None)

            value = request.form.get(field, None)
            field_types = get_auto_field_types(self.model_class, self.add_fields, self.field_types)
            match field_types[field].lower():
                case "boolean":
                    res = UpdateValue(bool(int(request.form.get(field, False))))
                case "TIMESTAMP":
                    res = UpdateValue(datetime.fromtimestamp(int(value) / 1000.0))
                case "relationship_one":
                    req_value = request.form[field]
                    rel_class = relationship_class(self.model_class, field)
                    res = UpdateValue(session.query(rel_class).filter_by(id=req_value).one_or_none())
                case "relationship_many":
                    req_value = request.form.getlist(field)
                    rel_class = relationship_class(self.model_class, field)
                    res = UpdateValue(session.query(rel_class).filter(rel_class.id.in_(req_value)).all())
                case "file_upload":
                    if field in request.files and request.files[field].filename:
                        try:
                            file = request.files[field]
                            upload_file_path = save_upload_file(upload_file=file,
                                                                dest_folder=config.get("core", "upload_file_folder"))
                            res = UpdateValue(upload_file_path)
                        except UploadError as e:
                            flash(f"{e}", "danger")
                            return redirect(self.list_view_model.search_url_func()), 302
                    else:
                        res = NoUpdate()
                case _:
                    res = NoUpdate()
            if res.is_updated():
                kwargs[field] = res.value
        item = self.model_class(**kwargs)
        session.add(item)
        session.commit()
        callback(item.to_dict())
        flash(f"Successfully added item {item.id}", "success")
        return redirect(self.list_view_model.search_url_func()), 302

    def add_item_get(self):
        model = self.add_view_model
        return render_template(self.add_template, model=json.dumps(model.to_dict(), default=str),
                               title=f"Add {self.model_class.__name__}"), 200

    @provide_session
    def add_item(self, session=None):
        return request.method == "POST" and self.add_item_post(session=session) or self.add_item_get()

    @provide_session
    def update_item_get(self, item_id, item_name_func=None, session=None):
        item = session.query(self.model_class).filter_by(id=item_id).one_or_none()
        model = self.update_view_model
        model.update_fields = self.update_fields
        model.disabled_view_models = self.disabled_view_models
        model.item = item
        model_json = json.dumps(model.to_dict(session), default=str)

        title = f"Update {self.model_class.__name__}: \
            {item_name_func() if item_name_func else self.update_view_model.item_name()}"
        return render_template(
            self.update_template, model=model_json,
            title=title
        ), 200

    @provide_session
    def update_item_post(self, item_id, session=None):
        try:
            item = session.query(self.model_class).filter_by(id=item_id).one_or_none()
            field_types = get_auto_field_types(self.model_class, self.update_fields, self.field_types)
            for field in self.update_fields:
                res = NoUpdate()
                if field in self.disabled_update_fields:
                    continue
                if field_types[field].lower() == "relationship_many":
                    req_value = request.form.getlist(field)
                    rel_class = relationship_class(self.model_class, field)
                    res = UpdateValue(session.query(rel_class).filter(rel_class.id.in_(req_value)).all())
                elif field_types[field].lower() == "relationship_one":
                    req_value = request.form[field]
                    rel_class = relationship_class(self.model_class, field)
                    res = UpdateValue(session.query(rel_class).filter_by(id=req_value).one_or_none())
                elif field_types[field] == "file_upload":
                    if field in request.files and request.files[field].filename:
                        upload_file_name = secure_filename(request.files[field].filename)
                        file = request.files[field]
                        file.save(os.path.join("/tmp/flask_files", upload_file_name))
                        res = UpdateValue(upload_file_name)
                    else:
                        res = NoUpdate()
                else:
                    value = request.form.get(field, None)
                    match field_types[field].lower():
                        case "boolean":
                            value = request.form.get(field, False)
                            if value in ("true", "True", "1", 1):
                                res = UpdateValue(True)
                            else:
                                res = UpdateValue(False)
                        case "date":
                            res = UpdateValue(datetime.fromtimestamp(int(value) / 1000.0))
                        case "string":
                            res = UpdateValue(value)
                        case "select":
                            res = UpdateValue(value)
                        case "timestamp":
                            res = UpdateValue(datetime.fromisoformat(value))
                        case "float":
                            res = UpdateValue(float(value))
                        case "text":
                            res = UpdateValue(str(value))
                        case "integer":
                            res = UpdateValue(int(value))
                        case _:
                            res = NoUpdate()
                if res.is_updated():
                    setattr(item, field, res.value)

            session.add(item)
            flash("Successfully updated the item", "success")
            return redirect(self.list_view_model.search_url_func()), 302
        except Exception as e:
            self.log.error(e)
            flash("Error update the item", "danger")
            return redirect(self.list_view_model.detail_url_func(item_id=item_id)), 302

    @provide_session
    @check_permission("edit")
    def update_item(self, item_id, session=None):
        return request.method == "GET" and self.update_item_get(item_id, session=session) or self.update_item_post(
            item_id, session=session)

    @provide_session
    def delete_item_get(self, item, session=None):
        if not item:
            flash("Item not found", "danger")
            return abort(404)
        res = self.delete_view_model
        res.item = item
        return render_template(self.delete_template, model=json.dumps(res.to_dict(), default=str),
                               title=f"Delete {self.model_class.__name__}: {self.delete_view_model.item_name()}"), 200

    @provide_session
    @check_permission("delete")
    def delete_item_post(self, item, session=None):
        session.delete(item)
        flash("Successfully deleted the item", "success")
        return redirect(self.list_view_model.search_url_func()), 302

    @provide_session
    @check_permission("delete")
    def delete_item(self, item_id, session=None):
        item = session.query(self.model_class).filter_by(id=item_id).one_or_none()
        if request.method == "GET":
            return self.delete_item_get(item, session=session)
        else:
            return self.delete_item_post(item, session=session)

    @provide_session
    @check_permission("list")
    def detail_item(self, item_id, session=None):
        item = session.query(self.model_class).filter_by(id=item_id).one_or_none()
        if not item:
            flash("Item not found", "danger")
            return abort(404)
        res = self.detail_view_model
        res.item = item
        return render_template(
            self.detail_template, model=json.dumps(res.to_dict(), default=str),
            title=f"Details of {self.model_class.__name__}: {self.detail_view_model.item_name()}"
        ), 200


class SingleViewModel(ViewModel):

    def __init__(self, model_class, auth):
        super().__init__(model_class, auth)
        self.detail_url_func = self.detail_enabled() and outside_url_for(".detail_item")

    @provide_session
    def update_item(self, item_id=None, session=None):
        return request.method == "GET" and self.update_item_get(item_id, session=session) or self.update_item_post(
            item_id, session=session)

    @provide_session
    @check_permission("list")
    def detail_item(self, item_id=None, session=None):
        item = session.query(self.model_class).first()
        if not item:
            flash("Item not found", "danger")
            return abort(404)
        res = self.detail_view_model
        res.item = item
        return render_template(self.detail_template, model=json.dumps(res.to_dict(), default=str),
                               title=f"Details of {self.model_class.__name__}"), 200

    def register(self, flask_app_or_bp):
        if self.update_enabled():
            self.bp.route("/update", methods=["GET", "POST"])(self.auth(self.update_item))
        if self.detail_enabled():
            self.bp.route("/", methods=["GET"])(self.auth(self.detail_item))

        flask_app_or_bp.register_blueprint(self.bp)

    @provide_session
    def update_item_post(self, item_id, session=None):
        item = session.query(self.model_class).first()
        item_id = item_id or item.id
        _, status = super().update_item_post(item_id, session=session)
        if status == 302:
            return redirect(self.list_view_model.detail_url_func()), 302

    def update_item_get(self, item_id=None, item_name_func=None, session=None):
        item = session.query(self.model_class).first()
        item_id = item_id or item.id
        return super().update_item_get(item_id, item_name_func=lambda: "", session=session)


class EmptyViewModel:
    bp: Blueprint = None
    template_folder = "templates"
    static_folder = "static"

    def __init__(self, auth):
        self.auth = auth
        self.__class__.bp = Blueprint(
            self.__class__.__name__, __name__,
            url_prefix=f"{self.__class__.__name__}",
            template_folder=self.template_folder,
            static_folder=self.static_folder
        )

    def register(self, flask_app_or_bp):
        flask_app_or_bp.register_blueprint(self.bp)
