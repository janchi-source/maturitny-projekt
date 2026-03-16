from flask import Blueprint, render_template
from flask_login import login_required


settings_bp = Blueprint("settings", __name__)


@settings_bp.route("", strict_slashes=False)
@settings_bp.route("/", strict_slashes=False)
@login_required
def index():
    return render_template("settings/index.html")
