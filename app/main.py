from app.core.logging import setup_logging

setup_logging()

# Importing the app after logging ensures early logs are captured
from app.api.routes import app  # noqa: E402

__all__ = ['app']
