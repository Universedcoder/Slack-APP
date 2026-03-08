from DataBot.services.db import QueryResult
from DataBot.services.slack_utils import build_sql_error_response, build_success_response


def test_sql_error_response_uses_code_block() -> None:
    payload = build_sql_error_response('column "foo" does not exist')
    assert payload["response_type"] == "ephemeral"
    assert "```" in payload["text"]


def test_success_response_contains_blocks() -> None:
    payload = build_success_response(
        "show revenue by region",
        QueryResult(
            sql="SELECT region, SUM(revenue) AS revenue FROM public.sales_daily GROUP BY region LIMIT 20",
            columns=["region", "revenue"],
            rows=[{"region": "East", "revenue": 100.0}],
        ),
    )
    assert payload["response_type"] == "in_channel"
    assert len(payload["blocks"]) == 4  # question, sql, results, export button
