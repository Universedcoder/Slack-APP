# DataBot

DataBot is a FastAPI backend that accepts a Slack slash command, converts natural-language questions into SQL with Groq via LangChain, runs the SQL against Supabase Postgres, and sends the result back to Slack.

## Features

- Slack `/ask-data` slash command support
- Slack request signature verification
- LangChain + Groq natural-language to SQL generation
- Supabase Postgres query execution
- Slack-friendly tabular responses and error messages
- Modular package layout for future growth

## Project Structure

```
DataBot/
├── main.py
├── routers/
│   └── slack.py
├── services/
│   ├── nl_to_sql.py
│   ├── db.py
│   └── slack_utils.py
└── core/
    ├── config.py
    └── security.py
tests/
├── test_db.py
├── test_slack.py
└── test_slack_utils.py
```

## Supported Slash Command

- `/ask-data show revenue by region for 2025-09-01`
- `/ask-data total orders per category`
- `/ask-data which region had the highest revenue on 2025-09-02`
- `/ask-data compare electronics revenue across all dates`

## Database Schema

DataBot is currently constrained to the `public.sales_daily` table:

- `date`
- `region`
- `category`
- `revenue`
- `orders`
- `created_at`

## Environment Variables

Create a local `.env` file based on `.env.example` and fill in your actual values:

```
SLACK_SIGNING_SECRET=your_slack_signing_secret_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
PORT=3000
QUERY_ROW_LIMIT=20
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the API:
```bash
uvicorn DataBot.main:app --reload --port 3000
```

3. Expose it to Slack:
```bash
ngrok http 3000
```

4. In your Slack app configuration, create a slash command:
   - Command: `/ask-data`
   - Request URL: `https://your-ngrok-url.ngrok-free.app/slack/events`

## Error Handling

- Empty question: ephemeral usage hint
- Invalid Slack signature: HTTP 403
- LLM generation failure: warning message asking the user to rephrase
- SQL execution failure: ephemeral error message with a code block

## Testing

```bash
pytest
```
