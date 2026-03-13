import Foundation

// MARK: - Chat Message
struct ChatMessage: Identifiable {
    let id: UUID
    let role: MessageRole
    let content: String
    let timestamp: Date
    var parksMentioned: [ParkMention]
    var isLoading: Bool

    init(
        id: UUID = UUID(),
        role: MessageRole,
        content: String,
        timestamp: Date = Date(),
        parksMentioned: [ParkMention] = [],
        isLoading: Bool = false
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.parksMentioned = parksMentioned
        self.isLoading = isLoading
    }

    static func userMessage(_ content: String) -> ChatMessage {
        ChatMessage(role: .user, content: content)
    }

    static func aiMessage(_ content: String, parks: [ParkMention] = []) -> ChatMessage {
        ChatMessage(role: .assistant, content: content, parksMentioned: parks)
    }

    static func loading() -> ChatMessage {
        ChatMessage(role: .assistant, content: "", isLoading: true)
    }
}

extension ChatMessage: Equatable {
    static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool {
        lhs.id == rhs.id
    }
}

enum MessageRole: String, Codable {
    case user
    case assistant
}

// MARK: - Conversation
struct Conversation: Identifiable, Codable {
    let id: String
    let sessionId: String
    var title: String?
    let startedAt: Date
    var messages: [StoredMessage]
    var isActive: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case sessionId = "session_id"
        case title
        case startedAt = "started_at"
        case messages
        case isActive = "is_active"
    }
}

struct StoredMessage: Identifiable, Codable {
    var id: UUID { UUID() }
    let role: String
    let content: String
    let createdAt: Date
    let parksMentioned: [String]

    enum CodingKeys: String, CodingKey {
        case role, content
        case createdAt = "created_at"
        case parksMentioned = "parks_mentioned"
    }
}

// MARK: - Quick Suggestions
struct QuickSuggestion: Identifiable {
    let id = UUID()
    let icon: String
    let title: String
    let query: String
}

extension QuickSuggestion {
    static let suggestions: [QuickSuggestion] = [
        QuickSuggestion(
            icon: "figure.and.child.holdinghands",
            title: "Toddler-friendly",
            query: "Where can I take my toddler?"
        ),
        QuickSuggestion(
            icon: "dog",
            title: "Dog parks",
            query: "Which parks are dog-friendly?"
        ),
        QuickSuggestion(
            icon: "figure.hiking",
            title: "Hiking trails",
            query: "Best parks for hiking trails?"
        ),
        QuickSuggestion(
            icon: "sparkles",
            title: "Special features",
            query: "Parks with unique features like carousels or splash pads?"
        ),
        QuickSuggestion(
            icon: "leaf",
            title: "Nature walks",
            query: "Quiet nature parks for a peaceful walk?"
        ),
        QuickSuggestion(
            icon: "sportscourt",
            title: "Sports",
            query: "Parks with sports facilities?"
        )
    ]
}
