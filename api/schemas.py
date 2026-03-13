"""
Pydantic Schemas for API Request/Response Validation
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# QUERY SCHEMAS
# ============================================================

class QueryRequest(BaseModel):
    """Request to query the parks RAG system."""
    question: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = None  # For conversation continuity
    user_id: Optional[int] = None
    location: Optional[Dict[str, float]] = None  # {"lat": 38.84, "lng": -77.30}

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Where can I take my 3 year old?",
                "session_id": "abc-123-def",
                "location": {"lat": 38.8462, "lng": -77.3064}
            }
        }


class ParkMention(BaseModel):
    """A park mentioned in a response."""
    name: str
    relevance_score: Optional[float] = None
    distance_miles: Optional[float] = None


class QueryResponse(BaseModel):
    """Response from the RAG system."""
    answer: str
    session_id: str
    parks_mentioned: List[ParkMention] = []
    response_time_seconds: float
    conversation_turn: int = 1

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "For a 3-year-old, I recommend Clemyjontri Park...",
                "session_id": "abc-123-def",
                "parks_mentioned": [
                    {"name": "Clemyjontri Park", "distance_miles": 12.4},
                    {"name": "Burke Lake Park", "distance_miles": 8.2}
                ],
                "response_time_seconds": 2.3,
                "conversation_turn": 1
            }
        }


# ============================================================
# USER SCHEMAS
# ============================================================

class UserPreferencesSchema(BaseModel):
    """User preferences for personalization."""
    home_location: Optional[Dict[str, float]] = None
    children_ages: List[int] = []
    has_dog: bool = False
    accessibility_needs: bool = False
    preferred_distance_miles: float = 15.0
    notifications_enabled: bool = True


class UserCreate(BaseModel):
    """Create a new user."""
    apple_id: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    preferences: Optional[UserPreferencesSchema] = None


class UserResponse(BaseModel):
    """User profile response."""
    id: int
    display_name: Optional[str]
    email: Optional[str]
    created_at: datetime
    preferences: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Update user profile."""
    display_name: Optional[str] = None
    preferences: Optional[UserPreferencesSchema] = None


# ============================================================
# AUTH SCHEMAS
# ============================================================

