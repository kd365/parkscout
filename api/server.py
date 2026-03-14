"""
FastAPI Server for Parks Finder

Endpoints:
- POST /query - Ask the AI about parks (RAG with memory)
- GET  /parks - List all parks with filters
- GET  /parks/{name} - Get park details
- POST /users - Create user
- GET  /users/{id} - Get user profile
- PUT  /users/{id} - Update user
- POST /users/{id}/saved-parks - Save a park
- GET  /users/{id}/saved-parks - Get saved parks
- GET  /users/{id}/conversations - Get conversation history
"""
import os
import json
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# LangChain imports
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Local imports
from .models import (
    init_db, get_session, User, SavedPark, Conversation, Message, SearchHistory,
    ParkReview, ParkAggregateRating, ParkBadge, BadgeConfirmation,
    BADGE_DEFINITIONS, BADGE_RATING_MAP, DISPUTE_NEGATIVE_THRESHOLD, DISPUTE_WINDOW_DAYS,
    USER_TIERS, get_user_tier
)
from .schemas import (
    QueryRequest, QueryResponse, ParkMention,
    UserCreate, UserResponse, UserUpdate,
    RegisterRequest, LoginRequest, AuthResponse,
    SaveParkRequest, SavedParkResponse,
    ParkSchema, ParkListResponse, ParkFilters, ParkAmenities,
    ConversationSummary, ConversationDetail, MessageSchema,
    ReviewCreate, ReviewResponse, ReviewListResponse, ParkTagsResponse,
    MarkReviewHelpfulRequest, PARK_TAGS, WeatherResponse,
    UserTier, BadgeDefinition, ParkBadgeSchema, BadgeConfirmRequest,
    BadgeConfirmResponse, ParkBadgesResponse, UserProfileWithTier
)
from .services.weather_service import get_weather_service

# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "chroma_parks")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "source_data", "fairfax_parks.json")
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "claude-haiku-4-5-20251001"  # Fast and cheap Claude model
MAX_HISTORY = 6

# Get API key from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are a friendly ParkScout guide helping families find the perfect parks in Fairfax County.
Always recommend at least 2 parks and compare their amenities.
For each park, mention the name, key amenities, and what makes it a good fit.
If one park is clearly better for the request, explain why but still offer an alternative.
When answering follow-up questions, reference the parks you previously mentioned.

PARKSCOUT VERIFIED BADGES - PRIORITIZE THESE IN RECOMMENDATIONS:
When parks have earned verified badges from the ParkScout community, highlight them prominently.
Badge data represents real parent confirmations and should be trusted over general data.
Include phrases like "ParkScout users have verified this park as a [Badge Name]" when applicable.

Key badges to highlight:
- "Solar Shield" = Excellent shade coverage (verified by parents)
- "The Fortress" = Fully fenced playground area
- "Golden Throne" = Exceptionally clean restrooms
- "Tiny Explorer" = Perfect for toddlers (ages 1-3)
- "Smooth Sailing" = Stroller-friendly paths
- "Splash Zone" = Water play features
- "Paws Welcome" = Dog-friendly with good off-leash area

If badge data is provided in the context, prioritize parks with relevant earned badges.
For example, if asked about shady parks, prioritize "Solar Shield" verified parks.

WEATHER AWARENESS:
- On hot days (85°F+), prioritize parks with splash pads, shade ("Solar Shield" badges), and water features
- On rainy days, suggest parks with pavilions or covered areas
- When UV is high, emphasize shaded playgrounds and "Solar Shield" verified parks
- In cold weather, suggest shorter visits and parks with nearby restrooms ("Golden Throne" badges)

Factor weather into your recommendations naturally without being repetitive about it."""


# ============================================================
# GLOBAL STATE
# ============================================================

# In-memory conversation store (replace with Redis for production)
conversation_memory: Dict[str, List[Dict[str, str]]] = {}

# Database engine
db_engine = None

# RAG components (initialized on startup)
retriever = None
chroma_store = None  # Keep reference for expanded retrieval in Self-Critic
llm = None

# Self-Critic configuration
CONFIDENCE_THRESHOLD = 0.7
MAX_RETRIEVAL_ATTEMPTS = 2
EXPANDED_K = 8  # Double the retrieval count on retry


# ============================================================
# LIFESPAN & DEPENDENCIES
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global db_engine, retriever, chroma_store, llm

    print("Initializing Parks Finder API...")

    # Initialize database
    db_path = os.path.join(os.path.dirname(__file__), "..", "parks_finder.db")
    db_engine = init_db(f"sqlite:///{db_path}")
    print(f"  Database: {db_path}")

    # Initialize RAG components
    print(f"  Loading ChromaDB from: {DB_PATH}")
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    chroma_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    chroma_store = chroma_db
    retriever = chroma_db.as_retriever(search_kwargs={"k": 4})

    print(f"  Loading LLM: {LLM_MODEL}")
    if not ANTHROPIC_API_KEY:
        print("  WARNING: ANTHROPIC_API_KEY not set!")
    llm = ChatAnthropic(
        model=LLM_MODEL,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.7,
        max_tokens=1024
    )

    print("API ready!")
    yield

    # Cleanup
    print("Shutting down...")


def get_db():
    """Dependency for database sessions."""
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()


# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(
    title="Parks Finder API",
    description="AI-powered Fairfax County parks discovery",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RAG QUERY ENDPOINTS
# ============================================================

def self_critic_evaluate(question: str, answer: str, context: str) -> float:
    """
    Self-Critic Agent: Evaluates the generator's response confidence.

    Returns a confidence score (0.0 to 1.0). If below CONFIDENCE_THRESHOLD,
    the pipeline triggers re-retrieval with expanded context.
    """
    critic_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a quality critic for a park recommendation system. "
            "Evaluate whether the answer adequately addresses the user's question "
            "using the provided context. Consider: Does it recommend specific parks? "
            "Does it address the specific needs mentioned (age, amenities, location)? "
            "Is the information grounded in the context provided? "
            "Respond with ONLY a single decimal number between 0.0 and 1.0."
        )),
        ("user", (
            "Question: {question}\n\n"
            "Context provided:\n{context}\n\n"
            "Generated answer: {answer}\n\n"
            "Confidence score (0.0 to 1.0):"
        )),
    ])
    chain = critic_prompt | llm | StrOutputParser()
    result = chain.invoke({"question": question, "context": context, "answer": answer})

    # Parse the score
    for token in result.strip().replace("\n", " ").split():
        token = token.strip(".,;:()")
        try:
            score = float(token)
            if 0.0 <= score <= 1.0:
                return score
        except ValueError:
            continue
    return 0.5  # Default if parsing fails


@app.post("/query", response_model=QueryResponse, tags=["AI"])
async def query_parks(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Ask the AI about Fairfax County parks.

    Uses a multi-agent pipeline:
    1. Generator Agent — retrieves context and generates recommendations
    2. Self-Critic Agent — confidence-checks the answer, triggers re-retrieval if < 0.7
    3. Evaluator Agent — LLM-as-Judge scoring (runs in CI/CD via test suite)

    Supports conversation memory - include session_id for follow-ups.
    Weather context is automatically included to provide relevant recommendations.
    """
    start_time = time.time()

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []

    history = conversation_memory[session_id]

    # Build history string
    history_str = "No previous conversation."
    if history:
        history_str = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history[-MAX_HISTORY:]
        ])

    # Get weather context (use user location if provided, otherwise default)
    weather_context = ""
    try:
        weather_service = get_weather_service()
        lat = request.location.get("lat", 38.8462) if request.location else 38.8462
        lon = request.location.get("lng", -77.3064) if request.location else -77.3064
        weather = await weather_service.get_current_weather(lat=lat, lon=lon)
        weather_context = weather_service.get_weather_context_for_rag(weather)
    except Exception as e:
        # Weather is optional - continue without it
        print(f"Weather fetch failed (non-blocking): {e}")
        weather_context = "Weather data unavailable."

    # ── Agent 1: Generator ──────────────────────────────────────
    # Retrieve relevant context and generate initial response
    docs = retriever.invoke(request.question)
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)
    badge_context = get_badge_context_for_rag(db, context)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", f"""Previous conversation:
{history_str}

