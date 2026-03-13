import Foundation
import CoreLocation

// MARK: - API Service
class APIService: ObservableObject {
    static let shared = APIService()

    /// The base URL for API requests.
    /// Uses centralized AppConfig for easy environment switching.
    /// See Configuration.swift for details on how to override for CI/CD.
    private let baseURL: String

    init() {
        self.baseURL = AppConfig.apiBaseURL

        #if DEBUG
        print("APIService initialized with base URL: \(baseURL)")
        #endif
    }

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        let iso8601Full = ISO8601DateFormatter()
        iso8601Full.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let iso8601Basic = ISO8601DateFormatter()
        iso8601Basic.formatOptions = [.withInternetDateTime]
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            // Try standard ISO8601 first (handles 3-digit milliseconds like "2026-02-21T02:41:05.965Z")
            if let date = iso8601Full.date(from: dateString) { return date }
            if let date = iso8601Basic.date(from: dateString) { return date }
            // Python produces microsecond precision without timezone: "2026-02-21T02:41:05.965467"
            // Truncate to 3-digit milliseconds and append Z so ISO8601DateFormatter can parse it
            var normalized = dateString
            if let dotIndex = normalized.firstIndex(of: ".") {
                let fractionalStart = normalized.index(after: dotIndex)
                let fractional = String(normalized[fractionalStart...])
                // Keep only first 3 digits of fractional seconds
                let truncated = String(fractional.prefix(3))
                normalized = String(normalized[...dotIndex]) + truncated
            }
            // Add Z if no timezone indicator present (ignore the "-" in date part like 2026-02-21)
            let hasTimezone = normalized.hasSuffix("Z") || normalized.contains("+") ||
                (normalized.count > 19 && normalized.dropFirst(19).contains("-"))
            if !hasTimezone {
                normalized += "Z"
            }
            if let date = iso8601Full.date(from: normalized) { return date }
            if let date = iso8601Basic.date(from: normalized) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode date: \(dateString)")
        }
        return decoder
    }()
    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()

    // MARK: - Query Parks (RAG)

    func queryParks(
        question: String,
        sessionId: String?,
        userId: Int?,
        location: CLLocationCoordinate2D?
    ) async throws -> QueryResponse {
        var body: [String: Any] = ["question": question]

        if let sessionId = sessionId {
            body["session_id"] = sessionId
        }
        if let userId = userId {
            body["user_id"] = userId
        }
        if let location = location {
            body["location"] = ["lat": location.latitude, "lng": location.longitude]
        }

        return try await post("/query", body: body)
    }

    func clearConversation(sessionId: String) async throws {
        let _: EmptyResponse = try await delete("/query/\(sessionId)")
    }

    // MARK: - Parks

    func listParks(
        playground: Bool? = nil,
        dogFriendly: Bool? = nil,
        restrooms: Bool? = nil,
        trails: Bool? = nil,
        limit: Int = 500,
        offset: Int = 0
    ) async throws -> ParkListResponse {
        var queryItems: [URLQueryItem] = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset))
        ]

        if let playground = playground {
            queryItems.append(URLQueryItem(name: "playground", value: String(playground)))
        }
        if let dogFriendly = dogFriendly {
            queryItems.append(URLQueryItem(name: "dog_friendly", value: String(dogFriendly)))
        }
        if let restrooms = restrooms {
            queryItems.append(URLQueryItem(name: "restrooms", value: String(restrooms)))
        }
        if let trails = trails {
            queryItems.append(URLQueryItem(name: "trails", value: String(trails)))
        }

        return try await get("/parks", queryItems: queryItems)
    }

    func getPark(name: String) async throws -> Park {
        let encoded = name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? name
        return try await get("/parks/\(encoded)")
    }

    // MARK: - Users

    func createUser(appleId: String?, email: String?, displayName: String?) async throws -> User {
        let body: [String: Any?] = [
            "apple_id": appleId,
            "email": email,
            "display_name": displayName
        ]
        return try await post("/users", body: body.compactMapValues { $0 })
    }

    func getUser(id: Int) async throws -> User {
        return try await get("/users/\(id)")
    }

    func updateUser(id: Int, displayName: String?, preferences: UserPreferences?) async throws -> User {
        var body: [String: Any] = [:]
        if let displayName = displayName {
            body["display_name"] = displayName
        }
        if let preferences = preferences {
            body["preferences"] = try encoder.encode(preferences)
        }
        return try await put("/users/\(id)", body: body)
    }

    // MARK: - Saved Parks

    func savePark(userId: Int, parkName: String, notes: String?, tags: [String]) async throws -> SavedParkResponse {
        let body: [String: Any] = [
            "park_name": parkName,
            "notes": notes ?? "",
            "tags": tags
        ]
        return try await post("/users/\(userId)/saved-parks", body: body)
    }

    func getSavedParks(userId: Int) async throws -> [SavedParkResponse] {
        return try await get("/users/\(userId)/saved-parks")
    }

    func unsavePark(userId: Int, parkName: String) async throws {
        let encoded = parkName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? parkName
        let _: EmptyResponse = try await delete("/users/\(userId)/saved-parks/\(encoded)")
    }

    // MARK: - Reviews

    func getAvailableTags() async throws -> TagsResponse {
        return try await get("/reviews/tags")
    }

    func submitReview(parkName: String, userId: Int, review: ReviewSubmission) async throws -> ReviewResponseModel {
        let encoded = parkName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? parkName
        var body: [String: Any] = [
            "park_name": parkName,
            "overall_rating": review.overallRating,
            "would_recommend": review.wouldRecommend,
            "tags": review.tags
        ]

        if let shade = review.shadeRating { body["shade_rating"] = shade }
        if let seating = review.seatingRating { body["seating_rating"] = seating }
        if let restroom = review.restroomCleanlinessRating { body["restroom_cleanliness_rating"] = restroom }
        if let playground = review.playgroundQualityRating { body["playground_quality_rating"] = playground }
        if let safety = review.safetyRating { body["safety_rating"] = safety }
        if let trail = review.trailQualityRating { body["trail_quality_rating"] = trail }
        if let crowdedness = review.crowdednessRating { body["crowdedness_rating"] = crowdedness }
        if let containment = review.containmentRating { body["containment_rating"] = containment }
        if let tips = review.tips, !tips.isEmpty { body["tips"] = tips }
        if let text = review.reviewText, !text.isEmpty { body["review_text"] = text }
        if let minAge = review.playgroundBestAgeMin { body["playground_best_age_min"] = minAge }
        if let maxAge = review.playgroundBestAgeMax { body["playground_best_age_max"] = maxAge }
        if let timeOfDay = review.visitTimeOfDay { body["visit_time_of_day"] = timeOfDay }

        // Add mom observations if provided
        if let obs = review.momObservations {
            var momObs: [String: Any] = [:]

            if let c = obs.containment {
                var containmentDict: [String: Any] = [:]
                if let ft = c.fencingType { containmentDict["fencing_type"] = ft }
                if let sl = c.sightlines { containmentDict["sightlines"] = sl }
                if let sv = c.singleVantagePoint { containmentDict["single_vantage_point"] = sv }
                if let n = c.notes { containmentDict["notes"] = n }
                if !containmentDict.isEmpty { momObs["containment"] = containmentDict }
            }

            if let l = obs.logistics {
                var logisticsDict: [String: Any] = [:]
                if let sp = l.strollerPathPaved { logisticsDict["stroller_path_paved"] = sp }
                if let pd = l.parkingToPlaygroundDistance { logisticsDict["parking_to_playground_distance"] = pd }
                if let qe = l.quickExitPossible { logisticsDict["quick_exit_possible"] = qe }
                if let n = l.notes { logisticsDict["notes"] = n }
                if !logisticsDict.isEmpty { momObs["logistics"] = logisticsDict }
            }

            if let r = obs.restrooms {
                var restroomDict: [String: Any] = [:]
                if let d = r.distanceFromPlayground { restroomDict["distance_from_playground"] = d }
                if let cw = r.changingTableWomens { restroomDict["changing_table_womens"] = cw }
                if let cm = r.changingTableMens { restroomDict["changing_table_mens"] = cm }
                if let fr = r.familyRestroom { restroomDict["family_restroom"] = fr }
                if let pt = r.pottyTrainingFriendly { restroomDict["potty_training_friendly"] = pt }
                if let n = r.notes { restroomDict["notes"] = n }
                if !restroomDict.isEmpty { momObs["restrooms"] = restroomDict }
            }

            if let s = obs.shade {
                var shadeDict: [String: Any] = [:]
                if let st = s.shadeType { shadeDict["shade_type"] = st }
                if let ps = s.playgroundShaded { shadeDict["playground_shaded"] = ps }
                if let ss = s.seatingShaded { shadeDict["seating_shaded"] = ss }
                if let n = s.notes { shadeDict["notes"] = n }
                if !shadeDict.isEmpty { momObs["shade"] = shadeDict }
            }

            if let n = obs.noiseEnvironment {
                var noiseDict: [String: Any] = [:]
                if let nl = n.noiseLevel { noiseDict["noise_level"] = nl }
                if let sf = n.sensoryFriendly { noiseDict["sensory_friendly"] = sf }
                if let notes = n.notes { noiseDict["notes"] = notes }
                if !noiseDict.isEmpty { momObs["noise_environment"] = noiseDict }
            }

            if let nb = obs.nearby {
                var nearbyDict: [String: Any] = [:]
                if let cn = nb.coffeeShopNearby { nearbyDict["coffee_shop_nearby"] = cn }
                if let name = nb.coffeeShopName { nearbyDict["coffee_shop_name"] = name }
                if let notes = nb.notes { nearbyDict["notes"] = notes }
                if !nearbyDict.isEmpty { momObs["nearby"] = nearbyDict }
            }

            if !momObs.isEmpty { body["mom_observations"] = momObs }
        }

        return try await post("/parks/\(encoded)/reviews?user_id=\(userId)", body: body)
    }

    func getReviews(parkName: String, limit: Int = 20, offset: Int = 0) async throws -> ReviewListResponseModel {
        let encoded = parkName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? parkName
        return try await get("/parks/\(encoded)/reviews", queryItems: [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset))
        ])
    }

    func markReviewHelpful(reviewId: Int) async throws {
        let _: HelpfulResponse = try await post("/reviews/\(reviewId)/helpful", body: [:])
    }

    // MARK: - Badges

    func getParkBadges(parkName: String) async throws -> [ParkBadge] {
        let encoded = parkName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? parkName
        let response: ParkBadgesResponse = try await get("/parks/\(encoded)/badges")
        return response.earnedBadges + response.pendingBadges
    }

    func confirmBadge(parkName: String, badgeId: String, reviewId: Int? = nil) async throws -> BadgeConfirmResponse {
        var body: [String: Any] = [
            "park_name": parkName,
            "badge_id": badgeId
        ]
        if let reviewId = reviewId {
            body["review_id"] = reviewId
        }
        return try await post("/badges/confirm", body: body)
    }

    func getUserProfile(userId: Int) async throws -> UserProfileWithTier {
        return try await get("/users/\(userId)/profile")
    }

    func getAllTiers() async throws -> [UserTier] {
        return try await get("/tiers")
    }

    // MARK: - Weather

    func getCurrentWeather(lat: Double? = nil, lon: Double? = nil) async throws -> WeatherResponseModel {
        var queryItems: [URLQueryItem] = []
        if let lat = lat {
            queryItems.append(URLQueryItem(name: "lat", value: String(lat)))
        }
        if let lon = lon {
            queryItems.append(URLQueryItem(name: "lon", value: String(lon)))
        }
        return try await get("/weather/current", queryItems: queryItems)
    }

    // MARK: - Health Check

    func healthCheck() async throws -> HealthResponse {
        return try await get("/health")
    }

    // MARK: - Private Helpers

    private func get<T: Decodable>(_ path: String, queryItems: [URLQueryItem] = []) async throws -> T {
        guard var components = URLComponents(string: baseURL + path) else {
            throw APIError.badRequest
        }
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }

        guard let url = components.url else {
            throw APIError.badRequest
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            #if DEBUG
            let preview = String(data: data, encoding: .utf8)?.prefix(500) ?? "nil"
            print("[APIService] Decode error for GET \(path): \(error)")
            print("[APIService] Response preview: \(preview)")
            #endif
            throw error
        }
    }

    private func post<T: Decodable>(_ path: String, body: [String: Any]) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.badRequest
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        return try decoder.decode(T.self, from: data)
    }

    private func put<T: Decodable>(_ path: String, body: [String: Any]) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.badRequest
        }

        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        return try decoder.decode(T.self, from: data)
    }

    private func delete<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.badRequest
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)

        if data.isEmpty, let emptyResponse = EmptyResponse() as? T {
            return emptyResponse
        }
        return try decoder.decode(T.self, from: data)
    }

    private func validateResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return
        case 400:
            throw APIError.badRequest
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.notFound
        case 500...599:
            throw APIError.serverError
        default:
            throw APIError.unknown(httpResponse.statusCode)
        }
    }
}

