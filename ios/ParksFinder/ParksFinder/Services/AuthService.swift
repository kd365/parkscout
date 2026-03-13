import Foundation
import SwiftUI

// MARK: - Auth Models

struct RegisterRequest: Codable {
    let email: String
    let password: String
    let displayName: String?

    enum CodingKeys: String, CodingKey {
        case email, password
        case displayName = "display_name"
    }
}

struct LoginRequest: Codable {
    let email: String
    let password: String
}

struct AuthResponse: Codable {
    let userId: Int
    let email: String
    let displayName: String?
    let token: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case email
        case displayName = "display_name"
        case token, message
    }
}

// MARK: - Auth Service

@MainActor
class AuthService: ObservableObject {
    static let shared = AuthService()

    @Published var isAuthenticated = false
    @Published var currentUser: AuthUser?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let baseURL: String
    private let tokenKey = "auth_token"
    private let userKey = "auth_user"

    struct AuthUser: Codable {
        let id: Int
        let email: String
        let displayName: String?
        let token: String
    }

    init() {
        self.baseURL = AppConfig.apiBaseURL
        loadStoredAuth()
    }

    // MARK: - Stored Auth

    private func loadStoredAuth() {
        if let userData = UserDefaults.standard.data(forKey: userKey),
           let user = try? JSONDecoder().decode(AuthUser.self, from: userData) {
            self.currentUser = user
            self.isAuthenticated = true
        }
    }

    private func storeAuth(_ response: AuthResponse) {
        let user = AuthUser(
            id: response.userId,
            email: response.email,
            displayName: response.displayName,
            token: response.token
        )

        if let encoded = try? JSONEncoder().encode(user) {
            UserDefaults.standard.set(encoded, forKey: userKey)
        }

        self.currentUser = user
        self.isAuthenticated = true
    }

    private func clearStoredAuth() {
        UserDefaults.standard.removeObject(forKey: userKey)
        self.currentUser = nil
        self.isAuthenticated = false
    }

    // MARK: - API Calls

    func register(email: String, password: String, displayName: String?) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        guard let url = URL(string: "\(baseURL)/auth/register") else {
            errorMessage = "Invalid URL"
            return false
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = RegisterRequest(email: email, password: password, displayName: displayName)

        do {
            request.httpBody = try JSONEncoder().encode(body)
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                errorMessage = "Invalid response"
                return false
            }

            if httpResponse.statusCode == 200 {
                let authResponse = try JSONDecoder().decode(AuthResponse.self, from: data)
                storeAuth(authResponse)
                return true
            } else if httpResponse.statusCode == 400 {
                errorMessage = "Email already registered"
                return false
            } else {
                errorMessage = "Registration failed"
                return false
            }
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func login(email: String, password: String) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        guard let url = URL(string: "\(baseURL)/auth/login") else {
            errorMessage = "Invalid URL"
            return false
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = LoginRequest(email: email, password: password)

        do {
            request.httpBody = try JSONEncoder().encode(body)
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                errorMessage = "Invalid response"
                return false
            }

            if httpResponse.statusCode == 200 {
                let authResponse = try JSONDecoder().decode(AuthResponse.self, from: data)
                storeAuth(authResponse)
                return true
            } else if httpResponse.statusCode == 401 {
                errorMessage = "Invalid email or password"
                return false
            } else {
                errorMessage = "Login failed"
                return false
            }
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func logout() async {
        guard let token = currentUser?.token else {
            clearStoredAuth()
            return
        }

        // Call logout endpoint (best effort)
        if let url = URL(string: "\(baseURL)/auth/logout?token=\(token)") {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            try? await URLSession.shared.data(for: request)
        }

        clearStoredAuth()
    }

    // MARK: - Helpers

    var userId: Int? {
        currentUser?.id
    }

    var displayName: String {
        currentUser?.displayName ?? currentUser?.email ?? "Guest"
    }

    var authToken: String? {
        currentUser?.token
    }
}
