"""Sentry configuration for error tracking and monitoring"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from config import settings
import logging

def init_sentry():
    """Initialize Sentry SDK for error tracking"""

    # Only initialize Sentry if DSN is provided
    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)

    if not sentry_dsn:
        logging.info("Sentry DSN not configured, skipping Sentry initialization")
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=settings.ENVIRONMENT,

        # Performance monitoring
        traces_sample_rate=1.0 if settings.ENVIRONMENT == "production" else 0.1,

        # Release tracking
        release=f"para-autopilot@{getattr(settings, 'VERSION', '0.1.0')}",

        # Integrations
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint",  # Track by endpoint name
            ),
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors to Sentry
            ),
        ],

        # Error sampling
        sample_rate=1.0,  # Capture 100% of errors

        # PII configuration
        send_default_pii=False,  # Don't send user PII by default

        # Before send hook - filter sensitive data
        before_send=filter_sensitive_data,

        # Performance monitoring
        profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 0.0,
    )

    logging.info(f"Sentry initialized for environment: {settings.ENVIRONMENT}")


def filter_sensitive_data(event, hint):
    """Filter sensitive data before sending to Sentry"""

    # Remove passwords from request data
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if isinstance(data, dict):
            # Remove sensitive fields
            sensitive_fields = ['password', 'token', 'api_key', 'secret', 'anthropic_key']
            for field in sensitive_fields:
                if field in data:
                    data[field] = '[FILTERED]'

    # Remove API keys from headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        if isinstance(headers, dict):
            sensitive_headers = ['Authorization', 'X-API-Key', 'Cookie']
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = '[FILTERED]'

    return event


def capture_exception(error: Exception, context: dict = None):
    """Manually capture an exception with additional context"""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", context: dict = None):
    """Capture a message with optional context"""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: str = None):
    """Set user context for error tracking"""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email
    })
