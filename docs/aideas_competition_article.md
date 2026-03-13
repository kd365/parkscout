# AIdeas: ParkScout

<!-- Cover Image: [Add eye-catching cover image here — iOS app screenshot montage or hero shot of the AI chat recommending parks] -->

**App Category:** Daily Life Enhancement

**Tags:** #aideas-2025 #daily-life-enhancement 

---

## My Vision

You can't Google *"park near me with a fenced playground, shade, clean restrooms, and a surface my stroller won't sink into."*

That's the problem ParkScout solves. It's an iOS app that lets parents describe what their family needs in plain language and get back park recommendations they can actually trust — powered by a RAG pipeline built on real parent reviews and verified park data from Fairfax County's 400+ parks.

> *"I have a 3-year-old and a dog. I need a park with restrooms, a fenced playground, and shade — within 15 minutes of Reston."*

ParkScout returns ranked results with a **Parent Score** — a composite rating built from parent-contributed observations on containment (can I see my kid?), restroom quality, stroller accessibility, shade coverage, and sensory environment. The AI factors in real-time weather, so it won't recommend splash pads on a 45-degree day.

## Why This Matters

There are 2.3 million parents in the DC metro area. Every weekend, they search for parks — and Google Maps, Yelp, and county websites don't answer the questions parents actually ask. The friction of finding the *right* park means families default to the same 2-3 familiar spots, missing hundreds of great options.

ParkScout changes the equation:
- **Natural language search** — ask what you need, not what category to filter by
- **Parent-verified data** — real observations from families, not generic listing info
- **Weather-aware** — recommendations adjust to current conditions automatically
- **Crowdsourced quality** — a Scout Badge system gamifies park verification, so the data gets better with every visit

## How I Built This

### Technical Architecture

ParkScout is a **mobile-first** application with a Python backend, SwiftUI iOS frontend, and a **multi-agent RAG pipeline** where three distinct LLM-powered agents collaborate on every query. I used **Kiro** for requirements-first spec generation and **Claude Code** to accelerate implementation.

**Multi-Agent RAG Pipeline (3 Agents):**
1. **Generator Agent** — LangChain + ChromaDB retrieval pipeline that fetches relevant park data and generates recommendations via Claude. Ingests 50+ parks from Fairfax County's ArcGIS API enriched with parent review data
2. **Self-Critic Agent** — Evaluates the generator's response with a confidence threshold (0.7). If the answer doesn't adequately address the query, it triggers re-retrieval with refined parameters and regenerates — catching cases where initial results miss specific needs
3. **Evaluator Agent** — LLM-as-Judge that scores every response on three metrics: **Faithfulness** (does the answer match the retrieved context?), **Answer Relevance** (does it address what was asked?), and **Context Precision** (did retrieval return the right documents?). Automated test suites enforce quality thresholds in CI/CD

**Backend (Python/FastAPI):**
- Full REST API — 15+ endpoints for queries, parks, users, reviews, weather, badges, and auth
- Weather Service — Real-time weather data injected into LLM context so recommendations are seasonally appropriate
- SQLite database with SQLAlchemy for users, reviews, badges, and aggregate ratings

**Gamification — Scout Badges & Rank Progression:**

Parks earn verified badges through crowdsourced parent confirmations. When 3 different parents confirm a specific quality through their reviews, the park earns that badge permanently:
- **Solar Shield** — Excellent shade coverage
- **The Fortress** — Fully fenced playground area
- **Golden Throne** — Exceptionally clean restrooms
- **Tiny Explorer** — Perfect for toddlers ages 1-3
- **Smooth Sailing** — Stroller-friendly paths
- **Splash Zone** — Water play features
- **Paws Welcome** — Dog-friendly with off-leash area
- **Feast Grounds** — Great picnic facilities

Reviewers level up through a tier system based on total reviews completed:
| Tier | Reviews | Icon |
|------|---------|------|
| Tenderfoot | 0-4 | Leaf |
| Trailblazer | 5-14 | Flame |
| Pathfinder | 15-29 | Map |
| Park Legend | 30+ | Star |

The RAG pipeline prioritizes badge-verified parks in recommendations — if a parent asks for shaded playgrounds, Solar Shield parks rank higher because that quality has been confirmed by multiple families.

**iOS App (SwiftUI):**
- Tab-based navigation: Parks, Explore (map), Discover (park picker), Profile, Scout (AI chat)
- Interactive map view with park annotations
- Park detail views with amenity data and Parent Scores
- Badge collection and Scout Rank progression UI
- Demo data fallback — app works offline with 10 real Fairfax County parks
- First-launch onboarding experience

**CI/CD Pipeline (GitHub Actions):**
- Automated Python tests (unit + RAG data quality)
- **RAG evaluation quality gates** — faithfulness, relevance, and context precision thresholds block merges when quality degrades
- Ruff linting for code quality
- iOS build verification on macOS runners
- Bandit security scanning with artifact upload
- Scheduled daily runs for RAG drift detection