{weather_context}

{badge_context}

Relevant parks data:
{context}

Current question: {request.question}""")
    ])

    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({})

    # ── Agent 2: Self-Critic ────────────────────────────────────
    # Evaluate confidence and re-retrieve with expanded context if needed
    retrieval_attempts = 1
    confidence = 0.5  # Default

    try:
        confidence = self_critic_evaluate(request.question, answer, context)
        print(f"[Self-Critic] Confidence: {confidence:.2f} (threshold: {CONFIDENCE_THRESHOLD})")

        if confidence < CONFIDENCE_THRESHOLD and chroma_store is not None:
            print(f"[Self-Critic] Below threshold — re-retrieving with k={EXPANDED_K}")
            retrieval_attempts = 2

            # Expanded retrieval with more documents
            expanded_retriever = chroma_store.as_retriever(search_kwargs={"k": EXPANDED_K})
            docs = expanded_retriever.invoke(request.question)
            context = "\n\n---\n\n".join(doc.page_content for doc in docs)
            badge_context = get_badge_context_for_rag(db, context)

            # Regenerate with richer context
            retry_prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("user", f"""Previous conversation:
{history_str}

{weather_context}

{badge_context}

Relevant parks data (expanded search):
{context}

Current question: {request.question}

IMPORTANT: The previous answer was not confident enough. Please provide a more thorough response
with specific park recommendations that directly address the user's needs.""")
            ])

            chain = retry_prompt | llm | StrOutputParser()
            answer = chain.invoke({})

            # Re-evaluate confidence
            confidence = self_critic_evaluate(request.question, answer, context)
            print(f"[Self-Critic] Retry confidence: {confidence:.2f}")

    except Exception as e:
        print(f"[Self-Critic] Evaluation failed (non-blocking): {e}")
        # Continue with original answer if critic fails

    response_time = time.time() - start_time

    # Update memory
    history.append({"role": "user", "content": request.question})
    history.append({"role": "assistant", "content": answer})
    conversation_memory[session_id] = history[-MAX_HISTORY:]

    # Extract park mentions (simple heuristic)
    parks_mentioned = extract_park_mentions(answer)

    # Log to database if user is authenticated
    if request.user_id:
        log_conversation(db, request.user_id, session_id, request.question, answer, response_time, parks_mentioned)

    return QueryResponse(
        answer=answer,
        session_id=session_id,
        parks_mentioned=parks_mentioned,
        response_time_seconds=round(response_time, 2),
        conversation_turn=len(history) // 2,
        confidence=round(confidence, 2),
        retrieval_attempts=retrieval_attempts
    )


def get_badge_context_for_rag(db: Session, parks_context: str) -> str:
    """
    Get badge information for parks mentioned in context.
    Returns formatted string for inclusion in RAG prompt.
    """
    try:
        # Get all earned badges
        earned_badges = db.query(ParkBadge).filter(ParkBadge.is_earned == True).all()

        if not earned_badges:
            return "PARKSCOUT VERIFIED BADGES: No badges earned yet."

        # Group badges by park
        parks_with_badges = {}
        for badge in earned_badges:
            if badge.badge_id not in BADGE_DEFINITIONS:
                continue
            if badge.park_name not in parks_with_badges:
                parks_with_badges[badge.park_name] = []
            badge_def = BADGE_DEFINITIONS[badge.badge_id]
            parks_with_badges[badge.park_name].append(
                f"{badge_def['name']} ({badge.confirmation_count} confirmations)"
            )

        if not parks_with_badges:
            return "PARKSCOUT VERIFIED BADGES: No badges earned yet."

        # Format for context
        badge_lines = ["PARKSCOUT VERIFIED BADGES (prioritize these in recommendations):"]
        for park_name, badges in parks_with_badges.items():
            badge_lines.append(f"- {park_name}: {', '.join(badges)}")

        return "\n".join(badge_lines)

    except Exception as e:
        print(f"Badge context fetch failed: {e}")
        return "PARKSCOUT VERIFIED BADGES: Badge data unavailable."


