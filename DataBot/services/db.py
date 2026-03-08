from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any

import psycopg
from psycopg.rows import dict_row

from DataBot.core.config import settings


READ_ONLY_PREFIXES = ("select",)
FORBIDDEN_SQL_PATTERNS = (
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\btruncate\b",
    r"\bcomment\b",
    r"\bcopy\b",
    r"--",
    r"/\*",
)


class SQLExecutionError(Exception):
    """Raised when generated SQL cannot be safely executed."""


@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]


def normalize_sql(sql: str) -> str:
    cleaned = " ".join(sql.strip().split())
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def ensure_safe_select_sql(sql: str) -> str:
    cleaned = normalize_sql(sql)
    lowered = cleaned.lower()

    if not lowered.startswith(READ_ONLY_PREFIXES):
        raise SQLExecutionError("Only a single SELECT statement is allowed.")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, lowered):
            raise SQLExecutionError("Generated SQL contained unsupported or unsafe operations.")

    if ";" in cleaned:
        raise SQLExecutionError("Multiple SQL statements are not allowed.")

    return cleaned


def apply_row_limit(sql: str, limit: int) -> str:
    if re.search(r"\blimit\s+\d+\b", sql, flags=re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {limit}"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def execute_read_only_query(sql: str) -> QueryResult:
    if not settings.database_url:
        raise SQLExecutionError("DATABASE_URL is not configured.")

    safe_sql = apply_row_limit(ensure_safe_select_sql(sql), settings.query_row_limit)

    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(safe_sql)
                rows = cursor.fetchall()
                columns = [column.name for column in cursor.description or []]
    except psycopg.Error as exc:
        raise SQLExecutionError(str(exc).strip()) from exc

    serialized_rows = [
        {key: _serialize_value(value) for key, value in row.items()}
        for row in rows
    ]

    return QueryResult(sql=safe_sql, columns=columns, rows=serialized_rows)
