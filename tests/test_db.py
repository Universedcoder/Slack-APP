from DataBot.services.db import SQLExecutionError, apply_row_limit, ensure_safe_select_sql


def test_rejects_non_select_sql() -> None:
    try:
        ensure_safe_select_sql("DELETE FROM public.sales_daily")
    except SQLExecutionError as exc:
        assert "SELECT" in str(exc)
    else:
        raise AssertionError("Expected SQLExecutionError")


def test_appends_limit_when_missing() -> None:
    sql = apply_row_limit(
        "SELECT region, SUM(revenue) AS revenue FROM public.sales_daily GROUP BY region",
        20,
    )
    assert sql.endswith("LIMIT 20")


def test_preserves_existing_limit() -> None:
    sql = apply_row_limit("SELECT * FROM public.sales_daily LIMIT 5", 20)
    assert sql.endswith("LIMIT 5")