// MARK: - Response Types

struct ParkListResponse: Codable {
    let parks: [Park]
    let totalCount: Int
    let filtersApplied: [String: AnyCodable]

    enum CodingKeys: String, CodingKey {
        case parks
        case totalCount = "total_count"
        case filtersApplied = "filters_applied"
    }
}

struct SavedParkResponse: Codable, Identifiable {
    let id: Int
    let parkName: String
    let savedAt: Date
    let notes: String?
    let tags: [String]
    let visitCount: Int
    let lastVisited: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case parkName = "park_name"
        case savedAt = "saved_at"
        case notes, tags
        case visitCount = "visit_count"
        case lastVisited = "last_visited"
    }
}

struct HealthResponse: Codable {
    let status: String
    let timestamp: String
    let llmModel: String
    let embeddingModel: String

    enum CodingKeys: String, CodingKey {
        case status, timestamp
        case llmModel = "llm_model"
        case embeddingModel = "embedding_model"
    }
}

struct EmptyResponse: Codable {}

// MARK: - Review Types

struct TagsResponse: Codable {
    let tags: [String]
    let categories: [String: [String]]
}

struct ReviewSubmission {
    var overallRating: Int
    var shadeRating: Int?
    var seatingRating: Int?
    var restroomCleanlinessRating: Int?
    var playgroundQualityRating: Int?
    var trailQualityRating: Int?
    var crowdednessRating: Int?
    var safetyRating: Int?
    var containmentRating: Int?  // "Can I See My Kid" rating
    var playgroundBestAgeMin: Int?
    var playgroundBestAgeMax: Int?
    var tags: [String]
    var tips: String?
    var reviewText: String?
    var visitTimeOfDay: String?
    var wouldRecommend: Bool

