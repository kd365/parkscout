"""
Seed synthetic reviews and badge confirmations for demo purposes.

Creates 10 synthetic users with diverse demographics and generates
realistic reviews for Clemyjontri Park, Burke Lake Park, and Frying Pan Farm Park.
Reviews are designed so that parks earn badges when enough parents confirm
the same quality (threshold: 3 confirmations).

Usage:
    cd lab3-ai-engine
    python scripts/seed_reviews.py
"""
import os
import sys
import hashlib
import secrets
from datetime import datetime, timedelta
import random

# Add parent dir to path so we can import api modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.models import (
    init_db, get_session, User, ParkReview, ParkBadge,
    BadgeConfirmation, ParkAggregateRating, SavedPark, BADGE_DEFINITIONS
)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "parks_finder.db")

# ============================================================
# SYNTHETIC USERS — 10 parents with diverse demographics
# ============================================================

USERS = [
    {"display_name": "Sarah M.", "email": "sarah.m@demo.parkscout.app"},
    {"display_name": "Marcus J.", "email": "marcus.j@demo.parkscout.app"},
    {"display_name": "Priya K.", "email": "priya.k@demo.parkscout.app"},
    {"display_name": "Carlos R.", "email": "carlos.r@demo.parkscout.app"},
    {"display_name": "Emily W.", "email": "emily.w@demo.parkscout.app"},
    {"display_name": "David L.", "email": "david.l@demo.parkscout.app"},
    {"display_name": "Aisha T.", "email": "aisha.t@demo.parkscout.app"},
    {"display_name": "Jason P.", "email": "jason.p@demo.parkscout.app"},
    {"display_name": "Lin C.", "email": "lin.c@demo.parkscout.app"},
    {"display_name": "Rachel S.", "email": "rachel.s@demo.parkscout.app"},
]

# ============================================================
# REVIEW DATA — realistic reviews for 3 parks
# ============================================================

# Each review dict maps to ParkReview columns.
# Badge confirmations are derived from the ratings.

