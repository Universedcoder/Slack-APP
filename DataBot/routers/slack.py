from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from DataBot.core.security import verify_slack_request
from DataBot.services.db import SQLExecutionError, execute_read_only_query
from DataBot.services.nl_to_sql import NLToSQLGenerationError, generate_sql_for_question
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

        return JSONResponse(content=build_success_response(question=question, result=result))
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
