from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
import redis
from config import get_config

db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()
redis_client = None

def create_app():
    app = Flask(__name__)
    
    app.config.from_object(get_config())
    
    global redis_client
    redis_client = redis.Redis.from_url(app.config['REDIS_URL'])
    
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    from . import models
    from .routes import bp as main_bp
    from .auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    with app.app_context():
        db.create_all()
    
    return app