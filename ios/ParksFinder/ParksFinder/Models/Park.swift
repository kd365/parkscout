import Foundation
import CoreLocation

// MARK: - Park Model
struct Park: Identifiable, Codable, Equatable {
    var id: String { parkName }  // Use parkName as the unique ID
    let parkName: String
    let classification: String?
    let address: String?
    let city: String?
    let description: String?
    let website: String?
    let phone: String?
    let amenities: ParkAmenities
    let bestFor: [String]?

    // Location coordinates from API
    let latitude: Double?
    let longitude: Double?

    var distanceMiles: Double?
    var driveTimeMinutes: Int?
    var distanceCategory: DistanceCategory?
    var isSaved: Bool = false

    // Rating data (from aggregate reviews)
    var momScore: Double?
    var totalReviews: Int?

    // Computed property for coordinate
    var coordinate: CLLocationCoordinate2D? {
        guard let lat = latitude, let lng = longitude else { return nil }
        return CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }

    enum CodingKeys: String, CodingKey {
        case parkName = "park_name"
        case classification, address, city, description, website, phone
        case amenities
        case bestFor = "best_for"
        case latitude, longitude
        case distanceMiles = "distance_miles"
        case driveTimeMinutes = "drive_time_minutes"
        case distanceCategory = "distance_category"
        case isSaved = "is_saved"
        case momScore = "mom_score"
        case totalReviews = "total_reviews"
    }

    static func == (lhs: Park, rhs: Park) -> Bool {
        lhs.parkName == rhs.parkName
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        parkName = try container.decode(String.self, forKey: .parkName)
        classification = try container.decodeIfPresent(String.self, forKey: .classification)
        address = try container.decodeIfPresent(String.self, forKey: .address)
        city = try container.decodeIfPresent(String.self, forKey: .city)
        description = try container.decodeIfPresent(String.self, forKey: .description)
        website = try container.decodeIfPresent(String.self, forKey: .website)
        phone = try container.decodeIfPresent(String.self, forKey: .phone)
        amenities = try container.decode(ParkAmenities.self, forKey: .amenities)
        bestFor = try container.decodeIfPresent([String].self, forKey: .bestFor)
        latitude = try container.decodeIfPresent(Double.self, forKey: .latitude)
        longitude = try container.decodeIfPresent(Double.self, forKey: .longitude)
        distanceMiles = try container.decodeIfPresent(Double.self, forKey: .distanceMiles)
        driveTimeMinutes = try container.decodeIfPresent(Int.self, forKey: .driveTimeMinutes)
        distanceCategory = try container.decodeIfPresent(DistanceCategory.self, forKey: .distanceCategory)
        isSaved = try container.decodeIfPresent(Bool.self, forKey: .isSaved) ?? false
        momScore = try container.decodeIfPresent(Double.self, forKey: .momScore)
        totalReviews = try container.decodeIfPresent(Int.self, forKey: .totalReviews)
    }
}

// MARK: - Amenities
struct ParkAmenities: Codable {
    let playground: String
    let restrooms: String
    let picnicShelters: String
    let trails: String
    let parking: String
    let waterActivities: String
    let specialFeatures: [String]
    let dogFriendly: String

    enum CodingKeys: String, CodingKey {
        case playground, restrooms, trails, parking
        case picnicShelters = "picnic_shelters"
        case waterActivities = "water_activities"
        case specialFeatures = "special_features"
        case dogFriendly = "dog_friendly"
    }

    var hasPlayground: Bool { playground != "No" }
    var hasRestrooms: Bool { restrooms != "No" }
    var hasTrails: Bool { trails != "None" }
    var isDogFriendly: Bool { dogFriendly.contains("Yes") }
}

// MARK: - Distance Category
enum DistanceCategory: String, Codable {
    case near
    case moderate
    case driveable

    var label: String {
        switch self {
        case .near: return "Near you"
        case .moderate: return "Moderately close"
        case .driveable: return "Driveable"
        }
    }

    var emoji: String {
        switch self {
        case .near: return "📍"
        case .moderate: return "🚗"
        case .driveable: return "🛣️"
        }
    }

    var color: String {
        switch self {
        case .near: return "green"
        case .moderate: return "orange"
        case .driveable: return "gray"
        }
    }
}

