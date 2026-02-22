import logging
import logging.config
import os


def setup_logging() -> None:
    """Configure app + uvicorn logging with sane defaults.

    - JSON logs are possible later; for now we keep console logs readable.
    - Respect LOG_LEVEL env.
    """
    level = os.getenv('LOG_LEVEL', 'INFO').upper()

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            }
        },
        'loggers': {
            '': {'handlers': ['console'], 'level': level},
            'uvicorn': {'handlers': ['console'], 'level': level, 'propagate': False},
            'uvicorn.error': {'handlers': ['console'], 'level': level, 'propagate': False},
            'uvicorn.access': {'handlers': ['console'], 'level': level, 'propagate': False},
        },
    }
    logging.config.dictConfig(config)
