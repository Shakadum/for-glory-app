import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import cloudinary  # type: ignore
except Exception:  # pragma: no cover
    cloudinary = None


def init_cloudinary() -> None:
    """Initialize Cloudinary from env.

    If the Cloudinary SDK isn't installed, the app can still run, but upload endpoints will fail.
    """
    if cloudinary is None:
        logger.warning('Cloudinary SDK not installed. Upload endpoints will fail until you add cloudinary to requirements.')
        return

    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
        logger.info('Cloudinary configured (cloud_name=%s)', settings.CLOUDINARY_CLOUD_NAME)
    else:
        logger.warning('Cloudinary NOT configured (missing env vars). Upload endpoints will fail.')
