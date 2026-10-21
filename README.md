# Orvyn

Orvyn is a command-line AI assistant for Windows built with LangChain and Google Gemini.
Sprint 1 increment: chat with Gemini, open Calculator, get live weather, friendly error handling, automated tests.

## Setup (Windows)

```
git clone <repo-url>
cd Orvyn
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` and set `GOOGLE_API_KEY` (free key: https://aistudio.google.com/apikey). Never commit `.env`.

## Run

```
python -m src.main
```

Try: `What is an AI agent?`, `Open the calculator`, `What's the weather in Rawalpindi?`. Type `exit` to quit.

## Test

```
pytest
```

Unit tests mock the model and the network. To also run the live tests against the real Gemini API:

```
set RUN_LIVE_TESTS=1
pytest
```

## Project layout

| Path | Purpose |
|---|---|
| `src/main.py` | Command-line loop |
| `src/agent.py` | Gemini model, agent and conversation history |
| `src/tools.py` | Allowlisted tools (Calculator, weather) |
| `src/errors.py` | Friendly error messages and logging |
| `src/config.py` | Environment variables and prompt loading |
| `prompts/system_v1.md` | Versioned system prompt |
| `tests/` | Unit and live tests |

## Team workflow

- Branch names start with the Jira key, e.g. `ORV-3-tools`.
- Commit messages start with the Jira key, e.g. `ORV-3 Add live weather tool`.
- One pull request per story, reviewed by a different member.
- Prompt changes get a new file (`system_v2.md`) and an entry in the prompt version log.
