import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from DataBot.core.config import settings
from DataBot.main import app
from DataBot.services.csv_utils import generate_csv
from DataBot.services.db import QueryResult

client = TestClient(app)


# ---------------------------------------------------------------------------
# generate_csv unit tests
# ---------------------------------------------------------------------------


def test_generate_csv_header_and_rows() -> None:
    result = QueryResult(
        sql="SELECT region, revenue FROM public.sales_daily LIMIT 20",
        columns=["region", "revenue"],
        rows=[
            {"region": "North", "revenue": 1200.5},
            {"region": "South", "revenue": 800.0},
        ],
    )
    csv_text = generate_csv(result)
    lines = csv_text.strip().splitlines()
    assert lines[0] == "region,revenue"
    assert "North" in lines[1]
    assert "South" in lines[2]


def test_generate_csv_empty_rows() -> None:
    result = QueryResult(
        sql="SELECT region FROM public.sales_daily LIMIT 20",
        columns=["region"],
        rows=[],
    )
    csv_text = generate_csv(result)
    lines = csv_text.strip().splitlines()
    # Only the header row should be present
    assert len(lines) == 1
    assert lines[0] == "region"


def test_generate_csv_special_characters() -> None:
    result = QueryResult(
        sql="SELECT category FROM public.sales_daily LIMIT 20",
        columns=["category"],
        rows=[{"category": 'Electronics, "Gadgets"'}],
    )
    csv_text = generate_csv(result)
    # csv module should quote values containing commas/quotes
    assert "Electronics" in csv_text


# ---------------------------------------------------------------------------
# /slack/actions endpoint tests
# ---------------------------------------------------------------------------


def _signed_action_headers(body: str) -> dict[str, str]:
    timestamp = str(int(time.time()))
    base_string = f"v0:{timestamp}:{body}"
    signature = "v0=" + hmac.new(
        settings.slack_signing_secret.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
    }


def test_actions_invalid_signature_returns_403() -> None:
    payload = json.dumps({"type": "block_actions", "actions": []})
    body = urlencode({"payload": payload})
    response = client.post(
        "/slack/actions",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "v0=invalid",
        },
    )
    assert response.status_code == 403


def test_actions_unknown_type_returns_200() -> None:
    payload = json.dumps({"type": "view_submission"})
    body = urlencode({"payload": payload})
    response = client.post(
        "/slack/actions", content=body, headers=_signed_action_headers(body)
    )
    assert response.status_code == 200


def test_actions_export_csv_schedules_background_task(monkeypatch) -> None:
    """Button click is acknowledged immediately; upload runs in background."""
    uploaded: list[str] = []
    follow_ups: list[str] = []

    async def _mock_upload(channel_id: str, csv_text: str, filename: str = "export.csv") -> None:
        uploaded.append(channel_id)
    async def _mock_response_url(response_url: str, message: dict[str, str]) -> None:
        if response_url:
            follow_ups.append(message["text"])

    monkeypatch.setattr("DataBot.routers.slack.upload_csv_to_slack", _mock_upload)
    monkeypatch.setattr("DataBot.routers.slack.post_to_response_url", _mock_response_url)
    monkeypatch.setattr(
        "DataBot.routers.slack.execute_read_only_query",
        lambda sql: QueryResult(
            sql=sql,
            columns=["region", "revenue"],
            rows=[{"region": "North", "revenue": 100.0}],
        ),
    )

    action_payload = {
        "type": "block_actions",
        "channel": {"id": "C999"},
        "response_url": "https://example.com/response",
        "message": {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Question*\n>show revenue by region",
                    },
                }
            ]
        },
        "actions": [
            {
                "action_id": "export_csv",
                "value": "SELECT region, SUM(revenue) AS revenue FROM public.sales_daily GROUP BY region LIMIT 20",
            }
        ],
    }
    body = urlencode({"payload": json.dumps(action_payload)})
    response = client.post(
        "/slack/actions", content=body, headers=_signed_action_headers(body)
    )
    assert response.status_code == 200
    assert uploaded == ["C999"]
    assert len(follow_ups) == 2
    assert "Preparing your CSV export" in follow_ups[0]
    assert "CSV uploaded as" in follow_ups[1]
