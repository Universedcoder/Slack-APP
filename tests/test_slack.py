import hashlib
import hmac
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from DataBot.core.config import settings
from DataBot.main import app
from DataBot.services.db import QueryResult
from DataBot.services.nl_to_sql import NLToSQLGenerationError


client = TestClient(app)


def _signed_headers(body: str) -> dict[str, str]:
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


def test_invalid_signature_returns_403() -> None:
    response = client.post(
        "/slack/events",
        data={"command": "/ask-data", "text": "total orders"},
        headers={
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "v0=invalid",
        },
    )
    assert response.status_code == 403


def test_empty_question_returns_usage_hint() -> None:
    body = urlencode({"command": "/ask-data", "text": ""})
    response = client.post("/slack/events", content=body, headers=_signed_headers(body))
    payload = response.json()
    assert response.status_code == 200
    assert payload["response_type"] == "ephemeral"
    assert "Usage" in payload["text"]


def test_successful_query_flow(monkeypatch) -> None:
    monkeypatch.setattr(
        "DataBot.routers.slack.generate_sql_for_question",
        lambda question: "SELECT region, SUM(revenue) AS revenue FROM public.sales_daily GROUP BY region",
    )
    monkeypatch.setattr(
        "DataBot.routers.slack.execute_read_only_query",
        lambda sql: QueryResult(
            sql=f"{sql} LIMIT 20",
            columns=["region", "revenue"],
            rows=[{"region": "North", "revenue": 1200.5}],
        ),
    )

    body = urlencode({"command": "/ask-data", "text": "show revenue by region"})
    response = client.post("/slack/events", content=body, headers=_signed_headers(body))
    payload = response.json()

    assert response.status_code == 200
    assert payload["response_type"] == "in_channel"
    assert "Found 1 row" in payload["text"]
    assert payload["blocks"]


def test_llm_failure_returns_warning(monkeypatch) -> None:
    def _raise(_: str) -> str:
        raise NLToSQLGenerationError("Try rephrasing the request.")

    monkeypatch.setattr("DataBot.routers.slack.generate_sql_for_question", _raise)

    body = urlencode({"command": "/ask-data", "text": "show revenue"})
    response = client.post("/slack/events", content=body, headers=_signed_headers(body))
    payload = response.json()

    assert response.status_code == 200
    assert payload["response_type"] == "ephemeral"
    assert "rephrasing" in payload["text"].lower()
