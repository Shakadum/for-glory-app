import os
from dataclasses import dataclass


def _env_any(*names: str, default=None, required: bool = False) -> str:
    """Return the first non-empty env var from *names.

    Allows alias keys so Render/.env can use different naming without breaking the app.
    """
    for name in names:
        val = os.getenv(name)
        if val is not None and str(val).strip() != "":
            return val
    if required and default is None:
        raise RuntimeError(f"Missing required environment variable. Tried: {', '.join(names)}")
    return default


@dataclass(frozen=True)
class Settings:
    # Database
    DATABASE_URL: str = _env_any("DATABASE_URL", required=True)

    # JWT / Auth
    SECRET_KEY: str = _env_any("SECRET_KEY", required=True)
    # Render/env naming: ALGORITHM (legacy: JWT_ALGORITHM)
    ALGORITHM: str = _env_any("ALGORITHM", "JWT_ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_env_any("ACCESS_TOKEN_EXPIRE_MINUTES", default="60"))

    # Cloudinary (Render/env naming: CLOUDINARY_NAME/KEY/SECRET)
    CLOUDINARY_CLOUD_NAME: str = _env_any("CLOUDINARY_NAME", "CLOUDINARY_CLOUD_NAME", required=True)
    CLOUDINARY_API_KEY: str = _env_any("CLOUDINARY_KEY", "CLOUDINARY_API_KEY", required=True)
    CLOUDINARY_API_SECRET: str = _env_any("CLOUDINARY_SECRET", "CLOUDINARY_API_SECRET", required=True)

    # Agora (Render/env naming: AGORA_APP_CERTIFICATE)
    AGORA_APP_ID: str = _env_any("AGORA_APP_ID", required=True)
    AGORA_APP_CERT: str = _env_any("AGORA_APP_CERTIFICATE", "AGORA_APP_CERT", required=True)

    # Mail (optional - enable only if you use password reset / email notifications)
    MAIL_USERNAME: str = _env_any("MAIL_USERNAME", default="")
    MAIL_PASSWORD: str = _env_any("MAIL_PASSWORD", default="")
    MAIL_FROM: str = _env_any("MAIL_FROM", default="")


settings = Settings()
