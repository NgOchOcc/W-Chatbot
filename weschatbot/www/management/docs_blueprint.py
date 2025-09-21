from flask import Blueprint, send_from_directory
import os
import weschatbot

docs_bp = Blueprint("docs", __name__, url_prefix="/docs")

base_dir = os.path.dirname(weschatbot.__file__)
DOCS_DIR = os.path.abspath(f"{base_dir}/docs/build/html")


@docs_bp.route("/")
def index():
    return send_from_directory(DOCS_DIR, "index.html")


@docs_bp.route("/<path:filename>")
def serve_docs(filename):
    return send_from_directory(DOCS_DIR, filename)
