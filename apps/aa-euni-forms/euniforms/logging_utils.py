"""Logging utilities for structured logging in euniforms."""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add extra fields if available
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_entry['stack_info'] = self.formatStack(record.stack_info)

        return json.dumps(log_entry, default=str)


class EuniformsLogger:
    """Centralized logging utility for euniforms with structured logging support."""

    def __init__(self, name: str):
        """Initialize logger with given name."""
        self.logger = logging.getLogger(name)

    def _log_with_context(self, level: int, message: str, **context):
        """Log message with additional context."""
        # Create extra dict for structured data
        extra = {'extra': context} if context else {}
        self.logger.log(level, message, extra=extra)

    def info(self, message: str, **context):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **context)

    def warning(self, message: str, **context):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **context)

    def error(self, message: str, exc_info=False, **context):
        """Log error message with context."""
        if exc_info:
            self.logger.error(message, exc_info=True, extra={'extra': context})
        else:
            self._log_with_context(logging.ERROR, message, **context)

    def debug(self, message: str, **context):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **context)

    def form_created(self, form_id: int, title: str, created_by_id: int, **context):
        """Log form creation event."""
        self.info(
            "Form created",
            event_type="form_created",
            form_id=form_id,
            form_title=title,
            created_by_id=created_by_id,
            **context
        )

    def form_submitted(self, form_id: int, response_id: int, user_id: Optional[int],
                      submitter_name: str, **context):
        """Log form submission event."""
        self.info(
            "Form response submitted",
            event_type="form_submitted",
            form_id=form_id,
            response_id=response_id,
            user_id=user_id,
            submitter_name=submitter_name,
            **context
        )

    def discord_webhook_sent(self, form_id: int, response_id: int, webhook_url: str,
                           success: bool, **context):
        """Log Discord webhook attempt."""
        level = logging.INFO if success else logging.WARNING
        message = "Discord webhook sent successfully" if success else "Discord webhook failed"

        self._log_with_context(
            level,
            message,
            event_type="discord_webhook",
            form_id=form_id,
            response_id=response_id,
            webhook_url=webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url,
            success=success,
            **context
        )

    def permission_denied(self, user_id: Optional[int], username: str, action: str,
                         resource: str, **context):
        """Log permission denied events for security monitoring."""
        self.warning(
            f"Permission denied: {action} on {resource}",
            event_type="permission_denied",
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            **context
        )

    def database_query_slow(self, query_time: float, query: str, **context):
        """Log slow database queries for performance monitoring."""
        if query_time > 1.0:  # Log queries taking more than 1 second
            self.warning(
                "Slow database query detected",
                event_type="slow_query",
                query_time=query_time,
                query=query[:200] + '...' if len(query) > 200 else query,
                **context
            )

    def user_activity(self, user_id: Optional[int], username: str, action: str, **context):
        """Log user activity for audit trails."""
        self.info(
            f"User activity: {action}",
            event_type="user_activity",
            user_id=user_id,
            username=username,
            action=action,
            **context
        )


# Global logger instance
app_logger = EuniformsLogger('euniforms')


def get_logger(name: str = 'euniforms') -> EuniformsLogger:
    """Get a logger instance for the given name."""
    return EuniformsLogger(name)


def log_user_action(user, action: str, **context):
    """Convenience function to log user actions."""
    app_logger.user_activity(
        user_id=user.id if user and hasattr(user, 'id') else None,
        username=getattr(user, 'username', 'anonymous'),
        action=action,
        **context
    )


def log_permission_denied(user, action: str, resource: str, **context):
    """Convenience function to log permission denied events."""
    app_logger.permission_denied(
        user_id=user.id if user and hasattr(user, 'id') else None,
        username=getattr(user, 'username', 'anonymous'),
        action=action,
        resource=resource,
        **context
    )


class PerformanceMiddleware:
    """Middleware to log slow requests for performance monitoring."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import time
        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time

        # Log slow requests (>2 seconds)
        if duration > 2.0:
            app_logger.warning(
                "Slow request detected",
                event_type="slow_request",
                path=request.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code,
                user_id=request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
            )

        return response