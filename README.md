[![tests](https://github.com/mohsinyousafzai0127/orvyn/actions/workflows/tests.yml/badge.svg)]()
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

## Run Orvyn

**Easiest (Windows):** double-click `orvyn.bat` in the project folder. It opens a console window, activates
the virtual environment and starts Orvyn. If `.venv` is missing it tells you how to create it.

**From a terminal** (Windows Terminal, cmd or the VS Code terminal), inside the project folder:

cmd:
```
.venv\Scripts\activate.bat
python -m src.main
```

PowerShell:
```
.venv\Scripts\Activate.ps1
python -m src.main
```

Commands inside Orvyn: `/help`, `/tools`, `/clear`, `/exit`.
Orvyn shows each tool call as it happens. Whenever it wants to write a file in the `workspace/` folder it asks
you first, and only `y` or `yes` allows it.

Try: `Compare the weather in Rawalpindi and Lahore and save a summary to weather.txt`

## Test

```
pytest
```

Unit tests mock the model and the network. To also run the live tests against the real Gemini API:

```
PowerShell:
$env:RUN_LIVE_TESTS = "1"
pytest

Command Prompt:
set RUN_LIVE_TESTS=1
pytest


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
