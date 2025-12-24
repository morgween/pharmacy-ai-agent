# Pharmacy AI Agent
## Overview

Real-time conversational AI pharmacy assistant for a retail pharmacy chain. Agent will serve customers through chat and using data from pharmacy internal system (can handle both API and DB access). Agent works with vanilla OpenAI API. 

**Key Features:**
- Streaming responses with GPT-5
- Stateless architecture
- 7 custom tools for medication management
- Multilanguage support (Hebrew/Russian/Arabic/English) 
- Authentithication system for user-specific access, can be used without loggin in
- Strict policy adherence (Agent is not a doctor and want provide any: medical advise, diagnosis)
- Tool call visualization in UI with VERSEL AI SDK

## Additional documentation
### Screenshots evidence 
[Screenshots folder](docs/screenshots)
### Additional documentation files
[Architecture overview](docs/ARCHITECTURE.md)

[Model evaluation plan](docs/EVALUATION_PLAN.md)

[Multi Flows](docs/FLOWS.md)
## Architecture

### System Components

```
Frontend (Next.js): 
    - Chat UI with streaming support (real-time answers)
    - Authentication window
    - Language menu for 4 supported languages
    - Window with tools call chain

Backend (Python - FastAPI):
    OpenAI Service (api):
        - Streaming chat completion
        - Tool loading from JSON schemas
        - Safety guards with prompt engineering + guard rails 
    Tool Framework (7 different tools)
        - get_medication_info - provides information about the medication (how to take, prescription, active components ... )
        - search_by_ingredient - Provides list of medication with required ingredient (search alternative for missing medication)
        - resolve_medication_id - internal tool to faster look up medication in medication stock API and to provide information about prescription
        - get_user_prescriptions - check if user have active prescription, uses resolve medication id to check the medication and provide usage information
        - check_stock - API call to inventory API, will provide availability of medication in stock
        - get_handling_warnings - retrieve medication warnings and label information
        - find_nearest_pharmacy - retrieve nearest pharmacy location
    Data Sources:
        - User DB - handles users data base with login information
        - Medication DB - handles medication database 
        - Prescriptions DB - handles user-based prescriptions
        - Locations DB - handles nearest pharmacy location
        - Inventory API - server which handles current available stock information.
```

### Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (REST API + SSE streaming)
- OpenAI Python SDK
- SQLite (access with SQLAlchemy)
- Pydantic for validation

**Frontend:**
- Next.js 14 (React 18)
- TypeScript
- Tailwind CSS
- Server-Sent Events for streaming

**Infrastructure:**
- Docker & Docker Compose (multi container for frontend, backend and medications API)

## Quick Start

### Prerequisites

- Docker Desktop installed and configured
- OpenAI API key (GPT-5 access)
- 4GB RAM minimum
- Ports 3000, 8000, 8001 - may be changed in .env

### Installation

```bash
# Clone repository
git clone https://github.com/morgween/pharmacy-ai-agent.git
cd pharmacy-ai-agent

# Configure environment
cp .env.example .env

# Edit .env and add your openAI API key (mandatory) and other configuration if needed:
nano .env
#OPENAI_API_KEY=your_actual_api_key_here

# build the project with 
docker compose build --no-cache
docker compose up -d
```

This will start:
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:3000
- Inventory Service: http://localhost:8001

1. **Access the application**

Open your browser at: **http://localhost:3000**

Can start chatting or sign in as one of demo users (10 demo users credentials are available - see [demo_user](data/demo_users.json))

## Features

### 1. Multi-Step Workflows

Chain of tool calls and responses.
See `tests/FLOWS.md` for detailed flow definitions.

### 2. Seven Custom Tools

* [get_medication_info](backend\services\tools\medication_tools.py#L172) Retrieve detailed medication information
* [resolve_medication_id](backend\services\tools\medication_tools.py#L108) Convert medication name to internal ID 
* [check_stock](backend\services\tools\inventory_tools.py#L22) Verify medication stock availability 
* [search_by_ingredient](backend\services\tools\medication_tools.py#L21) Find medications by active ingredient 
* [get_user_prescriptions](backend\services\tools\prescription_tools.py#L26) Get user's prescription list (requires auth) 
* [get_handling_warnings](backend\services\tools\handling_tools.py#L20) Retrieve medication warnings 
* [find_nearest_pharmacy](backend\services\tools\pharmacy_tools.py#L22) Locate nearby pharmacy addresses
#### For documentation check linked files
### 3. Policy Enforcement
The agent strictly adheres to a no-medical-advice policy:
**Agent can**
- Provide factual medication information
- Confirm prescription requirements (legal facts)
- Check stock availability
- Locate pharmacy addresses

**Agent can't**
- Give medical advice or recommendations
- Suggest dosage changes
- Diagnose conditions
- Advise on drug interactions for specific users
- Encourage purchases

### 4. Multilingual Support

- **Supported Languages:** English, Hebrew, Russian, Arabic
- **Auto-detection:** Detects user language automatically
- **RTL Support:** Right-to-left layout for Hebrew/Arabic
- **All tools work identically** across all languages

## Dev server without docker

Run in three different windows(better) or add && for background run

```bash
# install dependencies
pip install -r requirements.txt

# initialize database
python scripts/init_database.py

# run agent server
cd backend
uvicorn app:app --reload --port 8000

# run inventory server
cd demo_server_app
uvicorn app:app --port 8001

# run frontend
cd frontend
npm install
npm run dev
```
