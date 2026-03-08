import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from DataBot.core.config import settings


async def verify_slack_request(request: Request) -> None:
    """Verify that the request was sent by Slack."""
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Slack signature headers",
        )

    if abs(int(time.time()) - int(timestamp)) > 60 * 5:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request timestamp too old",
        )

    if hasattr(request, "_body"):
        body = request._body
    else:
        body = await request.body()
        request._body = body

    base_string = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = "v0=" + hmac.new(
        settings.slack_signing_secret.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Slack signature",
        )
