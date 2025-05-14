from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from markupsafe import Markup

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)
    from .routes import main_bp  
    app.register_blueprint(main_bp)

    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ''
        return Markup(s.replace('\n', '<br>\n'))

    from app import routes, models
    return app