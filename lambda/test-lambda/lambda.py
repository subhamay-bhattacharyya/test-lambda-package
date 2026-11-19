"""
AWS Lambda boilerplate handler.

Entry point: lambda.handler
Runtime:     Python 3.x (standard library only, no third-party dependencies)
"""

import json

from structured_logging import inject_lambda_context, logger


def _response(status_code: int, body: dict) -> dict:
    """Build an API Gateway-compatible proxy response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


@inject_lambda_context
def handler(event, context):
    """
    Lambda entry point.

    Args:
        event:   Invocation payload (dict for JSON events, or service-specific shape).
        context: Runtime context object (request id, remaining time, etc.).

    Returns:
        A dict. Shape depends on the trigger; this returns a generic result.
    """
    logger.info("Received event", extra={"event": event})

    try:
        # ---- Your business logic goes here ----
        logger.info("Repo synced", extra={"repo": "owner/name", "count": 3})
        result = {"message": "Hello from Lambda!", "request_id": context.aws_request_id}
        # ---------------------------------------

        return _response(200, result)

    except ValueError as exc:
        # Expected, client-side problem (bad input).
        logger.warning("Validation error: %s", exc)
        return _response(400, {"error": str(exc)})

    except Exception:
        # Unexpected failure: log the full traceback and return a generic 500.
        logger.exception("Unhandled error")
        return _response(500, {"error": "Internal server error"})
