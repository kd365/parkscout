import Foundation
import CoreLocation
import Combine

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText: String = ""
    @Published var isLoading: Bool = false
    @Published var error: String?

    private var sessionId: String?
    private var anonymousUserId: Int?
    private let apiService = APIService.shared
    private let locationService = LocationService.shared
    private let authService = AuthService.shared

    // Key for storing anonymous user ID
    private static let anonymousUserIdKey = "parks_finder_anonymous_user_id"

    /// Returns authenticated user ID if logged in, otherwise anonymous ID
    private var userId: Int? {
        authService.userId ?? anonymousUserId
    }

    init() {
        // Add welcome message
        messages.append(ChatMessage(
            role: .assistant,
            content: "Hi! I'm your Fairfax County parks guide. Ask me anything about local parks - I can help you find playgrounds, dog parks, hiking trails, and more!"
        ))

        // Load or create anonymous user for tracking
        Task {
            await loadOrCreateAnonymousUser()
        }
    }

    private func loadOrCreateAnonymousUser() async {
        // If user is authenticated, no need for anonymous user
        if authService.isAuthenticated {
            return
        }

        // Check if we have a saved anonymous user ID
        if let savedId = UserDefaults.standard.object(forKey: Self.anonymousUserIdKey) as? Int {
            anonymousUserId = savedId
            return
        }

        // Create new anonymous user
        do {
            let deviceId = UUID().uuidString
            let user = try await apiService.createUser(
                appleId: nil,
                email: nil,
                displayName: "Anonymous_\(deviceId.prefix(8))"
            )
            anonymousUserId = user.id
            UserDefaults.standard.set(user.id, forKey: Self.anonymousUserIdKey)
        } catch {
            // Continue without user tracking if creation fails
            print("Failed to create anonymous user: \(error)")
        }
    }

    func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        // Clear input and add user message
        inputText = ""
        messages.append(.userMessage(text))

        // Add loading indicator
        isLoading = true
        let loadingId = UUID()
        messages.append(ChatMessage(id: loadingId, role: .assistant, content: "", isLoading: true))

        do {
            let response = try await apiService.queryParks(
                question: text,
                sessionId: sessionId,
                userId: userId,
                location: locationService.currentLocation
            )

            // Update session ID for conversation continuity
            sessionId = response.sessionId

            // Remove loading and add response
            messages.removeAll { $0.id == loadingId }
            messages.append(.aiMessage(response.answer, parks: response.parksMentioned))

        } catch {
            messages.removeAll { $0.id == loadingId }
            self.error = error.localizedDescription
            messages.append(.aiMessage("Sorry, I had trouble answering that. Please try again."))
        }

        isLoading = false
    }

    func clearConversation() async {
        if let sessionId = sessionId {
            try? await apiService.clearConversation(sessionId: sessionId)
        }

        messages = [ChatMessage(
            role: .assistant,
            content: "Conversation cleared! What would you like to know about Fairfax County parks?"
        )]
        sessionId = nil
    }

    func useSuggestion(_ suggestion: QuickSuggestion) async {
        inputText = suggestion.query
        await sendMessage()
    }
}