def extract_park_mentions(text: str) -> List[ParkMention]:
    """Extract park names mentioned in response.

    Also matches features/facilities mentioned in park descriptions
    (e.g., "Hidden Oaks Nature Center" -> returns "Annandale" park).
    """
    try:
        with open(DATA_PATH, 'r') as f:
            parks = json.load(f)
    except:
        return []

    text_lower = text.lower()
    mentions = []
    seen_parks = set()

    # First pass: exact park name matches
    for park in parks:
        name = park["park_name"]
        if name.lower() in text_lower and name not in seen_parks:
            mentions.append(ParkMention(name=name))
            seen_parks.add(name)

    # Second pass: match features in descriptions
    # e.g., "Hidden Oaks Nature Center" is in Annandale's description
    for park in parks:
        name = park["park_name"]
        if name in seen_parks:
            continue

        description = park.get("description", "")
        # Extract notable features from description (after "Features:")
        if "Features:" in description:
            features_text = description.split("Features:")[-1]
            # Split by comma and check each feature
            features = [f.strip() for f in features_text.split(",")]
            for feature in features:
                # Clean up feature name (remove trailing periods, etc.)
                feature_clean = feature.strip().rstrip(".")
                if len(feature_clean) > 5 and feature_clean.lower() in text_lower:
                    mentions.append(ParkMention(name=name))
                    seen_parks.add(name)
                    break

    return mentions


def log_conversation(db: Session, user_id: int, session_id: str,
                    question: str, answer: str, response_time: float,
                    parks_mentioned: List[ParkMention]):
    """Log conversation to database."""
    # Find or create conversation
    conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
    if not conv:
        conv = Conversation(
            user_id=user_id,
            session_id=session_id,
            title=question[:50] + "..." if len(question) > 50 else question
        )
        db.add(conv)
        db.flush()

    # Add messages
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=question
    )
    ai_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        response_time_seconds=response_time,
        parks_mentioned=[p.name for p in parks_mentioned]
    )
    db.add_all([user_msg, ai_msg])
    db.commit()


@app.delete("/query/{session_id}", tags=["AI"])
async def clear_conversation(session_id: str):
    """Clear conversation memory for a session."""
    if session_id in conversation_memory:
        del conversation_memory[session_id]
    return {"message": "Conversation cleared"}


# ============================================================
# PARKS ENDPOINTS
# ============================================================

@app.get("/parks", response_model=ParkListResponse, tags=["Parks"])
async def list_parks(
    playground: Optional[bool] = None,
    dog_friendly: Optional[bool] = None,
    restrooms: Optional[bool] = None,
    trails: Optional[bool] = None,
    carousel: Optional[bool] = None,
    classification: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all parks with optional filters.
    Includes aggregate mom_score and total_reviews from community ratings.
    """
    with open(DATA_PATH, 'r') as f:
        parks = json.load(f)

    # Apply filters
    filtered = parks
    filters_applied = {}

    if playground is not None:
        filtered = [p for p in filtered
                   if (p["amenities"]["playground"] != "No") == playground]
        filters_applied["playground"] = playground

    if dog_friendly is not None:
        filtered = [p for p in filtered
                   if ("Yes" in p["amenities"]["dog_friendly"]) == dog_friendly]
        filters_applied["dog_friendly"] = dog_friendly

    if restrooms is not None:
        filtered = [p for p in filtered
                   if (p["amenities"]["restrooms"] != "No") == restrooms]
        filters_applied["restrooms"] = restrooms

    if trails is not None:
        filtered = [p for p in filtered
                   if (p["amenities"]["trails"] != "None") == trails]
        filters_applied["trails"] = trails

    if carousel is not None:
        filtered = [p for p in filtered
                   if ("Carousel" in p["amenities"].get("special_features", [])) == carousel]
        filters_applied["carousel"] = carousel

    if classification:
        filtered = [p for p in filtered
                   if p.get("classification", "").lower() == classification.lower()]
        filters_applied["classification"] = classification

    total = len(filtered)
    paginated = filtered[offset:offset + limit]

    # Get aggregate ratings from database for these parks
    park_names = [p["park_name"] for p in paginated]
    aggregates = {}
    try:
        agg_results = db.query(ParkAggregateRating).filter(
            ParkAggregateRating.park_name.in_(park_names)
        ).all()
        aggregates = {agg.park_name: agg for agg in agg_results}
    except Exception:
        pass  # Continue without ratings if DB query fails

    # Convert parks to ParkSchema with ratings
    park_schemas = []
    for p in paginated:
        park_data = p.copy()
        park_data["amenities"] = ParkAmenities(**p["amenities"])

        # Add mom_score and total_reviews from aggregates
        agg = aggregates.get(p["park_name"])
        if agg:
            park_data["mom_score"] = agg.mom_score
            park_data["total_reviews"] = agg.total_reviews
        else:
            park_data["mom_score"] = None
            park_data["total_reviews"] = 0

        park_schemas.append(ParkSchema(**park_data))

    return ParkListResponse(
        parks=park_schemas,
        total_count=total,
        filters_applied=filters_applied
    )


@app.get("/parks/{park_name}", response_model=ParkSchema, tags=["Parks"])
async def get_park(park_name: str):
    """Get details for a specific park."""
    with open(DATA_PATH, 'r') as f:
        parks = json.load(f)

    # Handle partial names like "Clemyjontri" matching "Clemyjontri Park"
    for park in parks:
        if park["park_name"].lower() == park_name.lower() or \
           park_name.lower() in park["park_name"].lower():
            park_data = park.copy()
            park_data["amenities"] = ParkAmenities(**park["amenities"])
            return ParkSchema(**park_data)

    raise HTTPException(status_code=404, detail="Park not found")


# ============================================================
# USER ENDPOINTS
# ============================================================

@app.post("/users", response_model=UserResponse, tags=["Users"])
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    db_user = User(
        apple_id=user.apple_id,
        email=user.email,
        display_name=user.display_name,
        preferences=user.preferences.model_dump() if user.preferences else {}
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def update_user(user_id: int, update: UserUpdate, db: Session = Depends(get_db)):
    """Update user profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update.display_name:
        user.display_name = update.display_name
    if update.preferences:
        user.preferences = update.preferences.model_dump()

    db.commit()
    db.refresh(user)
    return user


# ============================================================
# AUTH ENDPOINTS
# ============================================================

# Simple token storage (in production, use Redis or database)
active_sessions: Dict[str, int] = {}  # token -> user_id


def hash_password(password: str) -> str:
    """Hash password with salt using SHA-256."""
    salt = "parksfinder_salt_2024"  # In production, use unique salt per user
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == password_hash


def generate_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


@app.post("/auth/register", response_model=AuthResponse, tags=["Auth"])
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user with hashed password
    db_user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name or request.email.split("@")[0],
        preferences={}
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate session token
    token = generate_token()
    active_sessions[token] = db_user.id

    return AuthResponse(
        user_id=db_user.id,
        email=db_user.email,
        display_name=db_user.display_name,
        token=token,
        message="Registration successful"
    )


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last active
    user.last_active = datetime.utcnow()
    db.commit()

    # Generate session token
    token = generate_token()
    active_sessions[token] = user.id

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        token=token,
        message="Login successful"
    )


