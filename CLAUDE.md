# ParkScout - AI-Powered Park Discovery for Families

## Project Overview
ParkScout is an iOS app (SwiftUI) for parents to discover family-friendly parks in Fairfax County using natural language. It uses a RAG pipeline (LangChain + ChromaDB) backed by parent-provided reviews and ingested park data from Fairfax County's ArcGIS API (400+ parks, 50+ ingested with embeddings).

## Architecture
- **Backend**: Python FastAPI server at `api/server.py` on port 8001
  - RAG pipeline: LangChain + ChromaDB (local) or Aurora pgvector (AWS target)
  - LLM: Claude via `langchain-anthropic` (requires `ANTHROPIC_API_KEY` env var)
  - Embeddings: Ollama `nomic-embed-text` (local)
  - Database: SQLite (`parks_finder.db`) with SQLAlchemy
  - Full REST API: /query, /parks, /users, /reviews, /weather, /badges, /auth
- **iOS App**: `ios/ParksFinder/` — SwiftUI, targets iOS 17+
  - Tab order: Parks, Explore (map), Discover (Park Picker wheel), Profile, Scout (AI chat)
  - Services: APIService, AuthService, LocationService, NetworkMonitor
  - Demo data fallback in `Models/DemoData.swift` — 10 real parks with accurate data
  - First-launch onboarding via `@AppStorage("hasSeenOnboarding")` fullScreenCover
  - Config: `Configuration.swift` — API base URL defaults to `http://localhost:8001`
- **AWS Target**: SAM template at `aws/template.yaml` — Lambda, API Gateway, DynamoDB, Aurora, S3, Cognito
- **CI/CD**: `.github/workflows/ci.yml` — pytest, ruff, iOS build, bandit security scan
- **Kiro Specs**: `.kiro/specs/parkscout-premium-aws-migration/` — 27 requirements, 6 phases (overly ambitious for competition, used for roadmap only)

## Key Files
- `api/server.py` — Main FastAPI server (54K lines, large file)
- `api/models.py` — SQLAlchemy models (users, parks, reviews, badges, tiers)
- `api/schemas.py` — Pydantic schemas
- `api/services/weather_service.py` — Weather integration
- `main.py` — CLI RAG demo (ChromaDB + Ollama llama3.2:1b)
- `fetch_all_parks.py` — ArcGIS park data scraper
- `ingest.py` — ChromaDB ingestion script
- `lambda/auth/handler.py` — AWS Lambda auth handler
- `lambda/ai_chat/handler.py` — AWS Lambda AI chat handler

## Server Startup
The server requires `ANTHROPIC_API_KEY` to start — it crashes in lifespan() at ChatAnthropic initialization.
To fix: either set the key or patch `api/server.py` lines 139-146 to make LLM optional.
```bash
cd /Users/kathleenhill/aico-delta_Fall2025/labs/CICDPipeline/lab3-ai-engine
source venv/bin/activate
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn api.server:app --host 0.0.0.0 --port 8001
```

## Competition Post (AIdeas 2025)
- Article at: `docs/aideas_competition_article.md`
- **App Category**: Daily Life Enhancement
- **Tags**: #aideas-2025, #daily-life-enhancement, #NAMER
- **Title format**: "AIdeas: ParkScout"
- **Required sections**: App Category, My Vision, Why This Matters, How I Built This, Demo, What I Learned
- **Need cover image** — something eye-catching
- **Demo**: Screenshots from iOS Simulator + screen recording recommended
- **Goal**: Get the most likes — visual engagement is key

## Known Issues & Fixes
- **Date decoding**: Python's `datetime.utcnow()` produces microsecond precision (6 digits) dates like `2026-02-21T02:41:05.965467`. Apple's `ISO8601DateFormatter` with `.withFractionalSeconds` only handles 3-digit milliseconds, causing silent decode failures for reviews, badges, and saved parks. Fixed by adding a `DateFormatter` fallback with `"yyyy-MM-dd'T'HH:mm:ss.SSSSSS"` format in `APIService.swift` decoder.
- **Model retirement**: `claude-3-5-haiku-20241022` was retired. Updated `LLM_MODEL` in `api/server.py` line 63 to `claude-haiku-4-5-20251001`.
- **Onboarding persistence**: `@AppStorage("hasSeenOnboarding")` persists across launches. To reset for demo: Simulator > Device > Erase All Content and Settings, or delete and reinstall the app.
- **Renamed Mom Score → Parent Score**: Changed in `ParkDetailView.swift` (`ParentScoreCard` struct) and onboarding text in `ContentView.swift`.

## Multi-Agent RAG Pipeline (Competition Framing)
- **Generator Agent**: LangChain + ChromaDB + Claude — retrieves park context and generates answers
- **Self-Critic Agent**: Confidence threshold 0.7 triggers re-retrieval with expanded context
- **Evaluator Agent (LLM-as-Judge)**: `api/services/rag_evaluator.py` — scores faithfulness, relevance, context precision
- Tests: `tests/test_rag_evaluation.py` (5 park-related test cases, `@pytest.mark.evaluation`)
- CI/CD: `.github/workflows/ci.yml` includes `rag-evaluation` job with daily drift detection cron

## Gamification System
- **8 Badge types** defined in `api/models.py` `BADGE_DEFINITIONS` — parks earn badges when 3+ parents confirm a quality
- **4 User tiers**: Tenderfoot (0-4), Trailblazer (5-14), Pathfinder (15-29), Park Legend (30+ reviews)
- **Parent Score**: Weighted composite — restrooms 20%, playground 20%, containment 20%, shade 15%, safety 15%, trails 10%
- Badge views: `Components/BadgeViews.swift` — BadgeChip, BadgeCard, BadgeRow, UserTierBadge, TierProgressCard

## Demo Data & Seeding
- `scripts/seed_reviews.py` — Creates 10 synthetic users, 15 reviews across 3 parks, 10 earned badges, 4 saved parks
- Parks with seeded data: Clemyjontri Park (5 badges), Burke Lake Park (2 badges), Frying Pan Farm Park (3 badges)
- Saved parks seeded for user_id=1 (used by iOS `SavedParksView`)
- Run: `cd lab3-ai-engine && source venv/bin/activate && python scripts/seed_reviews.py`

## Recent Changes (March 2026)
- Reordered iOS tabs: Parks first, Scout (AI chat) last
- Eliminated "More" menu — merged Saved Parks into Profile tab
- Added first-launch onboarding (fullScreenCover, opt-out via AppStorage) — shows every launch unless user toggles "Don't show again"
- Created DemoData.swift — 10 real Fairfax County parks for offline fallback
- ParksViewModel and ParkPickerViewModel fall back to demo data when server unreachable
- Updated competition article to be grounded in what's actually built vs aspirational
- Added animated splash screen in `ParksFinderApp.swift` — tree icon + "ParkScout" with spring animation, fades out after 1.8s
- Added earned badge chips on park list cards in `ParksListView.swift` — `ParkCard` fetches badges on appear
- Onboarding delayed 2.5s so splash screen finishes first
- Fixed date decoder in `APIService.swift` to handle Python microsecond-precision dates (6-digit fractional seconds)
- Seeded saved parks (4 parks) for demo profile via `seed_reviews.py`

## Remaining Demo Tasks
- Record screen recording in Simulator (File > Record Screen) using demo script
- Generate GenAI cover image for competition article
- Finalize `docs/aideas_competition_article.md` demo section with actual screenshots/video
- Map search doesn't filter/zoom to the searched park correctly (cosmetic, low priority)
