"""Logging configuration for euniforms application."""

import os
from euniforms.logging_utils import StructuredFormatter

# Logging configuration that can be included in Django settings
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            '()': StructuredFormatter,
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.getcwd(), 'logs', 'euniforms.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50 MB
            'backupCount': 5,
            'formatter': 'structured',
        },
        'security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.getcwd(), 'logs', 'euniforms_security.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'structured',
        },
        'performance': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.getcwd(), 'logs', 'euniforms_performance.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'structured',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'euniforms': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'euniforms.security': {
            'handlers': ['security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'euniforms.performance': {
            'handlers': ['performance'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}


def setup_logging_directories():
    """Create logging directories if they don't exist."""
    logs_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)


# Example Django settings integration:
"""
# In your Django settings.py:

from euniforms.logging_config import LOGGING_CONFIG, setup_logging_directories

# Set up logging directories
setup_logging_directories()

# Use the logging configuration
LOGGING = LOGGING_CONFIG

# Optional: Customize log levels based on environment
if DEBUG:
    LOGGING['loggers']['euniforms']['level'] = 'DEBUG'
else:
    LOGGING['loggers']['euniforms']['level'] = 'INFO'
"""