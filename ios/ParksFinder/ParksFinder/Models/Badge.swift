import Foundation

// MARK: - Badge Models

struct BadgeDefinition: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let icon: String
    let category: String
    let threshold: Int
}

struct ParkBadge: Codable, Identifiable {
    var id: String { badgeId }
    let badgeId: String
    let name: String
    let description: String
    let icon: String
    let category: String
    let confirmationCount: Int
    let isEarned: Bool
    let earnedAt: Date?

    enum CodingKeys: String, CodingKey {
        case badgeId = "badge_id"
        case name, description, icon, category
        case confirmationCount = "confirmation_count"
        case isEarned = "is_earned"
        case earnedAt = "earned_at"
    }
}

struct ParkBadgesResponse: Codable {
    let parkName: String
    let earnedBadges: [ParkBadge]
    let pendingBadges: [ParkBadge]

    enum CodingKeys: String, CodingKey {
        case parkName = "park_name"
        case earnedBadges = "earned_badges"
        case pendingBadges = "pending_badges"
    }
}

struct BadgeConfirmRequest: Codable {
    let parkName: String
    let badgeId: String
    let reviewId: Int?

    enum CodingKeys: String, CodingKey {
        case parkName = "park_name"
        case badgeId = "badge_id"
        case reviewId = "review_id"
    }
}

struct BadgeConfirmResponse: Codable {
    let badgeId: String
    let parkName: String
    let newCount: Int
    let threshold: Int
    let badgeEarned: Bool
    let message: String

    enum CodingKeys: String, CodingKey {
        case badgeId = "badge_id"
        case parkName = "park_name"
        case newCount = "new_count"
        case threshold
        case badgeEarned = "badge_earned"
        case message
    }
}

// MARK: - User Tier

struct UserTier: Codable {
    let id: String
    let name: String
    let icon: String
    let minReviews: Int
    let maxReviews: Int

    enum CodingKeys: String, CodingKey {
        case id, name, icon
        case minReviews = "min_reviews"
        case maxReviews = "max_reviews"
    }
}

struct UserProfileWithTier: Codable {
    let id: Int
    let displayName: String?
    let email: String?
    let createdAt: Date
    let reviewCount: Int
    let tier: UserTier
    let badgeConfirmationsCount: Int

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case email
        case createdAt = "created_at"
        case reviewCount = "review_count"
        case tier
        case badgeConfirmationsCount = "badge_confirmations_count"
    }
}

// MARK: - Badge Colors & Helpers

extension ParkBadge {
    var categoryColor: String {
        switch category {
        case "comfort": return "green"
        case "safety": return "blue"
        case "facilities": return "orange"
        case "age_range": return "pink"
        case "accessibility": return "purple"
        case "features": return "cyan"
        case "pets": return "brown"
        default: return "gray"
        }
    }
}

extension UserTier {
    var tierColor: String {
        switch id {
        case "tenderfoot": return "green"
        case "trailblazer": return "orange"
        case "pathfinder": return "blue"
        case "park_legend": return "yellow"
        default: return "gray"
        }
    }
}
