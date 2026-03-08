from DataBot.services.chart_utils import (
    build_chart_image_url,
    build_chart_signature,
    generate_chart_png,
    is_chartable_result,
)
from DataBot.services.db import QueryResult
from DataBot.services.slack_utils import build_success_response


def test_chartable_result_detects_date_and_numeric_series() -> None:
    result = QueryResult(
        sql="SELECT date, revenue FROM public.sales_daily ORDER BY date LIMIT 20",
        columns=["date", "revenue"],
        rows=[
            {"date": "2025-09-01", "revenue": 100.0},
            {"date": "2025-09-02", "revenue": 120.0},
        ],
    )
    assert is_chartable_result(result) is True


def test_chartable_result_rejects_non_time_series() -> None:
    result = QueryResult(
        sql="SELECT region, revenue FROM public.sales_daily LIMIT 20",
        columns=["region", "revenue"],
        rows=[
            {"region": "North", "revenue": 100.0},
            {"region": "South", "revenue": 120.0},
        ],
    )
    assert is_chartable_result(result) is False


def test_generate_chart_png_returns_png_bytes() -> None:
    result = QueryResult(
        sql="SELECT date, revenue FROM public.sales_daily ORDER BY date LIMIT 20",
        columns=["date", "revenue"],
        rows=[
            {"date": "2025-09-01", "revenue": 100.0},
            {"date": "2025-09-02", "revenue": 120.0},
            {"date": "2025-09-03", "revenue": 90.0},
        ],
    )
    content = generate_chart_png(result)
    assert content.startswith(b"\x89PNG\r\n\x1a\n")


def test_build_success_response_adds_chart_block_for_date_series() -> None:
    result = QueryResult(
        sql="SELECT date, revenue FROM public.sales_daily ORDER BY date LIMIT 20",
        columns=["date", "revenue"],
        rows=[
            {"date": "2025-09-01", "revenue": 100.0},
            {"date": "2025-09-02", "revenue": 120.0},
        ],
    )
    payload = build_success_response(
        "show revenue across dates",
        result,
        base_url="https://example.ngrok-free.app",
    )
    image_blocks = [block for block in payload["blocks"] if block["type"] == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["image_url"] == build_chart_image_url(
        "https://example.ngrok-free.app",
        result.sql,
    )


def test_build_chart_signature_is_deterministic() -> None:
    sql = "SELECT date, revenue FROM public.sales_daily ORDER BY date LIMIT 20"
    assert build_chart_signature(sql) == build_chart_signature(sql)