CLEMYJONTRI_REVIEWS = [
    # Clemyjontri is known for: inclusive playground, fenced, great shade, clean restrooms
    # Should earn: The Fortress, Solar Shield, Golden Throne, Tiny Explorer, Smooth Sailing
    {
        "user_idx": 0, "overall_rating": 5, "shade_rating": 5, "seating_rating": 5,
        "restroom_cleanliness_rating": 5, "restroom_availability_rating": 5,
        "playground_quality_rating": 5, "trail_quality_rating": 5,
        "crowdedness_rating": 3, "safety_rating": 5, "containment_rating": 5,
        "playground_best_age_min": 1, "playground_best_age_max": 8,
        "review_text": "Absolutely the best park in Fairfax County for young kids. The inclusive playground is incredible — my daughter with sensory needs loves the carousel and the textured panels. Everything is fully fenced and I can see the entire play area from one bench.",
        "tips": "Arrive before 10am on weekends for parking. The overflow lot fills fast.",
        "tags": ["fully-fenced", "excellent-sightlines", "single-bench-view-all", "good-for-toddlers-1-3", "stroller-friendly", "clean-restrooms", "shaded-playground"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Saturday",
        "would_recommend": True,
        "badges": ["the_fortress", "solar_shield", "golden_throne", "tiny_explorer", "smooth_sailing"],
    },
    {
        "user_idx": 1, "overall_rating": 5, "shade_rating": 4, "seating_rating": 4,
        "restroom_cleanliness_rating": 4, "restroom_availability_rating": 5,
        "playground_quality_rating": 5, "trail_quality_rating": 4,
        "crowdedness_rating": 2, "safety_rating": 5, "containment_rating": 5,
        "playground_best_age_min": 2, "playground_best_age_max": 7,
        "review_text": "As a dad, I appreciate that this park has changing tables in BOTH restrooms. The fenced playground means I can relax while my twins run around. Great sightlines everywhere.",
        "tips": "Bring sunscreen for the carousel area — less shade there. The spray ground is seasonal.",
        "tags": ["fully-fenced", "excellent-sightlines", "changing-table-mens-too", "good-for-toddlers-1-3", "stroller-friendly", "clean-restrooms"],
        "visit_time_of_day": "Afternoon", "visit_day_of_week": "Sunday",
        "would_recommend": True,
        "badges": ["the_fortress", "solar_shield", "golden_throne", "tiny_explorer", "smooth_sailing"],
    },
    {
        "user_idx": 2, "overall_rating": 5, "shade_rating": 5, "seating_rating": 5,
        "restroom_cleanliness_rating": 5, "restroom_availability_rating": 5,
        "playground_quality_rating": 5, "trail_quality_rating": 5,
        "crowdedness_rating": 3, "safety_rating": 5, "containment_rating": 5,
        "playground_best_age_min": 1, "playground_best_age_max": 6,
        "review_text": "My 18-month-old loves the toddler section. The rubber surface is pristine and the whole area is enclosed. Paved paths everywhere — my double stroller glides. Restrooms are spotless with a family restroom option.",
        "tips": "The sensory garden is a hidden gem. Pack snacks — no food vendors on site.",
        "tags": ["fully-fenced", "rubber-surface-new", "good-for-toddlers-1-3", "stroller-friendly", "clean-restrooms", "shaded-playground", "sensory-friendly"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Wednesday",
        "would_recommend": True,
        "badges": ["the_fortress", "solar_shield", "golden_throne", "tiny_explorer", "smooth_sailing"],
    },
    {
        "user_idx": 3, "overall_rating": 4, "shade_rating": 4, "seating_rating": 4,
        "restroom_cleanliness_rating": 4, "restroom_availability_rating": 4,
        "playground_quality_rating": 5, "trail_quality_rating": 4,
        "crowdedness_rating": 2, "safety_rating": 5, "containment_rating": 5,
        "playground_best_age_min": 2, "playground_best_age_max": 10,
        "review_text": "We drive 30 minutes to come here because no other park compares for accessibility. My son uses a wheelchair and he can access every single piece of equipment. The carousel has wheelchair spots.",
        "tips": "Weekday mornings are quiet. The ADA parking spots fill up fast on weekends.",
        "tags": ["fully-fenced", "wheelchair-accessible", "good-for-toddlers-1-3", "stroller-friendly", "modern-equipment"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Tuesday",
        "would_recommend": True,
        "badges": ["the_fortress", "tiny_explorer", "smooth_sailing"],
    },
    {
        "user_idx": 4, "overall_rating": 4, "shade_rating": 4, "seating_rating": 3,
        "restroom_cleanliness_rating": 4, "restroom_availability_rating": 4,
        "playground_quality_rating": 5, "trail_quality_rating": 4,
        "crowdedness_rating": 2, "safety_rating": 5, "containment_rating": 5,
        "playground_best_age_min": 1, "playground_best_age_max": 8,
        "review_text": "Great park but it gets PACKED on weekends. Come during the week if you can. The playground equipment is top notch and the fencing gives total peace of mind.",
        "tips": "Tuesday/Wednesday mornings are the sweet spot. Plenty of shade by the big trees.",
        "tags": ["fully-fenced", "can-get-crowded", "good-for-toddlers-1-3", "modern-equipment", "natural-tree-shade"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Tuesday",
        "would_recommend": True,
        "badges": ["the_fortress", "solar_shield", "tiny_explorer"],
    },
]

BURKE_LAKE_REVIEWS = [
    # Burke Lake is known for: train, carousel, fishing, trails, dog-friendly
    # Should earn: Paws Welcome, Feast Grounds, Splash Zone
    {
        "user_idx": 5, "overall_rating": 5, "shade_rating": 4, "seating_rating": 4,
        "restroom_cleanliness_rating": 3, "restroom_availability_rating": 4,
        "playground_quality_rating": 4, "trail_quality_rating": 5,
        "crowdedness_rating": 3, "safety_rating": 4, "containment_rating": 3,
        "playground_best_age_min": 3, "playground_best_age_max": 12,
        "review_text": "Burke Lake is our every-weekend park. The miniature train is a hit with both kids. Dog area is great — our golden retriever goes nuts. The trails along the lake are beautiful and well-maintained.",
        "tips": "The ice cream shop closes at 4pm. Bring fishing gear — the pier is free.",
        "tags": ["good-for-preschool-3-5", "good-for-elementary-5-10", "nature-immersive", "good-for-picnics", "easy-parking"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Saturday",
        "would_recommend": True,
        "badges": ["paws_welcome", "feast_grounds"],
    },
    {
        "user_idx": 6, "overall_rating": 4, "shade_rating": 3, "seating_rating": 3,
        "restroom_cleanliness_rating": 3, "restroom_availability_rating": 3,
        "playground_quality_rating": 3, "trail_quality_rating": 4,
        "crowdedness_rating": 2, "safety_rating": 4, "containment_rating": 2,
        "playground_best_age_min": 4, "playground_best_age_max": 12,
        "review_text": "Fantastic for older kids but not ideal for toddlers — the playground isn't fenced and it's near the parking lot. Great picnic shelters though, we hosted a birthday party here. Dog area is spacious.",
        "tips": "Reserve picnic shelters online — they book up fast in spring/summer.",
        "tags": ["good-for-elementary-5-10", "good-for-birthday-parties", "good-for-picnics", "has-blind-spots", "open-near-road"],
        "visit_time_of_day": "Afternoon", "visit_day_of_week": "Saturday",
        "would_recommend": True,
        "badges": ["paws_welcome", "feast_grounds"],
    },
    {
        "user_idx": 7, "overall_rating": 5, "shade_rating": 4, "seating_rating": 4,
        "restroom_cleanliness_rating": 3, "restroom_availability_rating": 4,
        "playground_quality_rating": 4, "trail_quality_rating": 5,
        "crowdedness_rating": 3, "safety_rating": 4, "containment_rating": 3,
        "playground_best_age_min": 3, "playground_best_age_max": 10,
        "review_text": "My kids love the carousel and train ride. The 5-mile trail around the lake is perfect for family bikes. We bring our dog every time — the off-leash area by the lake is huge. Multiple picnic areas with grills.",
        "tips": "Bring quarters for the train ride. The boat rental is fun for older kids.",
        "tags": ["good-for-preschool-3-5", "nature-immersive", "good-for-picnics", "easy-parking"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Sunday",
        "would_recommend": True,
        "badges": ["paws_welcome", "feast_grounds"],
    },
    {
        "user_idx": 8, "overall_rating": 4, "shade_rating": 3, "seating_rating": 3,
        "restroom_cleanliness_rating": 2, "restroom_availability_rating": 3,
        "playground_quality_rating": 3, "trail_quality_rating": 4,
        "crowdedness_rating": 2, "safety_rating": 4, "containment_rating": 3,
        "playground_best_age_min": 5, "playground_best_age_max": 12,
        "review_text": "Great park for a full day out. The disc golf course is fun for older kids. Fishing pier is peaceful. Restrooms could be cleaner — the ones by the marina are the best bet.",
        "tips": "Bring bug spray in summer. The west parking lot is closest to the playground.",
        "tags": ["good-for-elementary-5-10", "bring-bug-spray", "nature-immersive"],
        "visit_time_of_day": "Afternoon", "visit_day_of_week": "Friday",
        "would_recommend": True,
        "badges": ["feast_grounds"],
    },
    {
        "user_idx": 9, "overall_rating": 4, "shade_rating": 4, "seating_rating": 3,
        "restroom_cleanliness_rating": 3, "restroom_availability_rating": 4,
        "playground_quality_rating": 4, "trail_quality_rating": 5,
        "crowdedness_rating": 3, "safety_rating": 4, "containment_rating": 3,
        "playground_best_age_min": 4, "playground_best_age_max": 14,
        "review_text": "We come here mostly for the trails and fishing. My tween loves the disc golf. Playground is decent but not the main draw. The lake views from the trail are gorgeous in fall.",
        "tips": "Fall colors in October are incredible. The south trail is less crowded.",
        "tags": ["good-for-tweens-10-plus", "nature-immersive", "great-fall-colors"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Saturday",
        "would_recommend": True,
        "badges": [],
    },
]

FRYING_PAN_REVIEWS = [
    # Frying Pan Farm is known for: farm animals, carousel, toddler-friendly, educational
    # Should earn: Tiny Explorer, Feast Grounds, Golden Throne
    {
        "user_idx": 0, "overall_rating": 5, "shade_rating": 3, "seating_rating": 4,
        "restroom_cleanliness_rating": 5, "restroom_availability_rating": 5,
        "playground_quality_rating": 4, "trail_quality_rating": 3,
        "crowdedness_rating": 3, "safety_rating": 5, "containment_rating": 4,
        "playground_best_age_min": 1, "playground_best_age_max": 6,
        "review_text": "My toddler is OBSESSED with the animals. The goats, chickens, horses — she wants to visit every weekend. The playground is nice for little ones and the restrooms in the visitor center are spotless.",
        "tips": "The country store has great apple cider in fall. Pony rides on weekends!",
        "tags": ["good-for-toddlers-1-3", "good-for-preschool-3-5", "clean-restrooms", "good-for-picnics", "great-for-photos"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Saturday",
        "would_recommend": True,
        "badges": ["tiny_explorer", "feast_grounds", "golden_throne"],
    },
    {
        "user_idx": 2, "overall_rating": 5, "shade_rating": 3, "seating_rating": 4,
        "restroom_cleanliness_rating": 4, "restroom_availability_rating": 5,
        "playground_quality_rating": 4, "trail_quality_rating": 3,
        "crowdedness_rating": 2, "safety_rating": 5, "containment_rating": 4,
        "playground_best_age_min": 1, "playground_best_age_max": 5,
        "review_text": "Perfect for toddler birthday parties! We rented the picnic shelter and the kids spent the whole time with the animals. Carousel is gentle enough for 2-year-olds. Restrooms are well-maintained.",
        "tips": "Book the picnic shelter early for birthday parties. Bring hand wipes for after the animals.",
        "tags": ["good-for-toddlers-1-3", "good-for-birthday-parties", "clean-restrooms", "good-for-picnics"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Sunday",
        "would_recommend": True,
        "badges": ["tiny_explorer", "feast_grounds", "golden_throne"],
    },
    {
        "user_idx": 4, "overall_rating": 4, "shade_rating": 2, "seating_rating": 3,
        "restroom_cleanliness_rating": 4, "restroom_availability_rating": 4,
        "playground_quality_rating": 3, "trail_quality_rating": 2,
        "crowdedness_rating": 2, "safety_rating": 4, "containment_rating": 4,
        "playground_best_age_min": 1, "playground_best_age_max": 5,
        "review_text": "My 2-year-old loves the farm animals. Not much shade though — we struggle on hot days. The indoor areas of the barn help. Great educational experience for little ones learning animal sounds!",
        "tips": "Come in spring for baby animals. Not great on hot days — no shade near the animals.",
        "tags": ["good-for-toddlers-1-3", "no-shade-bring-umbrella", "clean-restrooms"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Thursday",
        "would_recommend": True,
        "badges": ["tiny_explorer", "golden_throne"],
    },
    {
        "user_idx": 6, "overall_rating": 4, "shade_rating": 3, "seating_rating": 3,
        "restroom_cleanliness_rating": 4, "restroom_availability_rating": 4,
        "playground_quality_rating": 3, "trail_quality_rating": 3,
        "crowdedness_rating": 3, "safety_rating": 4, "containment_rating": 3,
        "playground_best_age_min": 2, "playground_best_age_max": 7,
        "review_text": "Great for a 2-hour visit. The seasonal events (pumpkin patch, holiday lights) are the best. Picnic area near the playground is convenient. Country store has fun souvenirs.",
        "tips": "The Halloween event sells out — buy tickets early online.",
        "tags": ["good-for-toddlers-1-3", "good-for-preschool-3-5", "good-for-picnics"],
        "visit_time_of_day": "Afternoon", "visit_day_of_week": "Saturday",
        "would_recommend": True,
        "badges": ["tiny_explorer", "feast_grounds"],
    },
    {
        "user_idx": 8, "overall_rating": 4, "shade_rating": 3, "seating_rating": 4,
        "restroom_cleanliness_rating": 5, "restroom_availability_rating": 5,
        "playground_quality_rating": 4, "trail_quality_rating": 3,
        "crowdedness_rating": 3, "safety_rating": 5, "containment_rating": 4,
        "playground_best_age_min": 1, "playground_best_age_max": 6,
        "review_text": "We bring our toddler here every other week. She feeds the goats and rides the carousel. Restrooms in the main building are always clean. Playground is basic but fine for little ones.",
        "tips": "Free admission! Just pay for carousel rides and pony rides.",
        "tags": ["good-for-toddlers-1-3", "clean-restrooms", "easy-parking"],
        "visit_time_of_day": "Morning", "visit_day_of_week": "Wednesday",
        "would_recommend": True,
        "badges": ["tiny_explorer", "golden_throne"],
    },
]

PARK_REVIEWS = {
    "Clemyjontri": CLEMYJONTRI_REVIEWS,
    "Burke Lake": BURKE_LAKE_REVIEWS,
    "Frying Pan Farm": FRYING_PAN_REVIEWS,
}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def seed_database():
    engine = init_db(f"sqlite:///{DB_PATH}")
    session = get_session(engine)

    print("Seeding ParkScout demo data...")
    print(f"Database: {DB_PATH}\n")

    # Check for existing demo data
    existing = session.query(User).filter(User.email.like("%@demo.parkscout.app")).first()
    if existing:
        print("Demo data already exists. Clearing and re-seeding...")
        session.query(BadgeConfirmation).filter(
            BadgeConfirmation.user_id.in_(
                session.query(User.id).filter(User.email.like("%@demo.parkscout.app"))
            )
        ).delete(synchronize_session=False)
        session.query(ParkReview).filter(
            ParkReview.user_id.in_(
                session.query(User.id).filter(User.email.like("%@demo.parkscout.app"))
            )
        ).delete(synchronize_session=False)
        session.query(User).filter(User.email.like("%@demo.parkscout.app")).delete(synchronize_session=False)
        session.query(ParkBadge).delete(synchronize_session=False)
        session.query(ParkAggregateRating).delete(synchronize_session=False)
        session.commit()

    # 1. Create users
    print("Creating 10 synthetic users...")
    user_objects = []
    for i, u in enumerate(USERS):
        user = User(
            email=u["email"],
            display_name=u["display_name"],
            password_hash=hash_password("demo123"),
            created_at=datetime.utcnow() - timedelta(days=random.randint(30, 180)),
        )
        session.add(user)
        session.flush()  # Get the ID
        user_objects.append(user)
        print(f"  Created user: {u['display_name']} (id={user.id})")

    # 2. Create reviews and track badge confirmations
    badge_counts = {}  # {(park_name, badge_id): count}
    total_reviews = 0

    for park_name, reviews in PARK_REVIEWS.items():
        print(f"\nSeeding reviews for {park_name}...")
        for rev in reviews:
            user = user_objects[rev["user_idx"]]
            days_ago = random.randint(1, 90)
            review = ParkReview(
                user_id=user.id,
                park_name=park_name,
                created_at=datetime.utcnow() - timedelta(days=days_ago),
                visit_date=datetime.utcnow() - timedelta(days=days_ago + random.randint(0, 3)),
                overall_rating=rev["overall_rating"],
                shade_rating=rev.get("shade_rating"),
                seating_rating=rev.get("seating_rating"),
                restroom_cleanliness_rating=rev.get("restroom_cleanliness_rating"),
                restroom_availability_rating=rev.get("restroom_availability_rating"),
                playground_quality_rating=rev.get("playground_quality_rating"),
                trail_quality_rating=rev.get("trail_quality_rating"),
                crowdedness_rating=rev.get("crowdedness_rating"),
                safety_rating=rev.get("safety_rating"),
                containment_rating=rev.get("containment_rating"),
                playground_best_age_min=rev.get("playground_best_age_min"),
                playground_best_age_max=rev.get("playground_best_age_max"),
                review_text=rev.get("review_text"),
                tips=rev.get("tips"),
                tags=rev.get("tags", []),
                visit_time_of_day=rev.get("visit_time_of_day"),
                visit_day_of_week=rev.get("visit_day_of_week"),
                would_recommend=rev.get("would_recommend", True),
                helpful_count=random.randint(0, 12),
            )
            session.add(review)
            session.flush()
            total_reviews += 1

            # Badge confirmations
            for badge_id in rev.get("badges", []):
                confirmation = BadgeConfirmation(
                    user_id=user.id,
                    park_name=park_name,
                    badge_id=badge_id,
                    confirmed_at=review.created_at,
                    review_id=review.id,
                    is_negative=False,
                )
                session.add(confirmation)
                key = (park_name, badge_id)
                badge_counts[key] = badge_counts.get(key, 0) + 1

            print(f"  Review by {user.display_name}: {rev['overall_rating']}/5 — {len(rev.get('badges', []))} badge confirmations")

    # 3. Create park badges based on confirmation counts
    print(f"\nProcessing badge confirmations...")
    earned_badges = 0
    for (park_name, badge_id), count in badge_counts.items():
        badge_def = BADGE_DEFINITIONS.get(badge_id)
        if not badge_def:
            continue
        threshold = badge_def["threshold"]
        is_earned = count >= threshold
        badge = ParkBadge(
            park_name=park_name,
            badge_id=badge_id,
            confirmation_count=count,
            is_earned=is_earned,
            earned_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)) if is_earned else None,
            status="earned" if is_earned else "earned",
            negative_count=0,
        )
        session.add(badge)
        status = "EARNED" if is_earned else f"pending ({count}/{threshold})"
        print(f"  {park_name} — {badge_def['name']}: {status}")
        if is_earned:
            earned_badges += 1

    # 4. Create aggregate ratings
    print(f"\nComputing aggregate ratings...")
    for park_name, reviews in PARK_REVIEWS.items():
        n = len(reviews)
        avg = lambda field: sum(r.get(field, 0) or 0 for r in reviews) / n

        # Weighted parent score: restrooms=20%, playground=20%, containment=20%, shade=15%, safety=15%, trails=10%
        parent_score = (
            avg("restroom_cleanliness_rating") * 0.20 +
            avg("playground_quality_rating") * 0.20 +
            avg("containment_rating") * 0.20 +
            avg("shade_rating") * 0.15 +
            avg("safety_rating") * 0.15 +
            avg("trail_quality_rating") * 0.10
        )

        agg = ParkAggregateRating(
            park_name=park_name,
            total_reviews=n,
            avg_shade=round(avg("shade_rating"), 1),
            avg_seating=round(avg("seating_rating"), 1),
            avg_restroom_cleanliness=round(avg("restroom_cleanliness_rating"), 1),
            avg_restroom_availability=round(avg("restroom_availability_rating"), 1),
            avg_playground_quality=round(avg("playground_quality_rating"), 1),
            avg_trail_quality=round(avg("trail_quality_rating"), 1),
            avg_crowdedness=round(avg("crowdedness_rating"), 1),
            avg_safety=round(avg("safety_rating"), 1),
            avg_containment=round(avg("containment_rating"), 1),
            avg_overall=round(avg("overall_rating"), 1),
            mom_score=round(parent_score, 2),
            recommend_percentage=round(sum(1 for r in reviews if r.get("would_recommend", True)) / n * 100, 0),
        )
        session.add(agg)
        print(f"  {park_name}: Parent Score {parent_score:.2f}/5, {n} reviews, {agg.recommend_percentage}% recommend")

    # 5. Seed saved parks for demo user (user_id=1 used by iOS app)
    print(f"\nSeeding saved parks for demo profile...")
    # Clear existing saved parks for user 1
    session.query(SavedPark).filter(SavedPark.user_id == 1).delete(synchronize_session=False)
    # Also clear for first demo user
    first_user_id = user_objects[0].id
    session.query(SavedPark).filter(SavedPark.user_id == first_user_id).delete(synchronize_session=False)

    saved_parks_data = [
        {"park_name": "Clemyjontri", "notes": "Best inclusive playground in the county!", "tags": ["toddler-friendly", "fenced", "accessible"], "visit_count": 8},
        {"park_name": "Burke Lake", "notes": "Great for weekend family outings. Kids love the train!", "tags": ["train-ride", "fishing", "trails"], "visit_count": 5},
        {"park_name": "Frying Pan Farm", "notes": "Toddler's favorite — farm animals!", "tags": ["farm-animals", "carousel", "free-admission"], "visit_count": 6},
        {"park_name": "Lake Fairfax", "notes": "Water Mine in summer is a must", "tags": ["water-park", "camping", "trails"], "visit_count": 3},
    ]
    for target_uid in [1, first_user_id]:
        for sp in saved_parks_data:
            saved = SavedPark(
                user_id=target_uid,
                park_name=sp["park_name"],
                notes=sp["notes"],
                tags=sp["tags"],
                visit_count=sp["visit_count"],
                saved_at=datetime.utcnow() - timedelta(days=random.randint(10, 60)),
                last_visited=datetime.utcnow() - timedelta(days=random.randint(1, 14)),
            )
            session.add(saved)
        print(f"  Saved {len(saved_parks_data)} parks for user_id={target_uid}")

    session.commit()

    # Summary
    print(f"\n{'='*50}")
    print(f"SEED COMPLETE")
    print(f"{'='*50}")
    print(f"  Users created:    {len(USERS)}")
    print(f"  Reviews created:  {total_reviews}")
    print(f"  Badges earned:    {earned_badges}")
    print(f"  Parks with data:  {len(PARK_REVIEWS)}")
    print()
    print("Badge summary:")
    for (park_name, badge_id), count in sorted(badge_counts.items()):
        badge_def = BADGE_DEFINITIONS.get(badge_id, {})
        threshold = badge_def.get("threshold", 3)
        icon = "✅" if count >= threshold else "⏳"
        print(f"  {icon} {park_name} — {badge_def.get('name', badge_id)}: {count}/{threshold}")

    session.close()


if __name__ == "__main__":
    seed_database()