    // Mom-Logic Observations
    var momObservations: MomObservations?
}

// MARK: - Mom-Logic Observations

struct MomObservations: Codable {
    var containment: ContainmentInfo?
    var surface: SurfaceInfo?
    var logistics: LogisticsInfo?
    var restrooms: RestroomInfo?
    var shade: ShadeInfo?
    var noiseEnvironment: NoiseEnvironmentInfo?
    var nearby: NearbyConveniences?

    enum CodingKeys: String, CodingKey {
        case containment, surface, logistics, restrooms, shade
        case noiseEnvironment = "noise_environment"
        case nearby
    }
}

struct ContainmentInfo: Codable {
    var fencingType: String?
    var sightlines: String?
    var singleVantagePoint: Bool?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case fencingType = "fencing_type"
        case sightlines
        case singleVantagePoint = "single_vantage_point"
        case notes
    }
}

struct SurfaceInfo: Codable {
    var surfaceType: String?
    var condition: String?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case surfaceType = "surface_type"
        case condition, notes
    }
}

struct LogisticsInfo: Codable {
    var strollerPathPaved: Bool?
    var parkingToPlaygroundDistance: String?
    var parkingLotWideSpots: Bool?
    var quickExitPossible: Bool?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case strollerPathPaved = "stroller_path_paved"
        case parkingToPlaygroundDistance = "parking_to_playground_distance"
        case parkingLotWideSpots = "parking_lot_wide_spots"
        case quickExitPossible = "quick_exit_possible"
        case notes
    }
}

