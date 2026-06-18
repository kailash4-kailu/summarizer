# backend/app/config.py
"""Application configuration classes.

Separate development and production settings. Values are loaded from environment
variables where appropriate, with sensible defaults for local development.
"""

import os
from datetime import timedelta

class BaseConfig:
    # General Flask settings
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JSONIFY_PRETTYPRINT_REGULAR = True
    JSON_SORT_KEYS = False

    # Database – default to SQLite for local dev
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '../../instance/app.db'))}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Rate limiting defaults (per minute per IP)
    RATELIMIT_DEFAULT = "100 per minute"

    # Swagger configuration (flasgger)
    SWAGGER = {
        "title": "Summarizer API",
        "uiversion": 3,
        "openapi": "3.0.2",
    }

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV = "development"
    # Enable CORS for all origins in dev
    CORS_ORIGINS = "*"

class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV = "production"
    # In production, restrict CORS to specific origins (set via env var)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
    # Enforce HTTPS if behind a proxy (common on Render)
    PREFERRED_URL_SCHEME = "https"
