import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from DataBot.core.security import verify_slack_request
from DataBot.services.chart_utils import (
    generate_chart_png,
    is_chartable_result,
    verify_chart_signature,
)
from DataBot.services.csv_utils import generate_csv
from DataBot.services.db import SQLExecutionError, execute_read_only_query
from DataBot.services.nl_to_sql import NLToSQLGenerationError, generate_sql_for_question
from DataBot.services.slack_api import (
    SlackAPIError,
    post_to_response_url,
    upload_csv_to_slack,
)
from DataBot.services.slack_utils import (
    build_empty_question_response,
    build_generic_failure_response,
    build_invalid_command_response,
    build_llm_failure_response,
    build_sql_error_response,
    build_success_response,
)


router = APIRouter()


@router.post("/slack/events")
async def handle_slack_command(request: Request) -> JSONResponse:
    try:
        await verify_slack_request(request)
        form_data = await request.form()

        command = (form_data.get("command") or "").strip()
        question = (form_data.get("text") or "").strip()

        if command != "/ask-data":
            return JSONResponse(
                content=build_invalid_command_response(command),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not question:
            return JSONResponse(content=build_empty_question_response())

        sql = generate_sql_for_question(question)
        result = execute_read_only_query(sql)

        return JSONResponse(
            content=build_success_response(
                question=question,
                result=result,
                base_url=str(request.base_url).rstrip("/"),
            )
        )
    except HTTPException:
        raise
    except NLToSQLGenerationError as exc:
        return JSONResponse(content=build_llm_failure_response(str(exc)))
    except SQLExecutionError as exc:
        return JSONResponse(content=build_sql_error_response(str(exc)))
    except Exception:
        return JSONResponse(
            content=build_generic_failure_response(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def _do_csv_export(
    sql: str,
    channel_id: str,
    question: str,
    response_url: str,
) -> None:
    """Background task: re-execute SQL, generate CSV, upload to Slack."""
    try:
        await post_to_response_url(
            response_url,
            {
                "response_type": "ephemeral",
                "text": ":hourglass_flowing_sand: Preparing your CSV export...",
            },
        )
        result = execute_read_only_query(sql)
        csv_text = generate_csv(result)
        filename = question[:40].strip().replace(" ", "_") + ".csv" if question else "export.csv"
        await upload_csv_to_slack(channel_id, csv_text, filename)
        await post_to_response_url(
            response_url,
            {
                "response_type": "ephemeral",
                "text": f":white_check_mark: CSV uploaded as `{filename}`.",
            },
        )
    except SQLExecutionError as exc:
        await post_to_response_url(
            response_url,
            {
                "response_type": "ephemeral",
                "text": f":x: CSV export failed while re-running the query.\n```{str(exc)[:500]}```",
            },
        )
    except SlackAPIError as exc:
        await post_to_response_url(
            response_url,
            {
                "response_type": "ephemeral",
                "text": (
                    ":x: CSV export failed in Slack.\n"
                    f"```{str(exc)[:500]}```\n"
                    "If this mentions `not_in_channel` or `no_permission`, invite the app to the channel and reinstall it after updating scopes."
                ),
            },
        )


@router.post("/slack/actions")
async def handle_slack_actions(
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Handle Slack interactive component payloads (button clicks)."""
    try:
        await verify_slack_request(request)
        form_data = await request.form()

        payload_str = (form_data.get("payload") or "").strip()
        if not payload_str:
            return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)

        payload = json.loads(payload_str)

        if payload.get("type") != "block_actions":
            return JSONResponse(content={})
        channel_id: str = (payload.get("channel") or {}).get("id", "") or (
            payload.get("container") or {}
        ).get("channel_id", "")
        response_url: str = (payload.get("response_url") or "").strip()
        # Recover the original question text from the first section block.
        # Falls back to an empty string when not available.
        question: str = ""
        for block in payload.get("message", {}).get("blocks", []):
            if block.get("type") == "section":
                text_val = block.get("text", {}).get("text", "")
                if text_val.startswith("*Question*"):
                    question = text_val.replace("*Question*\n>", "", 1).strip()
                    break

        for action in payload.get("actions", []):
            if action.get("action_id") == "export_csv":
                sql = action.get("value", "").strip()
                if sql and channel_id:
                    background_tasks.add_task(
                        _do_csv_export,
                        sql,
                        channel_id,
                        question,
                        response_url,
                    )

        # Acknowledge immediately — Slack requires a 200 within 3 seconds.
        return JSONResponse(content={})
    except HTTPException:
        raise
    except Exception:
        return JSONResponse(content={}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/charts/query.png")
async def render_query_chart(sql: str, sig: str) -> Response:
    if not verify_chart_signature(sql, sig):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid chart signature.",
        )

    try:
        result = execute_read_only_query(sql)
    except SQLExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not is_chartable_result(result):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result is not chartable.",
        )

    return Response(content=generate_chart_png(result), media_type="image/png")
