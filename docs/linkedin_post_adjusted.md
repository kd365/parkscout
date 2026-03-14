# Accuracy-Adjusted LinkedIn/Competition Post

## Honesty Audit of Original Draft

| Claim | Verdict | Notes |
|-------|---------|-------|
| "Multi-agent RAG pipeline" with 3 agents | **PARTIALLY TRUE** | Generator and Evaluator exist in code. Self-Critic (confidence threshold + re-retrieval) is **NOT implemented** — no code for it anywhere in `server.py`. |
| "Self-Critic: Confidence-checks the answer (0.7 threshold)" | **FALSE** | No confidence scoring or re-retrieval logic exists in the codebase. |
| "Evaluator: LLM-as-Judge scoring Faithfulness, Relevance, Precision" | **TRUE** | Fully implemented in `api/services/rag_evaluator.py` with real Claude-based scoring. |
| "Generator: Claude + LangChain + ChromaDB" | **TRUE** | Working RAG pipeline in `api/server.py`. |
| "CI/CD Quality Gates block merges if quality degrades" | **STRETCH** | RAG eval runs in CI as a check on PRs, but there's no branch protection rule enforcing it — it can be bypassed. "Quality checks" is more accurate than "quality gates that block merges." |
| "400+ park records" | **TRUE** | 321 parks from ArcGIS, 400+ scraped total in source data. |
| "Scout Badges (e.g., The Golden Throne)" | **TRUE** | 8 badge types, fully implemented with confirmation thresholds. |
| "Weather-aware recommendations" | **TRUE** | Weather service injects real-time context into LLM prompts. |
| "Gamified frontend" | **TRUE** | Badges, tiers (Tenderfoot→Park Legend), badge chips on cards. |
| "Parent Score algorithm" | **TRUE** | Weighted composite in seed script and API. |
| "RAG pipeline prioritizes badge-verified parks" | **TRUE** | Badge data is injected into LLM prompt with "prioritize these" instruction. Not algorithmic re-ranking, but prompt-based prioritization. |
| "CI/CD quality gates caught two regressions" (in article) | **UNVERIFIABLE** | No git history to confirm this happened. Could be true from dev process but can't prove it. |
| Milestone 3: "Self-Reflective RAG" | **FALSE** | Same as Self-Critic — not implemented. |
| Milestone 7 badge names: "Caffeine Compass, Smooth Roller" | **WRONG NAMES** | Actual badges are: Smooth Sailing, not Smooth Roller. Caffeine Compass doesn't exist. |

---

## Corrected Post

---

From "Standard Search" to "Parent-Verified RAG": How I Built ParkScout for #AIdeas

Attention builders!

Ever tried to find a playground that is actually shaded, fenced, and stroller-friendly using just Google Maps? It's a nightmare. As a parent, "nearby" isn't enough — you need "verified."

I built ParkScout to solve this. It's an iOS app powered by a RAG pipeline with automated quality evaluation that turns 400+ park records and crowdsourced parent reviews into trusted, weather-aware recommendations.

**The Tech Stack (What's under the hood)**

**RAG Pipeline with LLM-as-Judge Evaluation:** Two LLM-powered components work together:

- **Generator:** Claude + LangChain + ChromaDB retrieves relevant park data (enriched with parent reviews, badge data, and weather context) and generates natural language recommendations.

- **Evaluator (LLM-as-Judge):** A separate Claude instance scores every response on three metrics — Faithfulness (is the answer grounded in retrieved context?), Answer Relevance (does it address what was asked?), and Context Precision (did retrieval return the right documents?). This runs in CI/CD to catch quality regressions before they ship.

**iOS/SwiftUI:** A clean, gamified frontend with "Scout Badges" — parks earn verified badges like The Golden Throne (clean restrooms) and The Fortress (fully fenced) when 3+ parents confirm the quality through reviews. Users level up from Tenderfoot to Park Legend.

**Weather-Aware Context:** Real-time weather data is injected into every query so the AI won't recommend splash pads on a 45-degree day or open fields during a thunderstorm.

**CI/CD Pipeline:** GitHub Actions running unit tests, RAG evaluation checks, Ruff linting, iOS build verification, and Bandit security scanning — with scheduled daily runs for drift detection.

**The "Aha!" Moment**

I learned that RAG quality is about the data, not the model. I spent more time cleaning ArcGIS data and building a "Parent Score" algorithm (weighted composite of shade, containment, restrooms, playground quality, safety, and trails) than tuning prompts. If the vector store doesn't know about the "fenced-in" status, the smartest LLM in the world can't help you.

**I need your Scout Badge!**

I'm competing in the AWS #AIdeas 2025 challenge, and winners are determined by community engagement.

If you've ever fought a stroller through a mulch pit or searched for a bathroom in a panic, please:

- Check out the full build article and demo video
- Drop a Like on the project!
- Leave a comment — I'd love to talk RAG evaluation, SwiftUI map integration, or gamification design

Demo Video: https://www.youtube.com/watch?v=wCID797d7HI
GitHub: https://github.com/kd365/parkscout

#AWS #GenerativeAI #RAG #LangChain #SwiftUI #ParentingTech #BuildInPublic #AIdeas2025 #NAMER

---

## Key Changes from Original

1. **Removed Self-Critic claim entirely** — it's not in the code, so don't claim it
2. **Changed "3-agent team" to "RAG pipeline with LLM-as-Judge evaluation"** — still impressive, and it's real
3. **Changed "CI/CD quality gates block merges" to "CI/CD quality checks"** — the eval runs but doesn't enforce branch protection
4. **Added specifics to Parent Score** — shows you actually built the algorithm, not just named it
5. **Removed "Pro Tips" section** — that's strategy notes for you, not part of the public post
6. **Fixed badge names** — removed Caffeine Compass and Smooth Roller references
7. **Kept the engagement hook and CTA** — those are genuine and effective