```
iOS App (SwiftUI)
    │
    ▼
FastAPI Backend / API Gateway
    │
    ├──► Multi-Agent RAG Pipeline
    │        │
    │        ├── Agent 1: Generator ──► ChromaDB retrieval + Claude
    │        │
    │        ├── Agent 2: Self-Critic ──► Confidence check + retry
    │        │
    │        └── Agent 3: Evaluator ──► LLM-as-Judge
    │                ├── Faithfulness
    │                ├── Answer Relevance
    │                └── Context Precision
    │
    ├──► Weather Service ──► Weather API
    │
    ├──► Auth ──► Local Auth / Cognito
    │
    └──► Reviews & Badges ──► SQLite / DynamoDB
            ├── Scout Badges (park quality verification)
            └── User Tiers (Tenderfoot → Park Legend)
```

### Key Milestones

1. **Data ingestion** — Scraped 400+ parks from Fairfax County ArcGIS, geocoded locations, built vector embeddings for semantic search
2. **RAG pipeline working** — End-to-end natural language queries returning ranked park recommendations with source attribution
3. **Self-Reflective RAG** — Added confidence scoring and automatic re-retrieval when the AI isn't confident in its initial response
4. **RAG evaluation pipeline** — LLM-as-Judge scoring faithfulness, relevance, and context precision with automated CI/CD quality gates
5. **Full API surface** — 15+ endpoints covering queries, parks, users, reviews, weather, badges, and saved parks
6. **iOS app** — SwiftUI views for chat, map, park list, park detail, badges, and auth — with offline demo data fallback
7. **Gamification system** — Scout Badges (Golden Throne, Fortress, Solar Shield, Caffeine Compass, Smooth Roller) with rank progression from Tenderfoot to Park Legend
8. **CI/CD pipeline** — GitHub Actions running tests, RAG quality evaluation, linting, iOS builds, and security scans on every push

## Demo

<!-- Replace VIDEO_URL below with the actual video link (YouTube, Vimeo, or direct MP4 URL) -->

**Watch the full demo walkthrough:**

[![ParkScout Demo Video](https://img.shields.io/badge/▶_Watch_Demo-ParkScout-green?style=for-the-badge&logo=youtube)](VIDEO_URL)

<!-- If embedding directly (e.g., on a platform that supports HTML video): -->
<!-- <video src="VIDEO_URL" controls width="100%"></video> -->

The demo walks through the complete ParkScout experience:

1. **Splash Screen & Onboarding** — The app launches with an animated ParkScout splash, followed by onboarding slides introducing the Parent Score system, Scout Badges, and AI-powered discovery
2. **Parks List** — Browse 300+ Fairfax County parks sorted by distance, with earned badge chips visible directly on each card
3. **Interactive Map** — Explore parks on the map with color-coded pins by distance, filter by Playground/Dog-Friendly/Trails, and search by park name
4. **Park Detail — Clemyjontri** — Tap into Clemyjontri to see 5 parent reviews, a 4.73/5 Parent Score, and 5 earned Scout Badges (The Fortress, Solar Shield, Golden Throne, Tiny Explorer, Smooth Sailing)
5. **Discover (Park Picker)** — Spin the wheel for a random park suggestion when you can't decide
6. **Scout AI Chat** — Ask natural language questions like *"Shaded playground near Reston for a toddler, needs restrooms"* and get ranked recommendations with Parent Scores, then follow up with *"What about one that's dog-friendly?"* to see conversational memory in action
7. **Profile & Saved Parks** — View saved parks, review history, and Scout Rank progression

## What I Learned

**RAG quality is all about the data, not the model.** I spent more time cleaning and enriching park data (adding parent-relevant attributes like shade coverage and stroller accessibility) than tuning the LLM. The self-reflective retry loop helps, but garbage in still equals garbage out — the vector store needs to contain the specific information parents care about.

**You can't improve what you don't measure.** Adding LLM-as-Judge evaluation transformed how I iterated on the RAG pipeline. Before measurement, I was guessing whether prompt changes helped. After adding faithfulness, relevance, and context precision metrics, I could see exactly which queries degraded when I changed retrieval parameters. The CI/CD quality gates caught two regressions that would have shipped silently.

**Kiro changed how I plan.** Using Kiro's requirements-first approach generated 27 requirements and 199 implementation tasks before I wrote a line of code. This was initially overwhelming — the full spec covers months of work. But it forced me to identify what actually matters for an MVP vs. what's aspirational. The spec became a living roadmap I could scope against rather than a to-do list I had to complete.

**Claude Code made the boring parts fast.** The CI/CD pipeline, data models, RAG evaluation harness, and API boilerplate were generated and iterated on rapidly. This freed me to focus on the interesting problems: how to structure park data for semantic search, what a "Parent Score" actually means mathematically, and how to make weather context useful rather than gimmicky.

---

<!-- GitHub: [Add your repo link here] -->

#aideas-2025 #daily-life-enhancement #NAMER

*Any opinions in this article are those of the individual author and may not reflect the opinions of AWS.*