struct RestroomInfo: Codable {
    var distanceFromPlayground: String?
    var changingTableWomens: Bool?
    var changingTableMens: Bool?
    var familyRestroom: Bool?
    var cleanliness: String?
    var pottyTrainingFriendly: Bool?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case distanceFromPlayground = "distance_from_playground"
        case changingTableWomens = "changing_table_womens"
        case changingTableMens = "changing_table_mens"
        case familyRestroom = "family_restroom"
        case cleanliness
        case pottyTrainingFriendly = "potty_training_friendly"
        case notes
    }
}

struct ShadeInfo: Codable {
    var shadeType: String?
    var playgroundShaded: Bool?
    var seatingShaded: Bool?
    var bestTimeForShade: String?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case shadeType = "shade_type"
        case playgroundShaded = "playground_shaded"
        case seatingShaded = "seating_shaded"
        case bestTimeForShade = "best_time_for_shade"
        case notes
    }
}

struct NoiseEnvironmentInfo: Codable {
    var noiseLevel: String?
    var nearHighway: Bool?
    var underFlightPath: Bool?
    var sensoryFriendly: Bool?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case noiseLevel = "noise_level"
        case nearHighway = "near_highway"
        case underFlightPath = "under_flight_path"
        case sensoryFriendly = "sensory_friendly"
        case notes
    }
}

