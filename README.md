# 🧠 iZhinga AI Backend

A modular AI backend powering the **iZhinga AI Travel Platform**, designed to deliver **personalized travel itineraries**, **smart packing**, **authentic local experiences**, and **AI-powered trip assistance**.  
Built with **FastAPI**, **PostgreSQL**, and **modular AI engines**, it enables scalable, API-driven AI for travel intelligence.

---

## 🚀 Core Capabilities

- ✅ **FastAPI Framework** - High-performance async APIs  
- ✅ **AI Engine Architecture** - Modular engines for NLP, Itinerary, Budget, and more  
- ✅ **PostgreSQL + Redis** - Persistent storage and caching  
- ✅ **OpenAI Integration** - LLM-based reasoning and personalization  
- ✅ **Extensible AI Modules** - Plug-and-play modules for packing, shopping, journaling, etc.  
- ✅ **Async Execution** - Optimized for concurrent requests  
- ✅ **Dockerized Deployment** - Easy to build, scale, and run anywhere  

---

## 🏗️ Project Structure

```
app/
├── config/                    # Environment, database, and Redis configs
│   ├── settings.py
│   ├── database.py
│   └── redis_config.py
├── helpers/                   # Core utilities
│   ├── db_executor.py
│   ├── cache_helper.py
│   ├── ai_engine_loader.py    # Loads and executes AI modules dynamically
│   └── openai_helper.py
├── modules/                   # AI Feature Modules (1-11)
│   ├── nlp_input_processor.py
│   ├── budget_optimizer.py
│   ├── profile_intelligence.py
│   ├── packing_assistant.py
│   ├── shopping_discovery.py
│   ├── itinerary_generator.py
│   ├── safety_monitor.py
│   ├── voice_assistant.py
│   └── cultural_etiquette.py
├── engines/                   # Core AI Engines (1-9)
│   ├── nlp_input_engine.py
│   ├── itinerary_engine.py
│   ├── budget_engine.py
│   ├── realtime_data_engine.py
│   ├── local_intelligence_engine.py
│   ├── authenticity_filter_engine.py
│   ├── personalization_engine.py
│   ├── replanning_engine.py
│   └── feedback_learning_engine.py
├── routes/                    # API Endpoints
│   ├── itinerary.py
│   ├── packing.py
│   ├── profile.py
│   ├── shopping.py
│   └── health.py
└── main.py                    # Application entry point
```

---

## ⚙️ Setup

### 1️⃣ Environment Setup

Copy the environment example file and configure:
```bash
cp .env.example .env
```

Set your variables for:
- **PostgreSQL** → connection info  
- **Redis** → caching host/port  
- **OpenAI API Keys**  
- **App config** → name, host, debug mode  

---

### 2️⃣ Install Dependencies

Using **uv**:
```bash
uv sync
```

Or using **pip**:
```bash
pip install -e .
```

---

### 3️⃣ Database Initialization

Create schema tables:
```bash
psql -U postgres -d izhinga_ai -f schema.sql
```

---

### 4️⃣ Run the App

#### Locally:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### With Docker:
```bash
docker-compose up --build
```

---

## 🧩 Available APIs

| Category | Endpoint | Description |
|-----------|-----------|-------------|
| **Health** | `/health` | General health check |
| **Profile Intelligence** | `/profile/generate` | Builds dynamic user profile |
| **Itinerary Generator** | `/itinerary/generate` | Creates optimized trip plan |
| **Packing Assistant** | `/packing/generate` | Suggests smart packing list |
| **Shopping** | `/shopping/recommend` | Finds authentic local products |
| **Safety** | `/safety/monitor` | Monitors real-time safety updates |
| **Voice Assistant** | `/assistant/voice` | NLP + translation for voice queries |

---

## 🧠 AI Engine Overview

| Engine | Function | Description |
|--------|-----------|-------------|
| **Engine 1** | NLP Input Understanding | Parses free-form trip inputs |
| **Engine 2** | Itinerary Generation | Creates day-by-day travel plans |
| **Engine 3** | Budget Optimization | Adjusts trips per user budget |
| **Engine 4** | Real-Time Integration | Adapts to live events, weather |
| **Engine 5** | Local Intelligence | Finds authentic local experiences |
| **Engine 6** | Authenticity Filtering | Removes tourist traps |
| **Engine 7** | Personalization | Learns from profiles & feedback |
| **Engine 8** | Replanning | Updates itinerary dynamically |
| **Engine 9** | Continuous Learning | Improves via user feedback |

Each engine is callable as a standalone async function and can be orchestrated by the backend API.

---

## 🧰 Technology Stack

**Core Stack**
- FastAPI  
- PostgreSQL (asyncpg)  
- Redis (aioredis)  
- Docker, uv  

**AI Layer**
- OpenAI GPT-4o APIs  
- LangChain, Transformers  
- OpenCV, FFmpeg, Whisper (for CV/voice modules)

**External APIs**
- Google Maps / Places / Weather  
- Serp API, Yelp API, TripAdvisor API  

---

## 🔄 Data Flow Summary

1. **User Input** → Parsed by NLP Engine  
2. **Profile Module** → Generates preference vector  
3. **Itinerary Engine** → Builds plan using profile + budget  
4. **Packing & Shopping Modules** → Suggests essentials and buys  
5. **Safety Engine** → Monitors real-time travel risk  
6. **Journal Module** → Organizes media & trip stories  

All outputs are structured JSON, ready for persistence in PostgreSQL and caching via Redis.

---


## 🧪 Development Notes

- Modular design: Each AI engine and module runs independently.  
- Full async I/O for performance.  
- Database output stored per `user_id`.  
