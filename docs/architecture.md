# Orvyn Architecture (Sprint 2)

Diagrams are written in Mermaid, so GitHub renders them directly.

## 1. Components

```mermaid
flowchart LR
    U[User] --> CLI[main.py<br/>CLI loop]
    CLI --> A[agent.py<br/>Orvyn agent]
    A <--> G[Gemini<br/>Google AI platform]
    A --> T{{tools.py<br/>allowlist}}
    T --> APP[open_app<br/>allowed Windows apps]
    T --> W[get_weather<br/>Open-Meteo API]
    A --> R[resilience.py<br/>retry with backoff]
    A --> E[errors.py<br/>friendly messages and logging]
    C[config.py<br/>key, model, prompt version] --> A
    P[prompts/system_v2.md] --> C
```

**Rationale:** the agent is the only module that talks to Gemini; tools, retry and error handling are separate so each can be tested without the API.

## 2. Tool-use sequence

```mermaid
sequenceDiagram
    actor User
    participant CLI as main.py
    participant Agent as Orvyn agent
    participant LLM as Gemini
    participant Tool as tools.py
    User->>CLI: Open notepad
    CLI->>Agent: ask(text)
    Agent->>Agent: validate input (empty, too long)
    Agent->>LLM: history + system prompt v2
    LLM-->>Agent: tool call open_app("notepad")
    Agent->>Tool: open_app("notepad")
    Tool-->>Agent: "Notepad opened." or "ERROR: ..."
    Agent->>LLM: tool result
    LLM-->>Agent: final answer (reports ERROR honestly)
    Agent-->>CLI: reply
    CLI-->>User: Orvyn: reply
```

**Rationale:** tools return text instead of raising, so the model sees failures and can report them instead of claiming success.

## 3. Retry and error flow

```mermaid
flowchart TD
    S[Send request to Gemini] --> OK{Success?}
    OK -- yes --> R[Return reply]
    OK -- no --> C{Transient error?<br/>rate limit, timeout, 503}
    C -- no --> F[Friendly error message]
    C -- yes --> N{Attempts left?}
    N -- yes --> B[Wait 1s, 2s, ...] --> S
    N -- no --> F
```

**Rationale:** temporary problems should not force the user to retype; bad API keys and unknown errors fail fast.

## 4. UI wireframes for Sprint 4

Image files are in `docs/wireframes/`.

![Screen 1: Chat](wireframes/screen1_chat.png)

![Screen 2: Tool activity](wireframes/screen2_tool_activity.png)

![Screen 3: Settings](wireframes/screen3_settings.png)

Text versions of the same screens:

### Screen 1: Chat
```
+--------------------------------------------------+
| Orvyn                              [Settings]    |
+--------------------------------------------------+
| You:   Open notepad                              |
| Orvyn: Notepad opened.                           |
| You:   Weather in Lahore?                        |
| Orvyn: Weather in Lahore, Pakistan: ...          |
|                                                  |
+--------------------------------------------------+
| [ Type a message...                    ] [Send]  |
+--------------------------------------------------+
```

### Screen 2: Tool activity panel
```
+--------------------------------------------------+
| Tool activity                                    |
+--------------------------------------------------+
| 10:41  open_app(notepad)        OK     0.2 s     |
| 10:42  get_weather(Lahore)      OK     0.9 s     |
| 10:43  open_app(regedit)        REFUSED          |
+--------------------------------------------------+
```

### Screen 3: Settings
```
+--------------------------------------------------+
| Settings                                         |
+--------------------------------------------------+
| Model:           [ gemini-3.6-flash  v ]         |
| Prompt version:  [ v2 v ]                        |
| Allowed apps:    [x] Calculator [x] Notepad ...  |
| [Clear conversation]                [Save]       |
+--------------------------------------------------+
```
