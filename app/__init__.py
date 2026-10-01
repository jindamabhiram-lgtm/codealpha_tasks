from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        instance_relative_config=True,
    )
    app.config.from_object(config_class)
    db.init_app(app)
    from app.auth import auth_bp
    from app.main import main_bp
    from app.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    with app.app_context():
        from app import models
        db.create_all()
    @app.errorhandler(404)
    def not_found(error):
        return ("<h1>404</h1><p>The page you requested was not found.</p>", 404)
    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return ("<h1>500</h1><p>Something went wrong on the server.</p>", 500)
    return app