@app.post("/auth/logout", tags=["Auth"])
async def logout(token: str):
    """Logout and invalidate session token."""
    if token in active_sessions:
        del active_sessions[token]
        return {"message": "Logged out successfully"}
    return {"message": "Already logged out"}


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_current_user(token: str, db: Session = Depends(get_db)):
    """Get current user from session token."""
    user_id = active_sessions.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ============================================================
# PARKSCOUT BADGE ENDPOINTS
# ============================================================

@app.get("/badges", response_model=List[BadgeDefinition], tags=["Badges"])
async def list_badges():
    """List all available badge definitions."""
    return [
        BadgeDefinition(id=badge_id, **{k: v for k, v in badge.items() if k != "criteria"})
        for badge_id, badge in BADGE_DEFINITIONS.items()
    ]


@app.get("/badges/{badge_id}", response_model=BadgeDefinition, tags=["Badges"])
async def get_badge(badge_id: str):
    """Get a specific badge definition."""
    if badge_id not in BADGE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Badge not found")
    badge = BADGE_DEFINITIONS[badge_id]
    return BadgeDefinition(id=badge_id, **{k: v for k, v in badge.items() if k != "criteria"})


@app.get("/parks/{park_name}/badges", response_model=ParkBadgesResponse, tags=["Badges"])
async def get_park_badges(park_name: str, db: Session = Depends(get_db)):
    """Get all badges (earned and pending) for a park."""
    badges = db.query(ParkBadge).filter(ParkBadge.park_name == park_name).all()

    earned = []
    pending = []
    disputed = []

    for badge in badges:
        if badge.badge_id not in BADGE_DEFINITIONS:
            continue
        badge_def = BADGE_DEFINITIONS[badge.badge_id]
        status = getattr(badge, 'status', 'earned') or 'earned'
        schema = ParkBadgeSchema(
            badge_id=badge.badge_id,
            name=badge_def["name"],
            description=badge_def["description"],
            icon=badge_def["icon"],
            category=badge_def["category"],
            confirmation_count=badge.confirmation_count,
            is_earned=badge.is_earned,
            earned_at=badge.earned_at if badge.is_earned else None,
            status=status,
            negative_count=badge.negative_count or 0
        )
        if status == "disputed":
            disputed.append(schema)
        elif status == "lost":
            # Lost badges go to disputed list with their status for visibility
            disputed.append(schema)
        elif badge.is_earned:
            earned.append(schema)
        elif badge.confirmation_count > 0:
            pending.append(schema)

    return ParkBadgesResponse(
        park_name=park_name,
        earned_badges=earned,
        pending_badges=pending,
        disputed_badges=disputed
    )


@app.post("/badges/confirm", response_model=BadgeConfirmResponse, tags=["Badges"])
async def confirm_badge(request: BadgeConfirmRequest, user_id: int, db: Session = Depends(get_db)):
    """
    Confirm a badge for a park (user verification).
    Once threshold confirmations are reached, badge is earned.
    """
    # Validate badge exists
    if request.badge_id not in BADGE_DEFINITIONS:
        raise HTTPException(status_code=400, detail="Invalid badge ID")

    badge_def = BADGE_DEFINITIONS[request.badge_id]
    threshold = badge_def["threshold"]

    # Check user hasn't already confirmed this badge for this park
    existing_confirmation = db.query(BadgeConfirmation).filter(
        BadgeConfirmation.user_id == user_id,
        BadgeConfirmation.park_name == request.park_name,
        BadgeConfirmation.badge_id == request.badge_id
    ).first()

    if existing_confirmation:
        raise HTTPException(status_code=400, detail="You have already confirmed this badge for this park")

    # Create confirmation
    confirmation = BadgeConfirmation(
        user_id=user_id,
        park_name=request.park_name,
        badge_id=request.badge_id,
        review_id=request.review_id
    )
    db.add(confirmation)

    # Get or create park badge record
    park_badge = db.query(ParkBadge).filter(
        ParkBadge.park_name == request.park_name,
        ParkBadge.badge_id == request.badge_id
    ).first()

    if not park_badge:
        park_badge = ParkBadge(
            park_name=request.park_name,
            badge_id=request.badge_id,
            confirmation_count=0,
            is_earned=False
        )
        db.add(park_badge)

    # Increment count
    park_badge.confirmation_count += 1
    new_count = park_badge.confirmation_count

    # Check if badge is now earned
    badge_earned = False
    if not park_badge.is_earned and new_count >= threshold:
        park_badge.is_earned = True
        park_badge.earned_at = datetime.utcnow()
        badge_earned = True

    db.commit()

    message = f"Badge confirmed! {new_count}/{threshold} confirmations."
    if badge_earned:
        message = f"Congratulations! {request.park_name} has earned the '{badge_def['name']}' badge!"

    return BadgeConfirmResponse(
        badge_id=request.badge_id,
        park_name=request.park_name,
        new_count=new_count,
        threshold=threshold,
        badge_earned=badge_earned,
        message=message
    )


