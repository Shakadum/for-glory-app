import os
from pydantic import BaseModel

class Settings(BaseModel):
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'change-me')
    ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))

    # DB
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///./forglory.db')

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str | None = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY: str | None = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET: str | None = os.getenv('CLOUDINARY_API_SECRET')

    # Agora
    AGORA_APP_ID: str | None = os.getenv('AGORA_APP_ID')

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = os.getenv('CORS_ALLOW_ORIGINS', '*').split(',')

settings = Settings()
