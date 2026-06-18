# backend/app/__init__.py
"""Flask application factory and extensions initialization.

This module creates the Flask app, registers extensions (SQLAlchemy, JWT, Limiter,
Swagger) and blueprints for routes.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Extensions (initialized later)
db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
swagger = Swagger()

def create_app():
    app = Flask(__name__)

    # Configuration
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        app.config.from_object("backend.app.config.ProductionConfig")
    else:
        app.config.from_object("backend.app.config.DevelopmentConfig")

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    swagger.init_app(app)

    # Register blueprints
    from backend.app.routes.api import api_bp
    from backend.app.routes.auth import auth_bp
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Simple health endpoint
    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
