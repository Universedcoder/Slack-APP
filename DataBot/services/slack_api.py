from typing import Any

import httpx

from DataBot.core.config import settings


class SlackAPIError(Exception):
    """Raised when a Slack API call fails."""

def _extract_error(payload: dict[str, Any]) -> str:
    return str(payload.get("error") or "unknown")


async def post_to_response_url(
    response_url: str,
    message: dict[str, Any],
) -> None:
    """Send a follow-up message to Slack using a response_url."""
    if not response_url:
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(response_url, json=message)
            response.raise_for_status()
    except httpx.HTTPError:
        return


async def ensure_channel_membership(channel_id: str) -> None:
    """Best-effort join for public channels before sharing uploaded files."""
    if not settings.slack_bot_token or not channel_id.startswith("C"):
        return

    auth_headers = {"Authorization": f"Bearer {settings.slack_bot_token}"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://slack.com/api/conversations.join",
            headers=auth_headers,
            json={"channel": channel_id},
        )
        payload = response.json()
        if payload.get("ok"):
            return
        return


async def upload_csv_to_slack(
    channel_id: str,
    csv_text: str,
    filename: str = "query_export.csv",
) -> None:
    """Upload a CSV string to a Slack channel using the Files v2 API.

    Flow (Slack Files v2):
      1. files.getUploadURLExternal  — obtain a pre-signed upload URL
      2. PUT/POST to the upload URL  — stream the file bytes
      3. files.completeUploadExternal — finalise and share to channel
    """
    if not settings.slack_bot_token:
        raise SlackAPIError("SLACK_BOT_TOKEN is not configured.")

    encoded = csv_text.encode("utf-8")
    auth_headers = {"Authorization": f"Bearer {settings.slack_bot_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        await ensure_channel_membership(channel_id)
        # Step 1: request a pre-signed upload URL
        r1 = await client.post(
            "https://slack.com/api/files.getUploadURLExternal",
            headers=auth_headers,
            data={"filename": filename, "length": str(len(encoded))},
        )
        r1_data = r1.json()
        if not r1_data.get("ok"):
            raise SlackAPIError(f"Could not obtain upload URL: {_extract_error(r1_data)}")

        upload_url: str = r1_data["upload_url"]
        file_id: str = r1_data["file_id"]

        # Step 2: upload the raw file content
        r2 = await client.post(
            upload_url,
            content=encoded,
            headers={"Content-Type": "text/csv; charset=utf-8"},
        )
        if r2.status_code not in (200, 204):
            raise SlackAPIError(
                f"File content upload failed (HTTP {r2.status_code})."
            )

        # Step 3: complete the upload and share to the channel
        r3 = await client.post(
            "https://slack.com/api/files.completeUploadExternal",
            headers=auth_headers,
            json={
                "files": [{"id": file_id, "title": filename}],
                "channel_id": channel_id,
            },
        )
        r3_data = r3.json()
        if not r3_data.get("ok"):
            raise SlackAPIError(f"Could not complete upload: {_extract_error(r3_data)}")
