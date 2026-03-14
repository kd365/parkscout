"""
Database Models for Parks Finder API

User data schema supporting:
- User profiles with preferences
- Saved/favorite parks
- Mom-centric crowdsourced reviews
- Search history
- Conversation sessions
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, create_engine, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


# ============================================================
# DISTANCE CATEGORIES (for RAG prompts)
# ============================================================
# "Near" = within 10 min drive
# "Moderately close" = 10-15 min drive
# "Driveable" = 15+ min drive (still in Fairfax)

DISTANCE_CATEGORIES = {
    "near": {"max_minutes": 10, "label": "Near you"},
    "moderate": {"min_minutes": 10, "max_minutes": 15, "label": "Moderately close"},
    "driveable": {"min_minutes": 15, "label": "Driveable"}
}


# ============================================================
# USER MODELS
# ============================================================

class User(Base):
    """User account and profile."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Auth
    apple_id = Column(String(255), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255), nullable=True)  # For email/password auth

    # Profile
    display_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Location (for distance calculations)
    home_lat = Column(Float)
    home_lng = Column(Float)

    # Preferences
    preferences = Column(JSON, default=dict)

    # Relationships
    saved_parks = relationship("SavedPark", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("ParkReview", back_populates="user", cascade="all, delete-orphan")
    badge_confirmations = relationship("BadgeConfirmation", back_populates="user", cascade="all, delete-orphan")

    @property
    def review_count(self) -> int:
        """Count of reviews submitted by this user."""
        return len(self.reviews) if self.reviews else 0

    @property
    def tier(self) -> dict:
        """Get user's current tier based on review count."""
        return get_user_tier(self.review_count)


# ============================================================
# MOM-CENTRIC PARK REVIEWS
# ============================================================

class ParkReview(Base):
    """
    Crowdsourced mom-centric park review.

    Rating scale: 1-5 stars for each category
    """
    __tablename__ = "park_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    park_name = Column(String(255), index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    visit_date = Column(DateTime)  # When they visited

    # ══════════════════════════════════════════════════════════
    # MOM-CENTRIC RATING CATEGORIES (1-5 scale)
    # ══════════════════════════════════════════════════════════

    # SHADE: Is there shade for hot days?
    # 1 = No shade at all
    # 3 = Some shaded areas
    # 5 = Excellent shade coverage, shaded playground
    shade_rating = Column(Integer, CheckConstraint('shade_rating >= 1 AND shade_rating <= 5'))

    # SEATING: Places for parents to sit while kids play
    # 1 = No seating
    # 3 = A few benches
    # 5 = Plenty of seating with good playground views
    seating_rating = Column(Integer, CheckConstraint('seating_rating >= 1 AND seating_rating <= 5'))

    # RESTROOM CLEANLINESS: Are restrooms clean and well-maintained?
    # 1 = Dirty/unusable
    # 3 = Acceptable
    # 5 = Very clean, well-stocked
    restroom_cleanliness_rating = Column(Integer, CheckConstraint('restroom_cleanliness_rating >= 1 AND restroom_cleanliness_rating <= 5'))

    # RESTROOM AVAILABILITY: Are restrooms actually open/accessible?
    # 1 = No restrooms or always locked
    # 3 = Portable toilets only
    # 5 = Permanent restrooms, always open
    restroom_availability_rating = Column(Integer, CheckConstraint('restroom_availability_rating >= 1 AND restroom_availability_rating <= 5'))

    # PLAYGROUND QUALITY: How good is the playground?
    # 1 = Old/broken equipment, unsafe
    # 3 = Decent equipment, some wear
    # 5 = Modern, well-maintained, age-appropriate sections
    playground_quality_rating = Column(Integer, CheckConstraint('playground_quality_rating >= 1 AND playground_quality_rating <= 5'))

    # PLAYGROUND AGE RANGE: Best age for the playground
    playground_best_age_min = Column(Integer)  # e.g., 2
    playground_best_age_max = Column(Integer)  # e.g., 8

    # TRAIL QUALITY: For stroller-friendliness and walking
    # 1 = No trails or very rough
    # 3 = Unpaved but walkable
    # 5 = Paved, stroller-friendly, well-maintained
    trail_quality_rating = Column(Integer, CheckConstraint('trail_quality_rating >= 1 AND trail_quality_rating <= 5'))

    # CROWDEDNESS: How crowded does it get?
    # 1 = Always packed, hard to find parking
    # 3 = Moderate crowds
    # 5 = Usually quiet, plenty of space
    crowdedness_rating = Column(Integer, CheckConstraint('crowdedness_rating >= 1 AND crowdedness_rating <= 5'))

    # SAFETY: Overall safety perception
    # 1 = Felt unsafe
    # 3 = Generally safe
    # 5 = Very safe, good sightlines, enclosed areas
    safety_rating = Column(Integer, CheckConstraint('safety_rating >= 1 AND safety_rating <= 5'))

    # CONTAINMENT: How easy is it to watch your kids? (The "Can I See My Kid" factor)
    # 1 = Impossible to watch, many blind spots, open to roads
    # 3 = Can watch with effort, some blind spots
    # 5 = Excellent sightlines, can see everything from one bench
    containment_rating = Column(Integer, CheckConstraint('containment_rating >= 1 AND containment_rating <= 5'))

    # ══════════════════════════════════════════════════════════
    # MOM-LOGIC OBSERVATIONS (Structured Data)
    # ══════════════════════════════════════════════════════════

    # Store as JSON for flexibility
    mom_observations = Column(JSON, default=dict)
    # Structure: {
    #   "containment": {
    #     "fencing_type": "fully-fenced",
    #     "sightlines": "excellent",
    #     "single_vantage_point": true,
    #     "notes": "Can see swings and slide from central bench"
    #   },
    #   "surface": {
    #     "surface_type": "rubber-new",
    #     "condition": "excellent",
    #     "notes": "Recently resurfaced"
    #   },
    #   "logistics": {
    #     "stroller_path_paved": true,
    #     "parking_to_playground_distance": "close",
    #     "quick_exit_possible": true
    #   },
    #   "restrooms": {
    #     "distance_from_playground": "adjacent",
    #     "changing_table_womens": true,
    #     "changing_table_mens": true,
    #     "potty_training_friendly": true
    #   },
    #   "shade": {
    #     "shade_type": "natural-trees",
    #     "playground_shaded": true,
    #     "best_time_for_shade": "morning"
    #   },
    #   "noise_environment": {
    #     "noise_level": "quiet",
    #     "sensory_friendly": true
    #   },
    #   "nearby": {
    #     "coffee_shop_nearby": true,
    #     "coffee_shop_name": "Starbucks on Main St"
    #   }
    # }

    # ══════════════════════════════════════════════════════════
    # ADDITIONAL INFO
    # ══════════════════════════════════════════════════════════

    # Overall recommendation
    overall_rating = Column(Integer, CheckConstraint('overall_rating >= 1 AND overall_rating <= 5'))
    would_recommend = Column(Boolean, default=True)

    # Free-form feedback
    review_text = Column(Text)
    tips = Column(Text)  # "Best parking is on the east side", "Bring bug spray"

    # Visit context
    visit_day_of_week = Column(String(20))  # "Saturday"
    visit_time_of_day = Column(String(20))  # "Morning", "Afternoon"
    weather_conditions = Column(String(50))  # "Sunny and hot"

    # Tags (multiple choice)
    tags = Column(JSON, default=list)
    # Example tags:
    # ["stroller-friendly", "good-for-toddlers", "picnic-spot",
    #  "birthday-party-venue", "needs-bug-spray", "muddy-when-wet"]

    # Photos (URLs to uploaded images)
    photo_urls = Column(JSON, default=list)

    # Helpful votes from other users
    helpful_count = Column(Integer, default=0)

    # Relationship
    user = relationship("User", back_populates="reviews")


class ParkHours(Base):
    """
    Crowdsourced/official park hours.
    Separate table since hours can vary by season.
    """
    __tablename__ = "park_hours"

    id = Column(Integer, primary_key=True, index=True)
    park_name = Column(String(255), index=True)

    # Source
    source = Column(String(50))  # "official", "crowdsourced"
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified = Column(Boolean, default=False)

    # Season/Date range
    season = Column(String(50))  # "summer", "winter", "year-round"
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Hours by day
    monday_open = Column(String(10))  # "6:00 AM"
    monday_close = Column(String(10))  # "8:00 PM"
    tuesday_open = Column(String(10))
    tuesday_close = Column(String(10))
    wednesday_open = Column(String(10))
    wednesday_close = Column(String(10))
    thursday_open = Column(String(10))
    thursday_close = Column(String(10))
    friday_open = Column(String(10))
    friday_close = Column(String(10))
    saturday_open = Column(String(10))
    saturday_close = Column(String(10))
    sunday_open = Column(String(10))
    sunday_close = Column(String(10))

    # Special notes
    notes = Column(Text)  # "Closes at dusk", "Restrooms close at 5pm"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ParkAggregateRating(Base):
    """
    Pre-computed aggregate ratings for each park.
    Updated whenever a new review is submitted.
    """
    __tablename__ = "park_aggregate_ratings"

    id = Column(Integer, primary_key=True, index=True)
    park_name = Column(String(255), unique=True, index=True)

    # Review counts
    total_reviews = Column(Integer, default=0)
    reviews_last_30_days = Column(Integer, default=0)

    # Average ratings (computed from reviews)
    avg_shade = Column(Float)
    avg_seating = Column(Float)
    avg_restroom_cleanliness = Column(Float)
    avg_restroom_availability = Column(Float)
    avg_playground_quality = Column(Float)
    avg_trail_quality = Column(Float)
    avg_crowdedness = Column(Float)
    avg_safety = Column(Float)
    avg_containment = Column(Float)  # The "Can I See My Kid" score
    avg_overall = Column(Float)

    # Computed "Mom Score" (weighted average)
    # Weights: restrooms=20%, playground=20%, containment=20%, shade=15%, safety=15%, trails=10%
    mom_score = Column(Float)

    # Best ages (mode from reviews)
    typical_best_age_min = Column(Integer)
    typical_best_age_max = Column(Integer)

    # Most common tags
    top_tags = Column(JSON, default=list)

    # Recommendation rate
    recommend_percentage = Column(Float)

    # ══════════════════════════════════════════════════════════
    # AGGREGATED MOM INSIGHTS (consensus from reviews)
    # ══════════════════════════════════════════════════════════

    # Containment consensus
    fencing_consensus = Column(String(50))  # Most reported fencing type
    sightlines_consensus = Column(String(50))  # "excellent", "good", etc.
    single_vantage_possible = Column(Boolean)
    containment_notes = Column(JSON, default=list)  # Top notes from reviews

    # Surface consensus
    surface_type_consensus = Column(String(50))
    surface_condition_consensus = Column(String(50))

    # Logistics consensus
    stroller_friendly = Column(Boolean)
    parking_distance_consensus = Column(String(50))
    quick_exit_friendly = Column(Boolean)
    logistics_notes = Column(JSON, default=list)

    # Restroom consensus
    restroom_distance_consensus = Column(String(50))
    has_changing_tables = Column(Boolean)
    mens_changing_table = Column(Boolean)
    family_restroom = Column(Boolean)
    potty_training_friendly = Column(Boolean)
    restroom_notes = Column(JSON, default=list)

    # Shade consensus
    shade_type_consensus = Column(String(50))
    playground_shaded = Column(Boolean)
    seating_shaded = Column(Boolean)

    # Environment consensus
    noise_level_consensus = Column(String(50))
    sensory_friendly = Column(Boolean)

    # Nearby conveniences
    coffee_nearby = Column(Boolean)
    coffee_shop_names = Column(JSON, default=list)

    # RAG-ready summary (pre-generated for fast retrieval)
    rag_summary = Column(Text)
    # Example: "Clemyjontri Park is fully fenced with excellent sightlines -
    # parents can see the entire playground from a single bench. The rubber
    # surface is new and clean. Restrooms are adjacent to the playground with
    # changing tables in both men's and women's rooms. Great for ages 2-8.
    # Tip: Arrive before 10am on weekends for parking."

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# SAVED PARKS
# ============================================================

class SavedPark(Base):
    """User's saved/favorite parks."""
    __tablename__ = "saved_parks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    park_name = Column(String(255), index=True)

    saved_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    tags = Column(JSON, default=list)

    visit_count = Column(Integer, default=0)
    last_visited = Column(DateTime)

    user = relationship("User", back_populates="saved_parks")


# ============================================================
# CONVERSATIONS & MEMORY
# ============================================================

class Conversation(Base):
    """Chat conversation session."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    session_id = Column(String(36), unique=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    title = Column(String(255))
    summary = Column(Text)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)

    role = Column(String(20))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    response_time_seconds = Column(Float)
    parks_mentioned = Column(JSON, default=list)
    retrieval_context = Column(Text)

    conversation = relationship("Conversation", back_populates="messages")


# ============================================================
# SEARCH & ANALYTICS
# ============================================================

class SearchHistory(Base):
    """Track user searches for analytics and personalization."""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    query = Column(Text)
    searched_at = Column(DateTime, default=datetime.utcnow)

    parks_returned = Column(JSON, default=list)
    clicked_park = Column(String(255))

    location_lat = Column(Float)
    location_lng = Column(Float)
    filters_used = Column(JSON, default=dict)

    user = relationship("User", back_populates="search_history")


# ============================================================
# PARK COORDINATES (for distance calculations)
# ============================================================

class ParkLocation(Base):
    """
    Geocoded park locations for distance calculations.
    Pre-computed from addresses.
    """
    __tablename__ = "park_locations"

    id = Column(Integer, primary_key=True, index=True)
    park_name = Column(String(255), unique=True, index=True)

    # Coordinates
    latitude = Column(Float)
    longitude = Column(Float)

    # Address (for verification)
    address = Column(String(500))
    city = Column(String(100))

    # Geocoding metadata
    geocoded_at = Column(DateTime, default=datetime.utcnow)
    geocode_source = Column(String(50))  # "google", "nominatim", "manual"
    geocode_confidence = Column(Float)  # 0-1


# ============================================================
# PARKSCOUT BADGE SYSTEM
# ============================================================

# Badge definitions with thresholds for earning
BADGE_DEFINITIONS = {
    # Shade/Weather Protection
    "solar_shield": {
        "name": "Solar Shield",
        "description": "Excellent canopy cover and shade",
        "icon": "sun.max.trianglebadge.exclamationmark",
        "category": "comfort",
        "threshold": 3,  # Confirmations needed
        "criteria": "shade_rating >= 4"
    },
    # Fencing/Safety
    "the_fortress": {
        "name": "The Fortress",
        "description": "Fully fenced playground area",
        "icon": "shield.checkered",
        "category": "safety",
        "threshold": 3,
        "criteria": "fenced_playground"
    },
    # Restrooms
    "golden_throne": {
        "name": "Golden Throne",
        "description": "Exceptionally clean restrooms",
        "icon": "sparkles",
        "category": "facilities",
        "threshold": 3,
        "criteria": "restroom_cleanliness_rating >= 4"
    },
    # Toddler-Friendly
    "tiny_explorer": {
        "name": "Tiny Explorer",
        "description": "Perfect for toddlers (ages 1-3)",
        "icon": "figure.and.child.holdinghands",
        "category": "age_range",
        "threshold": 3,
        "criteria": "toddler_friendly"
    },
    # Stroller Access
    "smooth_sailing": {
        "name": "Smooth Sailing",
        "description": "Excellent stroller-friendly paths",
        "icon": "figure.walk",
        "category": "accessibility",
        "threshold": 3,
        "criteria": "stroller_friendly_rating >= 4"
    },
    # Picnic Areas
    "feast_grounds": {
        "name": "Feast Grounds",
        "description": "Great picnic facilities",
        "icon": "fork.knife",
        "category": "facilities",
        "threshold": 3,
        "criteria": "picnic_facilities"
    },
    # Water Features
    "splash_zone": {
        "name": "Splash Zone",
        "description": "Water play area or splash pad",
        "icon": "drop.fill",
        "category": "features",
        "threshold": 3,
        "criteria": "water_features"
    },
    # Dog-Friendly
    "paws_welcome": {
        "name": "Paws Welcome",
        "description": "Dog-friendly with good off-leash area",
        "icon": "dog.fill",
        "category": "pets",
        "threshold": 3,
        "criteria": "dog_friendly"
    },
}

# Badge-to-rating mapping for contradiction detection
# Maps badge_id to the review rating field and the threshold below which
# a review is considered contradicting (negative confirmation)
BADGE_RATING_MAP = {
    "solar_shield": {"field": "shade_rating", "negative_threshold": 2},
    "golden_throne": {"field": "restroom_cleanliness_rating", "negative_threshold": 2},
    "smooth_sailing": {"field": "trail_quality_rating", "negative_threshold": 2},
    "the_fortress": {"field": "containment_rating", "negative_threshold": 2},
    "tiny_explorer": {"field": "playground_quality_rating", "negative_threshold": 2},
    "feast_grounds": {"field": "overall_rating", "negative_threshold": 2},
    "splash_zone": {"field": "overall_rating", "negative_threshold": 2},
    "paws_welcome": {"field": "overall_rating", "negative_threshold": 2},
}

# Number of negative confirmations within the dispute window to trigger dispute
DISPUTE_NEGATIVE_THRESHOLD = 2
# Days within which negative confirmations are counted
DISPUTE_WINDOW_DAYS = 90

# User tier definitions
USER_TIERS = {
    "tenderfoot": {"min_reviews": 0, "max_reviews": 4, "name": "Tenderfoot", "icon": "leaf"},
    "trailblazer": {"min_reviews": 5, "max_reviews": 14, "name": "Trailblazer", "icon": "flame"},
    "pathfinder": {"min_reviews": 15, "max_reviews": 29, "name": "Pathfinder", "icon": "map"},
    "park_legend": {"min_reviews": 30, "max_reviews": 999999, "name": "Park Legend", "icon": "star.fill"},
}


def get_user_tier(review_count: int) -> dict:
    """Get user tier based on review count."""
    for tier_id, tier in USER_TIERS.items():
        if tier["min_reviews"] <= review_count <= tier["max_reviews"]:
            return {"id": tier_id, **tier}
    return {"id": "tenderfoot", **USER_TIERS["tenderfoot"]}


class ParkBadge(Base):
    """
    Badges earned by parks through user confirmations.
    A badge is earned when threshold confirmations are reached.
    Badge lifecycle: earned → disputed → lost → re-earned.
    """
    __tablename__ = "park_badges"

    id = Column(Integer, primary_key=True, index=True)
    park_name = Column(String(255), index=True)
    badge_id = Column(String(50), index=True)  # e.g., "solar_shield"

    # When the badge was earned (enough confirmations)
    earned_at = Column(DateTime, default=datetime.utcnow)

    # Total confirmations received
    confirmation_count = Column(Integer, default=0)

    # Is the badge currently active (earned)
    is_earned = Column(Boolean, default=False)

    # Badge status: "earned", "disputed", "lost"
    # disputed = negative reviews accumulating, badge at risk
    # lost = too many contradicting reviews, badge revoked
    status = Column(String(20), default="earned")

    # Count of negative confirmations (contradicting reviews)
    negative_count = Column(Integer, default=0)


class BadgeConfirmation(Base):
    """
    Individual user confirmations for badge criteria.
    Tracks which users have confirmed which badges for which parks.
    """
    __tablename__ = "badge_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    park_name = Column(String(255), index=True)
    badge_id = Column(String(50), index=True)

    # When confirmed
    confirmed_at = Column(DateTime, default=datetime.utcnow)

    # Optional: linked to a review
    review_id = Column(Integer, ForeignKey("park_reviews.id"), nullable=True)

    # Whether this is a negative confirmation (contradicting the badge)
    # e.g., a low restroom rating contradicts a "Golden Throne" badge
    is_negative = Column(Boolean, default=False)

    user = relationship("User")
    review = relationship("ParkReview")


# ============================================================
# DATABASE SETUP
# ============================================================

def init_db(database_url: str = "sqlite:///./parks_finder.db"):
    """Initialize database and create tables."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


def get_session(engine):
    """Create a database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


if __name__ == "__main__":
    engine = init_db()
    print("Database initialized with tables:")
    for table in Base.metadata.tables:
        print(f"  - {table}")
