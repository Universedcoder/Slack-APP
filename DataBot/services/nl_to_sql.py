import re

from langchain_groq import ChatGroq

from DataBot.core.config import settings


class NLToSQLGenerationError(Exception):
    """Raised when the LLM cannot produce usable SQL."""


SQL_SYSTEM_PROMPT = """You convert analytics questions into PostgreSQL queries.

Rules:
- Use only the table public.sales_daily.
- Available columns: date, region, category, revenue, orders, created_at.
- Return exactly one SQL query and nothing else.
- The query must be a read-only SELECT statement.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, GRANT, REVOKE, TRUNCATE, COMMENT, COPY, or multiple statements.
- Prefer explicit column names and meaningful aliases.
- If the user asks for totals or comparisons, aggregate appropriately.
- If the request does not specify a limit, omit LIMIT because the server will enforce one.
"""


def _extract_sql(content: object) -> str:
    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        text = " ".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()
    else:
        text = str(content).strip()

    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    return text.strip()


def generate_sql_for_question(question: str) -> str:
    if not question.strip():
        raise NLToSQLGenerationError("Please provide a question after `/ask-data`.")

    try:
        llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.0,
            groq_api_key=settings.groq_api_key,
            max_retries=2,
        )
        response = llm.invoke(
            [
                ("system", SQL_SYSTEM_PROMPT),
                ("human", question.strip()),
            ]
        )
    except Exception as exc:
        raise NLToSQLGenerationError(
            "I couldn't generate SQL for that question. Try rephrasing it more explicitly."
        ) from exc

    sql = _extract_sql(response.content)
    if not sql:
        raise NLToSQLGenerationError(
            "I couldn't generate SQL for that question. Try rephrasing it more explicitly."
        )

    return sql
