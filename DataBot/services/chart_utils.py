import hashlib
import hmac
import io
from datetime import date, datetime
from decimal import Decimal
from numbers import Number
from urllib.parse import urlencode

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from DataBot.core.config import settings
from DataBot.services.db import QueryResult


DATE_COLUMN_NAMES = {"date", "day"}


def _is_date_like(value: object) -> bool:
    if isinstance(value, datetime):
        return True
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    return False


def _is_numeric_like(value: object) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float, Decimal, Number))


def _find_date_column(result: QueryResult) -> str | None:
    for column in result.columns:
        if column.lower() in DATE_COLUMN_NAMES:
            return column

    for column in result.columns:
        values = [row.get(column) for row in result.rows if row.get(column) is not None]
        if values and all(_is_date_like(value) for value in values):
            return column

    return None


def _find_numeric_column(result: QueryResult, date_column: str) -> str | None:
    for column in result.columns:
        if column == date_column:
            continue
        values = [row.get(column) for row in result.rows if row.get(column) is not None]
        if values and all(_is_numeric_like(value) for value in values):
            return column
    return None


def is_chartable_result(result: QueryResult) -> bool:
    if len(result.rows) < 2:
        return False

    date_column = _find_date_column(result)
    if not date_column:
        return False

    return _find_numeric_column(result, date_column) is not None


def extract_chart_series(result: QueryResult) -> tuple[list[str], list[float], str]:
    date_column = _find_date_column(result)
    if not date_column:
        raise ValueError("Result does not contain a chartable date column.")

    value_column = _find_numeric_column(result, date_column)
    if not value_column:
        raise ValueError("Result does not contain a chartable numeric column.")

    labels = [str(row.get(date_column, "")) for row in result.rows[: settings.chart_point_limit]]
    values = [float(row.get(value_column, 0)) for row in result.rows[: settings.chart_point_limit]]
    return labels, values, value_column


def generate_chart_png(result: QueryResult) -> bytes:
    labels, values, value_label = extract_chart_series(result)

    figure, axis = plt.subplots(figsize=(5.2, 2.6), dpi=140)
    axis.plot(labels, values, color="#2563eb", linewidth=2, marker="o", markersize=3)
    axis.fill_between(labels, values, color="#bfdbfe", alpha=0.35)
    axis.set_ylabel(value_label.replace("_", " ").title(), fontsize=8)
    axis.tick_params(axis="x", labelsize=7, rotation=35)
    axis.tick_params(axis="y", labelsize=7)
    axis.grid(axis="y", linestyle="--", alpha=0.25)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()

    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def build_chart_signature(sql: str) -> str:
    return hmac.new(
        settings.slack_signing_secret.encode("utf-8"),
        sql.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_chart_signature(sql: str, signature: str) -> bool:
    return hmac.compare_digest(build_chart_signature(sql), signature)


def build_chart_image_url(base_url: str, sql: str) -> str:
    query = urlencode({"sql": sql, "sig": build_chart_signature(sql)})
    return f"{base_url.rstrip('/')}/charts/query.png?{query}"