@app.get("/users/{user_id}/profile", response_model=UserProfileWithTier, tags=["Users"])
async def get_user_profile_with_tier(user_id: int, db: Session = Depends(get_db)):
    """Get user profile with tier information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    review_count = db.query(ParkReview).filter(ParkReview.user_id == user_id).count()
    confirmation_count = db.query(BadgeConfirmation).filter(BadgeConfirmation.user_id == user_id).count()
    tier_data = get_user_tier(review_count)

    return UserProfileWithTier(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        created_at=user.created_at,
        review_count=review_count,
        tier=UserTier(**tier_data),
        badge_confirmations_count=confirmation_count
    )


@app.get("/tiers", tags=["Badges"])
async def list_tiers():
    """List all user tier definitions."""
    return [{"id": k, **v} for k, v in USER_TIERS.items()]


# ============================================================
# SAVED PARKS ENDPOINTS
# ============================================================

@app.post("/users/{user_id}/saved-parks", response_model=SavedParkResponse, tags=["Saved Parks"])
async def save_park(user_id: int, request: SaveParkRequest, db: Session = Depends(get_db)):
    """Save a park to user's favorites."""
    # Check if already saved
    existing = db.query(SavedPark).filter(
        SavedPark.user_id == user_id,
        SavedPark.park_name == request.park_name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Park already saved")

    saved = SavedPark(
        user_id=user_id,
        park_name=request.park_name,
        notes=request.notes,
        tags=request.tags
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@app.get("/users/{user_id}/saved-parks", response_model=List[SavedParkResponse], tags=["Saved Parks"])
async def get_saved_parks(user_id: int, db: Session = Depends(get_db)):
    """Get user's saved parks."""
    saved = db.query(SavedPark).filter(SavedPark.user_id == user_id).all()
    return saved


@app.delete("/users/{user_id}/saved-parks/{park_name}", tags=["Saved Parks"])
async def unsave_park(user_id: int, park_name: str, db: Session = Depends(get_db)):
    """Remove a park from favorites."""
    saved = db.query(SavedPark).filter(
        SavedPark.user_id == user_id,
        SavedPark.park_name == park_name
    ).first()

    if not saved:
        raise HTTPException(status_code=404, detail="Saved park not found")

    db.delete(saved)
    db.commit()
    return {"message": "Park removed from favorites"}


# ============================================================
# CONVERSATION HISTORY ENDPOINTS
# ============================================================

@app.get("/users/{user_id}/conversations", response_model=List[ConversationSummary], tags=["Conversations"])
async def get_conversations(user_id: int, db: Session = Depends(get_db)):
    """Get user's conversation history."""
    convs = db.query(Conversation).filter(Conversation.user_id == user_id).all()
    return [
        ConversationSummary(
            session_id=c.session_id,
            title=c.title,
            started_at=c.started_at,
            message_count=len(c.messages),
            is_active=c.is_active
        )
        for c in convs
    ]


@app.get("/conversations/{session_id}", response_model=ConversationDetail, tags=["Conversations"])
async def get_conversation_detail(session_id: str, db: Session = Depends(get_db)):
    """Get full conversation with messages."""
    conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetail(
        session_id=conv.session_id,
        title=conv.title,
        started_at=conv.started_at,
        messages=[
            MessageSchema(
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                parks_mentioned=m.parks_mentioned or []
            )
            for m in conv.messages
        ]
    )


# ============================================================
# REVIEWS ENDPOINTS
# ============================================================

@app.get("/reviews/tags", response_model=ParkTagsResponse, tags=["Reviews"])
async def get_available_tags():
    """Get all available tags for reviews, organized by category."""
    categories = {
        "age": [t for t in PARK_TAGS if "good-for-toddlers" in t or "good-for-preschool" in t or "good-for-elementary" in t or "good-for-tweens" in t],
        "containment": [t for t in PARK_TAGS if t in ["fully-fenced", "partially-fenced", "open-near-road", "excellent-sightlines", "has-blind-spots", "single-bench-view-all"]],
        "accessibility": [t for t in PARK_TAGS if t in ["stroller-friendly", "wheelchair-accessible", "easy-parking", "hard-to-find-parking", "paved-path-to-playground", "wide-parking-for-minivan", "close-parking-quick-exit"]],
        "surface": [t for t in PARK_TAGS if "surface" in t],
        "shade": [t for t in PARK_TAGS if "shade" in t or "umbrella" in t],
        "restrooms": [t for t in PARK_TAGS if "restroom" in t or "changing-table" in t or "potty" in t or "family-restroom" in t],
        "playground": [t for t in PARK_TAGS if "playground" in t or "equipment" in t],
        "feeding": [t for t in PARK_TAGS if "nursing" in t or "snack" in t or "water-fountain" in t or "bring-your-own" in t],
        "environment": [t for t in PARK_TAGS if t in ["usually-quiet", "can-get-crowded", "under-flight-path", "near-highway-noise", "peaceful-nature-sounds", "sensory-friendly"]],
        "practical": [t for t in PARK_TAGS if t in ["bring-bug-spray", "muddy-when-wet", "good-for-picnics"]],
        "atmosphere": [t for t in PARK_TAGS if t in ["good-for-birthday-parties", "great-for-photos", "nature-immersive"]],
        "timing": [t for t in PARK_TAGS if t in ["best-in-morning", "best-late-afternoon", "avoid-weekends", "great-fall-colors"]],
        "nearby": [t for t in PARK_TAGS if "nearby" in t],
    }
    return ParkTagsResponse(tags=PARK_TAGS, categories=categories)


@app.post("/parks/{park_name}/reviews", response_model=ReviewResponse, tags=["Reviews"])
async def create_review(
    park_name: str,
    review: ReviewCreate,
    user_id: int = Query(..., description="User ID submitting the review"),
    db: Session = Depends(get_db)
):
    """Submit a mom-centric review for a park."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate tags are from allowed list
    invalid_tags = [t for t in review.tags if t not in PARK_TAGS]
    if invalid_tags:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tags: {invalid_tags}. Use GET /reviews/tags for valid options."
        )

    # Convert mom_observations to dict if provided
    mom_obs_dict = None
    if review.mom_observations:
        mom_obs_dict = review.mom_observations.model_dump(exclude_none=True)

    # Create review
    db_review = ParkReview(
        user_id=user_id,
        park_name=park_name,
        shade_rating=review.shade_rating,
        seating_rating=review.seating_rating,
        restroom_cleanliness_rating=review.restroom_cleanliness_rating,
        restroom_availability_rating=review.restroom_availability_rating,
        playground_quality_rating=review.playground_quality_rating,
        trail_quality_rating=review.trail_quality_rating,
        crowdedness_rating=review.crowdedness_rating,
        safety_rating=review.safety_rating,
        containment_rating=review.containment_rating,
        overall_rating=review.overall_rating,
        playground_best_age_min=review.playground_best_age_min,
        playground_best_age_max=review.playground_best_age_max,
        tags=review.tags,
        mom_observations=mom_obs_dict,
        tips=review.tips,
        review_text=review.review_text,
        visit_date=review.visit_date,
        visit_day_of_week=review.visit_day_of_week,
        visit_time_of_day=review.visit_time_of_day,
        would_recommend=review.would_recommend
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)

    # Update aggregate ratings
    update_park_aggregate_ratings(db, park_name)

    # Check for badge contradictions and trigger disputes if needed
    check_badge_disputes(db, park_name, db_review)

    return ReviewResponse(
        id=db_review.id,
        park_name=db_review.park_name,
        user_id=db_review.user_id,
        user_display_name=user.display_name,
        shade_rating=db_review.shade_rating,
        seating_rating=db_review.seating_rating,
        restroom_cleanliness_rating=db_review.restroom_cleanliness_rating,
        restroom_availability_rating=db_review.restroom_availability_rating,
        playground_quality_rating=db_review.playground_quality_rating,
        trail_quality_rating=db_review.trail_quality_rating,
        crowdedness_rating=db_review.crowdedness_rating,
        safety_rating=db_review.safety_rating,
        containment_rating=db_review.containment_rating,
        overall_rating=db_review.overall_rating,
        playground_best_age_min=db_review.playground_best_age_min,
        playground_best_age_max=db_review.playground_best_age_max,
        mom_observations=db_review.mom_observations,
        tags=db_review.tags or [],
        tips=db_review.tips,
        review_text=db_review.review_text,
        visit_date=db_review.visit_date,
        visit_day_of_week=db_review.visit_day_of_week,
        visit_time_of_day=db_review.visit_time_of_day,
        would_recommend=db_review.would_recommend,
        created_at=db_review.created_at,
        helpful_count=db_review.helpful_count or 0
    )


@app.get("/parks/{park_name}/reviews", response_model=ReviewListResponse, tags=["Reviews"])
async def get_park_reviews(
    park_name: str,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all reviews for a park."""
    reviews = db.query(ParkReview).filter(
        ParkReview.park_name == park_name
    ).order_by(ParkReview.created_at.desc()).offset(offset).limit(limit).all()

    total = db.query(ParkReview).filter(ParkReview.park_name == park_name).count()

    # Get aggregate data
    aggregate = db.query(ParkAggregateRating).filter(
        ParkAggregateRating.park_name == park_name
    ).first()

    review_responses = []
    for r in reviews:
        user = db.query(User).filter(User.id == r.user_id).first()
        review_responses.append(ReviewResponse(
            id=r.id,
            park_name=r.park_name,
            user_id=r.user_id,
            user_display_name=user.display_name if user else None,
            shade_rating=r.shade_rating,
            seating_rating=r.seating_rating,
            restroom_cleanliness_rating=r.restroom_cleanliness_rating,
            restroom_availability_rating=r.restroom_availability_rating,
            playground_quality_rating=r.playground_quality_rating,
            trail_quality_rating=r.trail_quality_rating,
            crowdedness_rating=r.crowdedness_rating,
            safety_rating=r.safety_rating,
            containment_rating=r.containment_rating,
            overall_rating=r.overall_rating,
            playground_best_age_min=r.playground_best_age_min,
            playground_best_age_max=r.playground_best_age_max,
            mom_observations=r.mom_observations,
            tags=r.tags or [],
            tips=r.tips,
            review_text=r.review_text,
            visit_date=r.visit_date,
            visit_day_of_week=r.visit_day_of_week,
            visit_time_of_day=r.visit_time_of_day,
            would_recommend=r.would_recommend,
            created_at=r.created_at,
            helpful_count=r.helpful_count or 0
        ))

    return ReviewListResponse(
        park_name=park_name,
        reviews=review_responses,
        total_count=total,
        average_overall=aggregate.avg_overall if aggregate else None,
        mom_score=aggregate.mom_score if aggregate else None,
        top_tags=aggregate.top_tags if aggregate else []
    )


@app.post("/reviews/{review_id}/helpful", tags=["Reviews"])
async def mark_review_helpful(review_id: int, db: Session = Depends(get_db)):
    """Mark a review as helpful (increment helpful count)."""
    review = db.query(ParkReview).filter(ParkReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.helpful_count = (review.helpful_count or 0) + 1
    db.commit()

    return {"message": "Marked as helpful", "helpful_count": review.helpful_count}


def check_badge_disputes(db: Session, park_name: str, review: ParkReview):
    """
    Check if a new review contradicts any earned badges for this park.
    If a review rates a badge-relevant quality low (below negative_threshold),
    it creates a negative confirmation. When enough negatives accumulate
    within the dispute window, the badge status changes to "disputed" or "lost".
    """
    # Get all earned badges for this park
    earned_badges = db.query(ParkBadge).filter(
        ParkBadge.park_name == park_name,
        ParkBadge.is_earned == True,  # noqa: E712
        ParkBadge.status.in_(["earned", "disputed"])
    ).all()

    if not earned_badges:
        return

    for badge in earned_badges:
        mapping = BADGE_RATING_MAP.get(badge.badge_id)
        if not mapping:
            continue

        # Get the relevant rating from the review
        rating_value = getattr(review, mapping["field"], None)
        if rating_value is None:
            continue

        # Check if this review contradicts the badge
        if rating_value <= mapping["negative_threshold"]:
            # Create a negative confirmation
            neg_confirmation = BadgeConfirmation(
                user_id=review.user_id,
                park_name=park_name,
                badge_id=badge.badge_id,
                review_id=review.id,
                is_negative=True,
                confirmed_at=datetime.utcnow()
            )
            db.add(neg_confirmation)
            badge.negative_count = (badge.negative_count or 0) + 1

            # Count recent negative confirmations within the dispute window
            window_start = datetime.utcnow() - timedelta(days=DISPUTE_WINDOW_DAYS)
            recent_negatives = db.query(BadgeConfirmation).filter(
                BadgeConfirmation.park_name == park_name,
                BadgeConfirmation.badge_id == badge.badge_id,
                BadgeConfirmation.is_negative == True,  # noqa: E712
                BadgeConfirmation.confirmed_at >= window_start
            ).count()
            # Add 1 for the one we just created (not yet flushed)
            recent_negatives += 1

            if recent_negatives >= DISPUTE_NEGATIVE_THRESHOLD:
                if badge.status == "earned":
                    badge.status = "disputed"
                elif badge.status == "disputed" and recent_negatives >= DISPUTE_NEGATIVE_THRESHOLD * 2:
                    # Double the threshold to go from disputed to lost
                    badge.status = "lost"
                    badge.is_earned = False

    db.commit()


def update_park_aggregate_ratings(db: Session, park_name: str):
    """Update aggregate ratings for a park after a new review."""
    reviews = db.query(ParkReview).filter(ParkReview.park_name == park_name).all()

    if not reviews:
        return

    # Calculate averages
    def avg(values):
        valid = [v for v in values if v is not None]
        return sum(valid) / len(valid) if valid else None

    def mode(values):
        """Get most common value."""
        valid = [v for v in values if v is not None]
        if not valid:
            return None
        counts = {}
        for v in valid:
            counts[v] = counts.get(v, 0) + 1
        return max(counts.keys(), key=lambda k: counts[k])

    def majority_bool(values):
        """Get majority boolean value."""
        valid = [v for v in values if v is not None]
        if not valid:
            return None
        true_count = sum(1 for v in valid if v)
        return true_count > len(valid) / 2

    avg_shade = avg([r.shade_rating for r in reviews])
    avg_seating = avg([r.seating_rating for r in reviews])
    avg_restroom_cleanliness = avg([r.restroom_cleanliness_rating for r in reviews])
    avg_restroom_availability = avg([r.restroom_availability_rating for r in reviews])
    avg_playground = avg([r.playground_quality_rating for r in reviews])
    avg_trail = avg([r.trail_quality_rating for r in reviews])
    avg_crowdedness = avg([r.crowdedness_rating for r in reviews])
    avg_safety = avg([r.safety_rating for r in reviews])
    avg_containment = avg([r.containment_rating for r in reviews])
    avg_overall = avg([r.overall_rating for r in reviews])

    # Calculate Mom Score (weighted average)
    # Weights: restrooms=20%, playground=20%, containment=20%, shade=15%, safety=15%, trails=10%
    weights = []
    mom_score_values = []
    if avg_restroom_cleanliness:
        mom_score_values.append(avg_restroom_cleanliness * 0.20)
        weights.append(0.20)
    if avg_playground:
        mom_score_values.append(avg_playground * 0.20)
        weights.append(0.20)
    if avg_containment:
        mom_score_values.append(avg_containment * 0.20)
        weights.append(0.20)
    if avg_shade:
        mom_score_values.append(avg_shade * 0.15)
        weights.append(0.15)
    if avg_safety:
        mom_score_values.append(avg_safety * 0.15)
        weights.append(0.15)
    if avg_trail:
        mom_score_values.append(avg_trail * 0.10)
        weights.append(0.10)

    mom_score = sum(mom_score_values) / sum(weights) if weights else None

    # Get top tags
    all_tags = []
    for r in reviews:
        if r.tags:
            all_tags.extend(r.tags)
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.keys(), key=lambda t: tag_counts[t], reverse=True)[:10]

    # Recommendation rate
    recommend_count = sum(1 for r in reviews if r.would_recommend)
    recommend_percentage = (recommend_count / len(reviews)) * 100 if reviews else None

    # Aggregate mom observations from all reviews
    fencing_types = []
    sightlines = []
    single_vantage = []
    containment_notes = []
    stroller_friendly = []
    parking_distances = []
    quick_exits = []
    logistics_notes = []
    restroom_distances = []
    changing_womens = []
    changing_mens = []
    family_restrooms = []
    potty_friendly = []
    restroom_notes = []
    shade_types = []
    playground_shaded = []
    seating_shaded = []
    noise_levels = []
    sensory_friendly_vals = []
    coffee_nearby = []
    coffee_names = []

    for r in reviews:
        if r.mom_observations:
            obs = r.mom_observations
            # Containment
            if obs.get("containment"):
                c = obs["containment"]
                if c.get("fencing_type"):
                    fencing_types.append(c["fencing_type"])
                if c.get("sightlines"):
                    sightlines.append(c["sightlines"])
                if c.get("single_vantage_point") is not None:
                    single_vantage.append(c["single_vantage_point"])
                if c.get("notes"):
                    containment_notes.append(c["notes"])

            # Logistics
            if obs.get("logistics"):
                l = obs["logistics"]
                if l.get("stroller_path_paved") is not None:
                    stroller_friendly.append(l["stroller_path_paved"])
                if l.get("parking_to_playground_distance"):
                    parking_distances.append(l["parking_to_playground_distance"])
                if l.get("quick_exit_possible") is not None:
                    quick_exits.append(l["quick_exit_possible"])
                if l.get("notes"):
                    logistics_notes.append(l["notes"])

            # Restrooms
            if obs.get("restrooms"):
                rr = obs["restrooms"]
                if rr.get("distance_from_playground"):
                    restroom_distances.append(rr["distance_from_playground"])
                if rr.get("changing_table_womens") is not None:
                    changing_womens.append(rr["changing_table_womens"])
                if rr.get("changing_table_mens") is not None:
                    changing_mens.append(rr["changing_table_mens"])
                if rr.get("family_restroom") is not None:
                    family_restrooms.append(rr["family_restroom"])
                if rr.get("potty_training_friendly") is not None:
                    potty_friendly.append(rr["potty_training_friendly"])
                if rr.get("notes"):
                    restroom_notes.append(rr["notes"])

            # Shade
            if obs.get("shade"):
                s = obs["shade"]
                if s.get("shade_type"):
                    shade_types.append(s["shade_type"])
                if s.get("playground_shaded") is not None:
                    playground_shaded.append(s["playground_shaded"])
                if s.get("seating_shaded") is not None:
                    seating_shaded.append(s["seating_shaded"])

            # Environment
            if obs.get("noise_environment"):
                n = obs["noise_environment"]
                if n.get("noise_level"):
                    noise_levels.append(n["noise_level"])
                if n.get("sensory_friendly") is not None:
                    sensory_friendly_vals.append(n["sensory_friendly"])

            # Nearby
            if obs.get("nearby"):
                nb = obs["nearby"]
                if nb.get("coffee_shop_nearby") is not None:
                    coffee_nearby.append(nb["coffee_shop_nearby"])
                if nb.get("coffee_shop_name"):
                    coffee_names.append(nb["coffee_shop_name"])

        # Also collect tips
        if r.tips:
            containment_notes.append(r.tips)

    # Update or create aggregate
    aggregate = db.query(ParkAggregateRating).filter(
        ParkAggregateRating.park_name == park_name
    ).first()

    if not aggregate:
        aggregate = ParkAggregateRating(park_name=park_name)
        db.add(aggregate)

    # Basic ratings
    aggregate.total_reviews = len(reviews)
    aggregate.avg_shade = avg_shade
    aggregate.avg_seating = avg_seating
    aggregate.avg_restroom_cleanliness = avg_restroom_cleanliness
    aggregate.avg_restroom_availability = avg_restroom_availability
    aggregate.avg_playground_quality = avg_playground
    aggregate.avg_trail_quality = avg_trail
    aggregate.avg_crowdedness = avg_crowdedness
    aggregate.avg_safety = avg_safety
    aggregate.avg_containment = avg_containment
    aggregate.avg_overall = avg_overall
    aggregate.mom_score = mom_score
    aggregate.top_tags = top_tags
    aggregate.recommend_percentage = recommend_percentage

    # Mom insights aggregates
    aggregate.fencing_consensus = mode(fencing_types)
    aggregate.sightlines_consensus = mode(sightlines)
    aggregate.single_vantage_possible = majority_bool(single_vantage)
    aggregate.containment_notes = list(set(containment_notes))[:5]  # Top 5 unique notes

    aggregate.stroller_friendly = majority_bool(stroller_friendly)
    aggregate.parking_distance_consensus = mode(parking_distances)
    aggregate.quick_exit_friendly = majority_bool(quick_exits)
    aggregate.logistics_notes = list(set(logistics_notes))[:3]

    aggregate.restroom_distance_consensus = mode(restroom_distances)
    aggregate.has_changing_tables = majority_bool(changing_womens)
    aggregate.mens_changing_table = majority_bool(changing_mens)
    aggregate.family_restroom = majority_bool(family_restrooms)
    aggregate.potty_training_friendly = majority_bool(potty_friendly)
    aggregate.restroom_notes = list(set(restroom_notes))[:3]

    aggregate.shade_type_consensus = mode(shade_types)
    aggregate.playground_shaded = majority_bool(playground_shaded)
    aggregate.seating_shaded = majority_bool(seating_shaded)

    aggregate.noise_level_consensus = mode(noise_levels)
    aggregate.sensory_friendly = majority_bool(sensory_friendly_vals)

    aggregate.coffee_nearby = majority_bool(coffee_nearby)
    aggregate.coffee_shop_names = list(set(coffee_names))[:3]

    # Generate RAG-ready summary
    aggregate.rag_summary = generate_rag_summary(aggregate, top_tags)

    db.commit()


def generate_rag_summary(aggregate, top_tags: list) -> str:
    """Generate a natural language summary for RAG retrieval."""
    parts = []

    # Containment/Safety
    if aggregate.fencing_consensus:
        fence_desc = aggregate.fencing_consensus.replace("-", " ")
        parts.append(f"This park is {fence_desc}")
    if aggregate.sightlines_consensus:
        parts.append(f"with {aggregate.sightlines_consensus} sightlines")
    if aggregate.single_vantage_possible:
        parts.append("- parents can see the entire play area from a single bench")

    # Surface (from tags)
    surface_tags = [t for t in top_tags if "surface" in t]
    if surface_tags:
        parts.append(f". The playground has {surface_tags[0].replace('-', ' ')}")

    # Restrooms
    if aggregate.restroom_distance_consensus:
        parts.append(f". Restrooms are {aggregate.restroom_distance_consensus.replace('-', ' ')} from the playground")
    if aggregate.mens_changing_table:
        parts.append("with changing tables in both men's and women's rooms")
    elif aggregate.has_changing_tables:
        parts.append("with a changing table in the women's room")
    if aggregate.potty_training_friendly:
        parts.append("and are potty-training friendly")

    # Shade
    if aggregate.shade_type_consensus:
        parts.append(f". Shade is {aggregate.shade_type_consensus.replace('-', ' ')}")
    if aggregate.playground_shaded:
        parts.append("covering the playground")

    # Stroller/Logistics
    if aggregate.stroller_friendly:
        parts.append(". Paths are paved and stroller-friendly")
    if aggregate.quick_exit_friendly:
        parts.append("with easy quick-exit parking")

    # Environment
    if aggregate.noise_level_consensus:
        parts.append(f". The atmosphere is {aggregate.noise_level_consensus}")
    if aggregate.sensory_friendly:
        parts.append("and sensory-friendly")

    # Coffee nearby
    if aggregate.coffee_nearby and aggregate.coffee_shop_names:
        parts.append(f". Nearby coffee: {', '.join(aggregate.coffee_shop_names[:2])}")

    # Top tips
    if aggregate.containment_notes:
        parts.append(f". Tip: {aggregate.containment_notes[0]}")

    return "".join(parts) if parts else None


# ============================================================
# HEALTH CHECK
# ============================================================

# ============================================================
# WEATHER
# ============================================================

@app.get("/weather/current", response_model=WeatherResponse, tags=["Weather"])
async def get_current_weather(
    lat: float = Query(default=38.8462, description="Latitude (defaults to Fairfax County center)"),
    lon: float = Query(default=-77.3064, description="Longitude (defaults to Fairfax County center)")
):
    """
    Get current weather with mom-friendly recommendations.

    Returns temperature, conditions, and suggestions for:
    - Activities that match the weather (splash pads on hot days, etc.)
    - Things to avoid (unshaded playgrounds when UV is high, etc.)
    - Suggested search queries for the AI assistant
    """
    weather_service = get_weather_service()

    try:
        weather = await weather_service.get_current_weather(lat=lat, lon=lon)
        return WeatherResponse(
            temperature_f=weather.temperature_f,
            feels_like_f=weather.feels_like_f,
            humidity=weather.humidity,
            precipitation_probability=weather.precipitation_probability,
            condition=weather.condition.value,
            uv_index=weather.uv_index,
            wind_speed_mph=weather.wind_speed_mph,
            is_daytime=weather.is_daytime,
            mom_tip=weather.mom_tip,
            suggested_activities=weather.suggested_activities,
            things_to_avoid=weather.things_to_avoid,
            suggested_queries=weather.suggested_queries
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Weather service unavailable: {str(e)}")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "llm_model": LLM_MODEL,
        "llm_provider": "anthropic",
        "embedding_model": EMBEDDING_MODEL
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
