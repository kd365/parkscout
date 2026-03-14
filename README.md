# ParkScout

**AI-Powered Park Discovery for Families**

ParkScout is an iOS app that lets parents discover family-friendly parks in Fairfax County using natural language. Ask what your family needs — shaded, fenced, stroller-friendly, clean restrooms — and get trusted recommendations powered by a multi-agent RAG pipeline and crowdsourced parent reviews.

[![CI](https://github.com/kd365/parkscout/actions/workflows/ci.yml/badge.svg)](https://github.com/kd365/parkscout/actions/workflows/ci.yml)

**Demo:** [Watch on YouTube](https://youtu.be/BYw7raANiD0)

---

## Architecture

```
iOS App (SwiftUI)
    │
    ▼
FastAPI Backend (Python)
    │
    ├──► Multi-Agent RAG Pipeline
    │        ├── Generator ──► ChromaDB retrieval + Claude
    │        ├── Self-Critic ──► Confidence check (0.7 threshold) + retry
    │        └── Evaluator ──► LLM-as-Judge (Faithfulness, Relevance, Precision)
    │
    ├──► Weather Service ──► Real-time weather context injection
    ├──► Badge System ──► Crowdsourced quality verification
    └──► SQLite / Aurora pgvector ──► Users, reviews, badges, saved parks
```

### Multi-Agent RAG Pipeline

Three LLM-powered agents collaborate on every query:

1. **Generator** — LangChain + ChromaDB (k=4) retrieves relevant park data enriched with parent reviews, badge data, and weather context. Claude generates natural language recommendations.
2. **Self-Critic** — Confidence-scores the generator's response (0.0–1.0). If below 0.7, re-retrieves with expanded context (k=8) and regenerates.
3. **Evaluator (LLM-as-Judge)** — Scores faithfulness, answer relevance, and context precision. Runs in CI/CD to catch quality regressions before they ship.

### Gamification — Scout Badges

Parks earn verified badges when 3+ parents confirm a quality through reviews:

| Badge | Meaning |
|-------|---------|
| Solar Shield | Excellent shade coverage |
| The Fortress | Fully fenced playground |
| Golden Throne | Exceptionally clean restrooms |
| Tiny Explorer | Perfect for toddlers (1–3) |
| Smooth Sailing | Stroller-friendly paths |
| Splash Zone | Water play features |
| Paws Welcome | Dog-friendly with off-leash area |
| Feast Grounds | Great picnic facilities |

Badges have a full lifecycle: **earned → disputed → lost → re-earned**. Contradicting reviews (low ratings on badge-relevant qualities) automatically trigger disputes within a 90-day sliding window.

Users progress through tiers: **Tenderfoot → Trailblazer → Pathfinder → Park Legend** based on review count.

### Parent Score

A weighted composite rating built from parent observations:

| Category | Weight |
|----------|--------|
| Restrooms | 20% |
| Playground | 20% |
| Containment | 20% |
| Shade | 15% |
| Safety | 15% |
| Trails | 10% |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| iOS App | SwiftUI, iOS 17+, MapKit |
| Backend | Python, FastAPI, SQLAlchemy |
| RAG | LangChain, ChromaDB, Claude (langchain-anthropic) |
| Embeddings | Ollama nomic-embed-text |
| Database | SQLite (local), Aurora pgvector (AWS target) |
| IaC | AWS SAM — Lambda, API Gateway, RDS, S3, Cognito |
| CI/CD | GitHub Actions — 5 jobs, daily drift detection |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Ollama (for local embeddings)
- Xcode 15+ (for iOS app)
- `ANTHROPIC_API_KEY` environment variable

### Backend

```bash
cd lab3-ai-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Seed demo data
python scripts/seed_reviews.py

# Start server
export ANTHROPIC_API_KEY=your-key-here
uvicorn api.server:app --host 0.0.0.0 --port 8001
```

### iOS App

```bash
cd ios/ParksFinder
open ParksFinder.xcodeproj
# Build and run on iOS 17+ Simulator
```

The app defaults to `http://localhost:8001`. To reset onboarding for demo: Simulator > Device > Erase All Content and Settings.

---

## CI/CD Pipeline

A 5-job GitHub Actions pipeline runs on every push to `main`/`develop` and on PRs:

| Job | What it does |
|-----|-------------|
| **test** | pytest unit tests + RAG data quality tests |
| **lint** | Ruff linter on `api/` and `tests/` |
| **build-ios** | Xcode build verification on macOS runner |
| **rag-evaluation** | LLM-as-Judge scoring faithfulness, relevance, context precision |
| **security** | Bandit static security scan with artifact upload |

Daily scheduled runs (`0 6 * * *`) detect RAG quality drift.

---

## Project Structure

```
├── api/
│   ├── server.py              # FastAPI server + RAG pipeline
│   ├── models.py              # SQLAlchemy models (users, reviews, badges)
│   ├── schemas.py             # Pydantic request/response schemas
│   └── services/
│       ├── weather_service.py # Weather context injection
│       └── rag_evaluator.py   # LLM-as-Judge evaluation
├── ios/ParksFinder/           # SwiftUI iOS app
├── aws/
│   └── template.yaml          # SAM template (Lambda, API GW, RDS, S3, Cognito)
├── lambda/                    # AWS Lambda handlers
├── scripts/
│   └── seed_reviews.py        # Demo data seeder
├── tests/                     # pytest test suite
├── .github/workflows/
│   └── ci.yml                 # 5-job CI/CD pipeline
├── fetch_all_parks.py         # ArcGIS park data scraper (400+ parks)
├── ingest.py                  # ChromaDB ingestion script
└── main.py                    # CLI RAG demo
```

---

## Data Sources

- **Fairfax County ArcGIS API** — 400+ park records with coordinates, amenities, and metadata
- **Crowdsourced parent reviews** — 10 rating categories per review (shade, safety, containment, restrooms, etc.)
- **Real-time weather** — Injected into every RAG query for seasonally appropriate recommendations

---

## AWS Deployment

See [aws/README.md](aws/README.md) for SAM deployment instructions. The target architecture includes:

- 8 Lambda functions
- API Gateway with CORS
- RDS PostgreSQL (Aurora pgvector)
- 3 S3 buckets (data, photos, quarantine)
- Cognito User Pool with Apple Sign-In
- VPC with NAT Gateway

---

## Competition

ParkScout is a semi-finalist in the **AWS #10KAIdeas 2025** competition in the **Daily Life Enhancement** track.

- [Builder Center Article](https://community.aws/content/2w67IHFYluKY5q3a2mwMGqfLnlc/aideas-parkscout)
- [Demo Video](https://youtu.be/BYw7raANiD0)

---

## License

This project was built for the AWS AIdeas 2025 competition.
