# Architecture (extension to README)

This document focuses on runtime behavior, tool execution, and data lifecycle.


## Project Structure

```
backend/ 
    services/ 
        tools/              - implementation of all tools + tool descriptions
        agent_tools.py      - handle agent tools 
        agent_utils.py      - helper agent functions
        openai_client.py    - client wrapper and system prompt injection
        openai_service.py   - main ai service, tools executions (singelton design pattern)
        safety_guards.py    - detector for policy violation
    routes/ 
        auth.py             - authentication flow endpoint API
        chat.py             - chat flow endpoint API
    domain/                
        config.py           - application configuration file
        constants.py        - constants from application
        enums.py            - enums
        messages.py         - handles messages, centralized multilanguage handling
        logging_config.py   - logger configuration
    repositories/           
        medication_repository.py - medications database managment
        user_repository.py  - users database managment
    tool_framwork/
        executor.py         - tool for execution of agent functions
        inference.py        - argument inference helper functions
        messages.py         - user-facing messages for missign parameters
        parser.py           - tools call parsing and calls tracking
        registry.py         - tool schema registry for agent
        runner.py           - runs tools, yields execution and build tool messages
        stream.py           - stream helper to yield chuncks for straming message response
        validators.py       - validation tool for argument validation
    prompts/ 
        system_prompt       - builds the system prompt and error messages
    utils/
        db_context.py       - db session helper
        language.py         - language detector 
        response.py         - error handling decorator for agent tools
        security.py         - security, pii masking
    data_source/
        base.py             - abstract class for data handlers normalization of 
                              text + levenshtein distance for misspeling errors   
        medications_api.py  - data source implemetation for json file (api return)
        medication_db.py    - data source for database
    app.py                  - agent main application
     
frontend/                   - next.js frontend
    src/app/                - pages (chat, login)
    src/components/         - react components
    public/                 - static assets

open_ai_tool_schemas/       

data/                      
    medications.json        - 5 demo medications
    demo_users.json         - 10 demo users
    demo_prescriptions.json - sample prescriptions
    pharmacy_locations.json - demo locations 
docs/                      
    screenshots/            - conversation evidence
    EVALUATION_PLAN.md
docker-compose.yml          - container orchestration
Dockerfile                  - backend container

```

## Constraints and goals
- Vanilla OpenAI API, streaming responses, stateless agent
- Factual, label-based answers only; no medical advice or purchase encouragement
- Tool-driven workflows for medications, inventory, prescriptions, and pharmacy locations

## Runtime pipeline
1. `POST /chat/completions` receives the user message, language, and optional user id.
2. Safety guard evaluates the message for medical-advice requests and refusal triggers.
3. System prompt is built with policy rules plus the medication knowledge base subset.
4. The streaming client sends the request to OpenAI and yields tokens to the frontend.
5. Tool-call parts are parsed, validated against schemas, and executed.
6. Tool results are appended as tool messages and the model continues the response.
7. Stream ends with a final assistant message plus tool-call trace data.

## Tool execution model
- Schemas are loaded from `open_ai_tool_schemas/` and registered at startup.
- A single executor routes tool names to tool handlers.
- Tool handlers return structured results and user-facing messages from a shared dictionary.
- Tool errors use a common decorator to standardize error responses.

## Data lifecycle
- Users and prescriptions live in sqlite and are seeded from json on startup or via `scripts/build_databases.py`.
- Medications exist in json and optional sqlite, with a data source toggle.
- Inventory is served by the demo inventory service and queried by `check_stock`.
- Pharmacy locations are static json and include optional alias cities for nearest-city fallback.

## Localization
- Language detection happens per request unless a session language is explicitly set.
- User-facing tool messages come from a centralized dictionary.
- Rtl layout is handled in the frontend; content is localized in the backend.