class RegisterRequest(BaseModel):
    """Register a new user with email/password."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)
    display_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "mom@example.com",
                "password": "securepass123",
                "display_name": "Sarah"
            }
        }


class LoginRequest(BaseModel):
    """Login with email/password."""
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "mom@example.com",
                "password": "securepass123"
            }
        }


class AuthResponse(BaseModel):
    """Authentication response with token."""
    user_id: int
    email: str
    display_name: Optional[str]
    token: str  # Session token
    message: str = "Success"

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "email": "mom@example.com",
                "display_name": "Sarah",
                "token": "abc123-session-token",
                "message": "Login successful"
            }
        }


# ============================================================
# PARKSCOUT BADGE SCHEMAS
# ============================================================

class UserTier(BaseModel):
    """User tier information based on review count."""
    id: str  # e.g., "trailblazer"
    name: str  # e.g., "Trailblazer"
    icon: str  # SF Symbol name
    min_reviews: int
    max_reviews: int

    class Config:
        json_schema_extra = {
            "example": {
                "id": "trailblazer",
                "name": "Trailblazer",
                "icon": "flame",
                "min_reviews": 5,
                "max_reviews": 14
            }
        }


class BadgeDefinition(BaseModel):
    """Definition of a badge type."""
    id: str
    name: str
    description: str
    icon: str
    category: str
    threshold: int


class ParkBadgeSchema(BaseModel):
    """A badge earned by a park."""
    badge_id: str
    name: str
    description: str
    icon: str
    category: str
    confirmation_count: int
    is_earned: bool
    earned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BadgeConfirmRequest(BaseModel):
    """Request to confirm a badge for a park."""
    park_name: str
    badge_id: str
    review_id: Optional[int] = None  # Link to review if applicable

    class Config:
        json_schema_extra = {
            "example": {
                "park_name": "Burke Lake Park",
                "badge_id": "solar_shield"
            }
        }


class BadgeConfirmResponse(BaseModel):
    """Response after confirming a badge."""
    badge_id: str
    park_name: str
    new_count: int
    threshold: int
    badge_earned: bool
    message: str


class ParkBadgesResponse(BaseModel):
    """All badges for a park."""
    park_name: str
    earned_badges: List[ParkBadgeSchema]
    pending_badges: List[ParkBadgeSchema]  # Badges with some confirmations but not earned


class UserProfileWithTier(BaseModel):
    """Extended user profile with tier information."""
    id: int
    display_name: Optional[str]
    email: Optional[str]
    created_at: datetime
    review_count: int
    tier: UserTier
    badge_confirmations_count: int

    class Config:
        from_attributes = True


# ============================================================
# SAVED PARKS SCHEMAS
# ============================================================

class SaveParkRequest(BaseModel):
    """Save a park to favorites."""
    park_name: str
    notes: Optional[str] = None
    tags: List[str] = []


class SavedParkResponse(BaseModel):
    """Saved park details."""
    id: int
    park_name: str
    saved_at: datetime
    notes: Optional[str]
    tags: List[str]
    visit_count: int
    last_visited: Optional[datetime]

    class Config:
        from_attributes = True


class MarkVisitRequest(BaseModel):
    """Mark a park as visited."""
    park_name: str


# ============================================================
# CONVERSATION SCHEMAS
# ============================================================

class ConversationSummary(BaseModel):
    """Brief conversation summary."""
    session_id: str
    title: Optional[str]
    started_at: datetime
    message_count: int
    is_active: bool


class MessageSchema(BaseModel):
    """Single message in conversation."""
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime
    parks_mentioned: List[str] = []


class ConversationDetail(BaseModel):
    """Full conversation with messages."""
    session_id: str
    title: Optional[str]
    started_at: datetime
    messages: List[MessageSchema]


# ============================================================
# PARK SCHEMAS
# ============================================================

class ParkAmenities(BaseModel):
    """Park amenities structure."""
    playground: str = "No"
    restrooms: str = "No"
    picnic_shelters: str = "No"
    trails: str = "None"
    parking: str = "Unknown"
    water_activities: str = "None"
    special_features: List[str] = []
    dog_friendly: str = "Unknown"


class ParkSchema(BaseModel):
    """Full park details."""
    park_name: str
    classification: Optional[str]
    address: Optional[str]
    city: Optional[str]
    description: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    amenities: ParkAmenities
    best_for: List[str] = []

    # Location coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Computed fields (added by API)
    distance_miles: Optional[float] = None
    is_saved: bool = False

    # Community ratings (from mom reviews)
    mom_score: Optional[float] = None  # Weighted mom-centric rating (1-5)
    total_reviews: int = 0  # Number of reviews from moms


class ParkListResponse(BaseModel):
    """List of parks with metadata."""
    parks: List[ParkSchema]
    total_count: int
    filters_applied: Dict[str, Any] = {}


# ============================================================
# FILTER SCHEMAS
# ============================================================

class ParkFilters(BaseModel):
    """Filters for park search."""
    playground: Optional[bool] = None
    dog_friendly: Optional[bool] = None
    restrooms: Optional[bool] = None
    trails: Optional[bool] = None
    water_activities: Optional[bool] = None
    carousel: Optional[bool] = None
    max_distance_miles: Optional[float] = None
    classification: Optional[str] = None  # "Countywide", "District", etc.


# ============================================================
# ANALYTICS SCHEMAS
# ============================================================

class SearchEvent(BaseModel):
    """Log a search event."""
    query: str
    parks_returned: List[str]
    clicked_park: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    filters: Optional[Dict[str, Any]] = None


class PopularParksResponse(BaseModel):
    """Popular parks analytics."""
    parks: List[Dict[str, Any]]
    period: str  # "week", "month", "all_time"


# ============================================================
# REVIEW SCHEMAS (Mom-centric)
# ============================================================

# Predefined tags - curated for mom-relevant insights
PARK_TAGS = [
    # Age-related
    "good-for-toddlers-1-3",
    "good-for-preschool-3-5",
    "good-for-elementary-5-10",
    "good-for-tweens-10-plus",

    # Accessibility & convenience
    "stroller-friendly",
    "wheelchair-accessible",
    "easy-parking",
    "hard-to-find-parking",
    "paved-path-to-playground",
    "wide-parking-for-minivan",
    "close-parking-quick-exit",

    # Containment & Safety (The "Can I See My Kid" Factor)
    "fully-fenced",
    "partially-fenced",
    "open-near-road",
    "excellent-sightlines",
    "has-blind-spots",
    "single-bench-view-all",

    # Surface Types
    "rubber-surface-new",
    "rubber-surface-worn",
    "wood-chip-surface",
    "sand-surface",
    "mulch-surface",

    # Playground features
    "shaded-playground",
    "fenced-playground",
    "benches-near-playground",
    "modern-equipment",
    "dated-equipment",

    # Shade Quality
    "natural-tree-shade",
    "structure-canopy-shade",
    "no-shade-bring-umbrella",

    # Restroom Realities
    "clean-restrooms",
    "restrooms-near-playground",
    "restrooms-far-sprint-required",
    "changing-table-womens",
    "changing-table-mens-too",
    "family-restroom-available",
    "potty-training-friendly",

    # Feeding & Comfort
    "shaded-benches-nursing",
    "picnic-tables-snack-time",
    "water-fountain-available",
    "bring-your-own-water",

    # Noise & Environment
    "usually-quiet",
    "can-get-crowded",
    "under-flight-path",
    "near-highway-noise",
    "peaceful-nature-sounds",
    "sensory-friendly",

    # Practical
    "bring-bug-spray",
    "muddy-when-wet",
    "good-for-picnics",

    # Vibe & atmosphere
    "good-for-birthday-parties",
    "great-for-photos",
    "nature-immersive",

    # Time-specific
    "best-in-morning",
    "best-late-afternoon",
    "avoid-weekends",
    "great-fall-colors",

    # Nearby Conveniences
    "coffee-shop-nearby",
    "restaurant-nearby",
    "ice-cream-nearby",
]


# ============================================================
# MOM-LOGIC DATA POINTS (Structured Observations)
# ============================================================

class ContainmentInfo(BaseModel):
    """The 'Can I See My Kid' factor - safety containment details."""
    fencing_type: Optional[str] = None  # "fully-fenced", "partially-fenced", "open", "open-near-road"
    sightlines: Optional[str] = None  # "excellent", "good", "has-blind-spots", "poor"
    single_vantage_point: Optional[bool] = None  # Can see whole play area from one bench?
    notes: Optional[str] = None  # "Swings visible from slide area bench"


class SurfaceInfo(BaseModel):
    """Playground surface details."""
    surface_type: Optional[str] = None  # "rubber-new", "rubber-worn", "woodchips", "sand", "mulch", "grass"
    condition: Optional[str] = None  # "excellent", "good", "fair", "poor"
    notes: Optional[str] = None  # "Gets muddy after rain"


class LogisticsInfo(BaseModel):
    """The 'Minivan & Stroller' logistics."""
    stroller_path_paved: Optional[bool] = None
    parking_to_playground_distance: Optional[str] = None  # "close", "moderate", "far"
    parking_lot_wide_spots: Optional[bool] = None  # For minivan side doors
    quick_exit_possible: Optional[bool] = None  # For meltdowns
    notes: Optional[str] = None


class RestroomInfo(BaseModel):
    """The 'Biological Realities' - restroom details."""
    distance_from_playground: Optional[str] = None  # "adjacent", "short-walk", "far-sprint-required"
    changing_table_womens: Optional[bool] = None
    changing_table_mens: Optional[bool] = None
    family_restroom: Optional[bool] = None
    cleanliness: Optional[str] = None  # "excellent", "good", "fair", "poor"
    potty_training_friendly: Optional[bool] = None  # Quick access, kid-sized, etc.
    notes: Optional[str] = None


class ShadeInfo(BaseModel):
    """Shade quality details."""
    shade_type: Optional[str] = None  # "natural-trees", "structure-canopy", "mixed", "none"
    playground_shaded: Optional[bool] = None
    seating_shaded: Optional[bool] = None
    best_time_for_shade: Optional[str] = None  # "morning", "afternoon", "all-day"
    notes: Optional[str] = None


class NoiseEnvironmentInfo(BaseModel):
    """Noise and environmental factors."""
    noise_level: Optional[str] = None  # "quiet", "moderate", "noisy"
    near_highway: Optional[bool] = None
    under_flight_path: Optional[bool] = None
    sensory_friendly: Optional[bool] = None  # Good for sensory-sensitive kids
    notes: Optional[str] = None


class NearbyConveniences(BaseModel):
    """Coffee and conveniences nearby."""
    coffee_shop_nearby: Optional[bool] = None
    coffee_shop_name: Optional[str] = None
    restaurant_nearby: Optional[bool] = None
    ice_cream_nearby: Optional[bool] = None
    drive_time_minutes: Optional[int] = None
    notes: Optional[str] = None


class MomLogicObservations(BaseModel):
    """Complete mom-logic observations for a park review."""
    containment: Optional[ContainmentInfo] = None
    surface: Optional[SurfaceInfo] = None
    logistics: Optional[LogisticsInfo] = None
    restrooms: Optional[RestroomInfo] = None
    shade: Optional[ShadeInfo] = None
    noise_environment: Optional[NoiseEnvironmentInfo] = None
    nearby: Optional[NearbyConveniences] = None


class ReviewCreate(BaseModel):
    """Submit a new park review."""
    park_name: str

    # Ratings (1-5 scale, all optional)
    shade_rating: Optional[int] = Field(None, ge=1, le=5)
    seating_rating: Optional[int] = Field(None, ge=1, le=5)
    restroom_cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    restroom_availability_rating: Optional[int] = Field(None, ge=1, le=5)
    playground_quality_rating: Optional[int] = Field(None, ge=1, le=5)
    trail_quality_rating: Optional[int] = Field(None, ge=1, le=5)
    crowdedness_rating: Optional[int] = Field(None, ge=1, le=5)
    safety_rating: Optional[int] = Field(None, ge=1, le=5)
    overall_rating: int = Field(..., ge=1, le=5)

    # Containment/Sightline rating (1-5, how easy to watch your kids)
    containment_rating: Optional[int] = Field(None, ge=1, le=5)

    # Playground age range
    playground_best_age_min: Optional[int] = Field(None, ge=0, le=18)
    playground_best_age_max: Optional[int] = Field(None, ge=0, le=18)

    # Tags (from predefined list)
    tags: List[str] = []

    # Mom-Logic Structured Observations
    mom_observations: Optional[MomLogicObservations] = None

    # Free-form text
    tips: Optional[str] = Field(None, max_length=1000)
    review_text: Optional[str] = Field(None, max_length=2000)

    # Visit context
    visit_date: Optional[datetime] = None
    visit_day_of_week: Optional[str] = None
    visit_time_of_day: Optional[str] = None  # "Morning", "Afternoon", "Evening"

    would_recommend: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "park_name": "Clemyjontri Park",
                "overall_rating": 5,
                "shade_rating": 4,
                "playground_quality_rating": 5,
                "containment_rating": 5,
                "playground_best_age_min": 2,
                "playground_best_age_max": 8,
                "tags": ["good-for-toddlers-1-3", "fully-fenced", "excellent-sightlines", "single-bench-view-all"],
                "mom_observations": {
                    "containment": {
                        "fencing_type": "fully-fenced",
                        "sightlines": "excellent",
                        "single_vantage_point": True,
                        "notes": "Can see swings and slide from the central bench"
                    },
                    "logistics": {
                        "stroller_path_paved": True,
                        "parking_to_playground_distance": "close",
                        "quick_exit_possible": True
                    },
                    "restrooms": {
                        "distance_from_playground": "adjacent",
                        "changing_table_womens": True,
                        "changing_table_mens": True,
                        "potty_training_friendly": True
                    }
                },
                "tips": "Best parking is in the overflow lot. Arrive before 10am on weekends.",
                "visit_time_of_day": "Morning",
                "would_recommend": True
            }
        }


class ReviewResponse(BaseModel):
    """Review response with full details."""
    id: int
    park_name: str
    user_id: int
    user_display_name: Optional[str] = None

    # Ratings
    shade_rating: Optional[int]
    seating_rating: Optional[int]
    restroom_cleanliness_rating: Optional[int]
    restroom_availability_rating: Optional[int]
    playground_quality_rating: Optional[int]
    trail_quality_rating: Optional[int]
    crowdedness_rating: Optional[int]
    safety_rating: Optional[int]
    containment_rating: Optional[int]
    overall_rating: int

    # Age range
    playground_best_age_min: Optional[int]
    playground_best_age_max: Optional[int]

    # Mom-Logic Observations
    mom_observations: Optional[MomLogicObservations] = None

    # Text
    tags: List[str]
    tips: Optional[str]
    review_text: Optional[str]

    # Context
    visit_date: Optional[datetime]
    visit_day_of_week: Optional[str]
    visit_time_of_day: Optional[str]
    would_recommend: bool

    # Meta
    created_at: datetime
    helpful_count: int = 0

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """List of reviews for a park."""
    park_name: str
    reviews: List[ReviewResponse]
    total_count: int
    average_overall: Optional[float] = None
    mom_score: Optional[float] = None
    top_tags: List[str] = []
    mom_insights: Optional["ParkMomInsights"] = None


class ParkMomInsights(BaseModel):
    """
    Aggregated mom-sourced insights for a park.
    This is what makes our data valuable beyond government sources.
    Used by the RAG system to provide nuanced recommendations.
    """
    park_name: str

    # Containment & Safety Summary
    fencing_consensus: Optional[str] = None  # Most reported fencing type
    sightlines_rating: Optional[str] = None  # "excellent", "good", "has-blind-spots"
    single_vantage_possible: Optional[bool] = None
    containment_notes: List[str] = []  # Collected tips like "swings visible from slide bench"

    # Surface Summary
    surface_type: Optional[str] = None
    surface_condition: Optional[str] = None

    # Logistics Summary
    stroller_friendly: Optional[bool] = None
    parking_distance: Optional[str] = None  # Consensus
    quick_exit_friendly: Optional[bool] = None
    logistics_notes: List[str] = []

    # Restroom Summary
    restroom_distance: Optional[str] = None
    has_changing_tables: Optional[bool] = None
    mens_changing_table: Optional[bool] = None  # Important for dads!
    family_restroom: Optional[bool] = None
    potty_training_friendly: Optional[bool] = None
    restroom_notes: List[str] = []

    # Shade Summary
    shade_type: Optional[str] = None
    playground_shaded: Optional[bool] = None
    seating_shaded: Optional[bool] = None
    best_time_for_shade: Optional[str] = None

    # Environment Summary
    noise_level: Optional[str] = None
    sensory_friendly: Optional[bool] = None
    environment_notes: List[str] = []

    # Nearby Conveniences
    coffee_nearby: Optional[bool] = None
    coffee_shop_names: List[str] = []

    # Overall Insights
    best_for_ages: Optional[str] = None  # e.g., "2-5 years"
    top_mom_tags: List[str] = []
    mom_tips: List[str] = []  # Top tips from reviews
    total_mom_reviews: int = 0

    # RAG-friendly summary
    rag_summary: Optional[str] = None  # Pre-generated summary for RAG context


class ParkTagsResponse(BaseModel):
    """Available tags for reviews."""
    tags: List[str]
    categories: Dict[str, List[str]]


class MarkReviewHelpfulRequest(BaseModel):
    """Mark a review as helpful."""
    review_id: int


# ============================================================
# WEATHER SCHEMAS
# ============================================================

class WeatherConditionEnum(str, Enum):
    """Weather condition categories."""
    SUNNY = "sunny"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    SNOWY = "snowy"
    FOGGY = "foggy"


class WeatherResponse(BaseModel):
    """Current weather data with mom-friendly recommendations."""
    temperature_f: float
    feels_like_f: float
    humidity: int
    precipitation_probability: int
    condition: str
    uv_index: float
    wind_speed_mph: float
    is_daytime: bool

    # Mom-friendly recommendations
    mom_tip: str
    suggested_activities: List[str]
    things_to_avoid: List[str]
    suggested_queries: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "temperature_f": 85.0,
                "feels_like_f": 88.0,
                "humidity": 65,
                "precipitation_probability": 10,
                "condition": "sunny",
                "uv_index": 7.0,
                "wind_speed_mph": 5.0,
                "is_daytime": True,
                "mom_tip": "Warm day - bring water and sunscreen!",
                "suggested_activities": ["splash pads", "shaded areas", "morning visits"],
                "things_to_avoid": ["midday playground visits"],
                "suggested_queries": ["Shaded playgrounds nearby", "Parks with water features"]
            }
        }