// MARK: - Query Response
struct QueryResponse: Codable {
    let answer: String
    let sessionId: String
    let parksMentioned: [ParkMention]
    let responseTimeSeconds: Double
    let conversationTurn: Int

    enum CodingKeys: String, CodingKey {
        case answer
        case sessionId = "session_id"
        case parksMentioned = "parks_mentioned"
        case responseTimeSeconds = "response_time_seconds"
        case conversationTurn = "conversation_turn"
    }
}

struct ParkMention: Codable, Identifiable {
    var id: String { name }
    let name: String
    let relevanceScore: Double?
    let distanceMiles: Double?

    enum CodingKeys: String, CodingKey {
        case name
        case relevanceScore = "relevance_score"
        case distanceMiles = "distance_miles"
    }
}

// MARK: - User
struct User: Codable, Identifiable {
    let id: Int
    let displayName: String?
    let email: String?
    let createdAt: Date
    let preferences: UserPreferences?

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case email
        case createdAt = "created_at"
        case preferences
    }
}

struct UserPreferences: Codable {
    var homeLocation: Location?
    var childrenAges: [Int]
    var hasDog: Bool
    var accessibilityNeeds: Bool
    var preferredDistanceMiles: Double
    var notificationsEnabled: Bool

    enum CodingKeys: String, CodingKey {
        case homeLocation = "home_location"
        case childrenAges = "children_ages"
        case hasDog = "has_dog"
        case accessibilityNeeds = "accessibility_needs"
        case preferredDistanceMiles = "preferred_distance_miles"
        case notificationsEnabled = "notifications_enabled"
    }

    init() {
        self.homeLocation = nil
        self.childrenAges = []
        self.hasDog = false
        self.accessibilityNeeds = false
        self.preferredDistanceMiles = 15.0
        self.notificationsEnabled = true
    }
}

struct Location: Codable {
    let lat: Double
    let lng: Double

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }
}

// MARK: - Park Review (Mom-centric)
struct ParkReview: Codable, Identifiable {
    let id: Int
    let parkName: String
    let userId: Int
    let shadeRating: Int?
    let seatingRating: Int?
    let restroomCleanlinessRating: Int?
    let restroomAvailabilityRating: Int?
    let playgroundQualityRating: Int?
    let playgroundBestAgeMin: Int?
    let playgroundBestAgeMax: Int?
    let trailQualityRating: Int?
    let crowdednessRating: Int?
    let safetyRating: Int?
    let overallRating: Int
    let tips: String?
    let tags: [String]
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case parkName = "park_name"
        case userId = "user_id"
        case shadeRating = "shade_rating"
        case seatingRating = "seating_rating"
        case restroomCleanlinessRating = "restroom_cleanliness_rating"
        case restroomAvailabilityRating = "restroom_availability_rating"
        case playgroundQualityRating = "playground_quality_rating"
        case playgroundBestAgeMin = "playground_best_age_min"
        case playgroundBestAgeMax = "playground_best_age_max"
        case trailQualityRating = "trail_quality_rating"
        case crowdednessRating = "crowdedness_rating"
        case safetyRating = "safety_rating"
        case overallRating = "overall_rating"
        case tips
        case tags
        case createdAt = "created_at"
    }
}

// MARK: - Aggregate Rating
struct ParkAggregateRating: Codable {
    let parkName: String
    let momScore: Double
    let totalReviews: Int
    let avgShade: Double?
    let avgSeating: Double?
    let avgRestroomCleanliness: Double?
    let avgPlaygroundQuality: Double?
    let avgTrailQuality: Double?
    let avgSafety: Double?
    let popularTags: [String]

    enum CodingKeys: String, CodingKey {
        case parkName = "park_name"
        case momScore = "mom_score"
        case totalReviews = "total_reviews"
        case avgShade = "avg_shade"
        case avgSeating = "avg_seating"
        case avgRestroomCleanliness = "avg_restroom_cleanliness"
        case avgPlaygroundQuality = "avg_playground_quality"
        case avgTrailQuality = "avg_trail_quality"
        case avgSafety = "avg_safety"
        case popularTags = "popular_tags"
    }
}
