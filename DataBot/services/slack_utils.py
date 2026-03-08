from typing import Any

from DataBot.core.config import settings
from DataBot.services.chart_utils import build_chart_image_url, is_chartable_result
from DataBot.services.db import QueryResult


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _format_table(columns: list[str], rows: list[dict[str, Any]], max_rows: int = 10) -> str:
    if not rows:
        return "No rows returned."

    preview_rows = rows[:max_rows]
    widths = {
        column: max(len(column), *(len(str(row.get(column, ""))) for row in preview_rows))
        for column in columns
    }

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns)
        for row in preview_rows
    ]
    return "\n".join([header, separator, *body])


def _base_response(
    text: str,
    response_type: str = "ephemeral",
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "response_type": response_type,
        "text": text,
    }
    if blocks:
        response["blocks"] = blocks
    return response


def build_empty_question_response() -> dict[str, Any]:
    return _base_response(
        "Usage: `/ask-data show revenue by region for 2025-09-01`",
        response_type="ephemeral",
    )


def build_invalid_command_response(command: str) -> dict[str, Any]:
    shown = command or "unknown"
    return _base_response(
        f"Unsupported slash command: `{shown}`. Use `/ask-data`.",
        response_type="ephemeral",
    )


def build_llm_failure_response(detail: str) -> dict[str, Any]:
    return _base_response(
        f":warning: {detail}",
        response_type="ephemeral",
    )


def build_sql_error_response(detail: str) -> dict[str, Any]:
    return _base_response(
        f":x: SQL execution failed.\n```{_truncate(detail, 500)}```",
        response_type="ephemeral",
    )


def build_generic_failure_response() -> dict[str, Any]:
    return _base_response(
        "Something went wrong while processing your data request.",
        response_type="ephemeral",
    )


def build_success_response(
    question: str,
    result: QueryResult,
    base_url: str | None = None,
) -> dict[str, Any]:
    if not result.rows:
        return _base_response(
            f"No results found for: {question}",
            response_type="ephemeral",
        )

    sql_block = _truncate(result.sql, settings.sql_preview_char_limit)
    table_block = _truncate(_format_table(result.columns, result.rows), 2500)
    summary = f"Found {len(result.rows)} row(s) for: {question}"

    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question*\n>{question}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*SQL*\n```{sql_block}```",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Results*\n```{table_block}```",
            },
        },
    ]

    if base_url and is_chartable_result(result):
        blocks.append(
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Trend",
                    "emoji": True,
                },
                "image_url": build_chart_image_url(base_url, result.sql),
                "alt_text": f"Trend chart for {question}",
            }
        )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Export CSV",
                        "emoji": True,
                    },
                    "action_id": "export_csv",
                    "value": result.sql[:2000],
                }
            ],
        }
    )

    return _base_response(summary, response_type="in_channel", blocks=blocks)
