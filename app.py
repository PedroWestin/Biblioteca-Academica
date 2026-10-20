from flask import Flask

import config
from database import db
from presentation import filters
from presentation.routes import admin_bp, auth_bp, catalog_bp


def create_app(**overrides):
    app = Flask(__name__, template_folder="presentation/templates", static_folder="presentation/static")
    app.config.from_object(config)
    app.config.update(overrides)
    db.init_app(app)
    filters.register(app)
    for bp in (auth_bp, catalog_bp, admin_bp):
        app.register_blueprint(bp)
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
