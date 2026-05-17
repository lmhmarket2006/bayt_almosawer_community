import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-later")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///community.db")

    # Railway أحيانًا يعطي رابط PostgreSQL يبدأ بـ postgres://
    # و SQLAlchemy يحتاج postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False