struct NearbyConveniences: Codable {
    var coffeeShopNearby: Bool?
    var coffeeShopName: String?
    var restaurantNearby: Bool?
    var iceCreamNearby: Bool?
    var driveTimeMinutes: Int?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case coffeeShopNearby = "coffee_shop_nearby"
        case coffeeShopName = "coffee_shop_name"
        case restaurantNearby = "restaurant_nearby"
        case iceCreamNearby = "ice_cream_nearby"
        case driveTimeMinutes = "drive_time_minutes"
        case notes
    }
}

struct ReviewResponseModel: Codable, Identifiable {
    let id: Int
    let parkName: String
    let userId: Int
    let userDisplayName: String?
    let shadeRating: Int?
    let seatingRating: Int?
    let restroomCleanlinessRating: Int?
    let restroomAvailabilityRating: Int?
    let playgroundQualityRating: Int?
    let trailQualityRating: Int?
    let crowdednessRating: Int?
    let safetyRating: Int?
    let containmentRating: Int?
    let overallRating: Int
    let playgroundBestAgeMin: Int?
    let playgroundBestAgeMax: Int?
    let momObservations: MomObservations?
    let tags: [String]
    let tips: String?
    let reviewText: String?
    let visitDate: Date?
    let visitDayOfWeek: String?
    let visitTimeOfDay: String?
    let wouldRecommend: Bool
    let createdAt: Date
    let helpfulCount: Int

