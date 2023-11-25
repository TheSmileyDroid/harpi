from flask import render_template
from flask.blueprints import Blueprint

bp = Blueprint("hub", __name__)


@bp.route("/")
def hub():
    return render_template("home.html")
