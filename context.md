# Project Context

## Project Name
Slack Slash Command Backend (FastAPI)

## Purpose
Build a lightweight backend service that integrates with Slack Slash Commands.
When a user types a command like `/hello` in Slack, Slack sends an HTTP POST request to our backend.
The backend processes the request and returns a response message.

The initial implementation will support a single command:

/hello → returns "hello there"

The system should be designed so that additional commands can be added easily later.

---

## Technology Stack

Backend Framework:
FastAPI (Python)

Server:
Uvicorn (ASGI)

Language:
Python 3.10+

External Platform:
Slack API (Slash Commands)

Development Tool:
ngrok (for exposing local server to Slack)

Package Manager:
pip

---

## Slack Interaction Flow

1. User types `/hello` in Slack.
2. Slack sends an HTTP POST request to our backend endpoint.
3. Request payload is sent as `application/x-www-form-urlencoded`.
4. Backend parses request parameters.
5. Backend returns a JSON response.
6. Slack displays the response in the channel.

---

## Slack Request Example

Slack sends data similar to:

command=/hello
text=
user_id=U123456
user_name=mohnish
channel_id=C123456
channel_name=general

Content-Type:
application/x-www-form-urlencoded

---

## Slack Response Format

Backend must return JSON.

Example:

{
  "response_type": "in_channel",
  "text": "hello there"
}

response_type options:

in_channel
Message visible to everyone in the channel.

ephemeral
Message visible only to the command sender.

---

## Environment Variables

The system should support environment variables for configuration.

SLACK_SIGNING_SECRET
PORT

Future support:

OPENAI_API_KEY
DATABASE_URL

---

## Security

Slack requests should be verified using the Slack Signing Secret.

Validation steps:

1. Extract timestamp from header.
2. Extract Slack signature.
3. Create base string.
4. HMAC SHA256 validation.

Headers to verify:

X-Slack-Request-Timestamp
X-Slack-Signature

---

## Expected Project Structure

project-root

app/
    main.py
    routes/
        slack_commands.py
    services/
        slack_service.py
    core/
        config.py
        security.py

requirements.txt
README.md

---

## Dependencies

fastapi
uvicorn
python-multipart
python-dotenv
httpx

---

## Local Development

Run server:

uvicorn app.main:app --reload --port 3000

Expose using ngrok:

ngrok http 3000

Use the generated public URL as the Slack Request URL.

Example:

https://abc123.ngrok-free.app/hello

---

## Initial Feature Scope

Version 1 includes:

• Slack slash command support
• `/hello` command
• request validation
• clean modular architecture

Future versions may include:

• AI agent responses
• LangGraph integration
• RAG pipelines
• database storage
• Slack events
• interactive Slack messages