    enum CodingKeys: String, CodingKey {
        case id
        case parkName = "park_name"
        case userId = "user_id"
        case userDisplayName = "user_display_name"
        case shadeRating = "shade_rating"
        case seatingRating = "seating_rating"
        case restroomCleanlinessRating = "restroom_cleanliness_rating"
        case restroomAvailabilityRating = "restroom_availability_rating"
        case playgroundQualityRating = "playground_quality_rating"
        case trailQualityRating = "trail_quality_rating"
        case crowdednessRating = "crowdedness_rating"
        case safetyRating = "safety_rating"
        case containmentRating = "containment_rating"
        case overallRating = "overall_rating"
        case playgroundBestAgeMin = "playground_best_age_min"
        case playgroundBestAgeMax = "playground_best_age_max"
        case momObservations = "mom_observations"
        case tags, tips
        case reviewText = "review_text"
        case visitDate = "visit_date"
        case visitDayOfWeek = "visit_day_of_week"
        case visitTimeOfDay = "visit_time_of_day"
        case wouldRecommend = "would_recommend"
        case createdAt = "created_at"
        case helpfulCount = "helpful_count"
    }
}

struct ReviewListResponseModel: Codable {
    let parkName: String
    let reviews: [ReviewResponseModel]
    let totalCount: Int
    let averageOverall: Double?
    let momScore: Double?
    let topTags: [String]

    enum CodingKeys: String, CodingKey {
        case parkName = "park_name"
        case reviews
        case totalCount = "total_count"
        case averageOverall = "average_overall"
        case momScore = "mom_score"
        case topTags = "top_tags"
    }
}

struct HelpfulResponse: Codable {
    let message: String
    let helpfulCount: Int

    enum CodingKeys: String, CodingKey {
        case message
        case helpfulCount = "helpful_count"
    }
}

// MARK: - Weather Response

struct WeatherResponseModel: Codable {
    let temperatureF: Double
    let feelsLikeF: Double
    let humidity: Int
    let precipitationProbability: Int
    let condition: String
    let uvIndex: Double
    let windSpeedMph: Double
    let isDaytime: Bool

    // Mom-friendly recommendations
    let momTip: String
    let suggestedActivities: [String]
    let thingsToAvoid: [String]
    let suggestedQueries: [String]

    enum CodingKeys: String, CodingKey {
        case temperatureF = "temperature_f"
        case feelsLikeF = "feels_like_f"
        case humidity
        case precipitationProbability = "precipitation_probability"
        case condition
        case uvIndex = "uv_index"
        case windSpeedMph = "wind_speed_mph"
        case isDaytime = "is_daytime"
        case momTip = "mom_tip"
        case suggestedActivities = "suggested_activities"
        case thingsToAvoid = "things_to_avoid"
        case suggestedQueries = "suggested_queries"
    }

    // Helper computed properties
    var conditionIcon: String {
        switch condition {
        case "sunny": return "sun.max.fill"
        case "partly_cloudy": return "cloud.sun.fill"
        case "cloudy": return "cloud.fill"
        case "rainy": return "cloud.rain.fill"
        case "stormy": return "cloud.bolt.rain.fill"
        case "snowy": return "cloud.snow.fill"
        case "foggy": return "cloud.fog.fill"
        default: return "cloud.fill"
        }
    }

    var conditionDisplayName: String {
        switch condition {
        case "sunny": return "Sunny"
        case "partly_cloudy": return "Partly Cloudy"
        case "cloudy": return "Cloudy"
        case "rainy": return "Rainy"
        case "stormy": return "Stormy"
        case "snowy": return "Snowy"
        case "foggy": return "Foggy"
        default: return "Unknown"
        }
    }
}

// MARK: - AnyCodable for dynamic JSON

struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        default:
            try container.encodeNil()
        }
    }
}

// MARK: - API Errors

enum APIError: LocalizedError {
    case invalidResponse
    case badRequest
    case unauthorized
    case notFound
    case serverError
    case unknown(Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .badRequest:
            return "Invalid request"
        case .unauthorized:
            return "Please sign in to continue"
        case .notFound:
            return "Resource not found"
        case .serverError:
            return "Server error. Please try again later."
        case .unknown(let code):
            return "Error: \(code)"
        }
    }
}
