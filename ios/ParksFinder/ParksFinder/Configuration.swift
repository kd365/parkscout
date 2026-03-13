import Foundation

/// App-wide configuration values
enum AppConfig {
    /// The current API base URL
    /// In DEBUG mode: Uses localhost for development
    /// In RELEASE mode: Uses production URL
    ///
    /// To override in CI/CD:
    /// 1. Add API_BASE_URL to your scheme's environment variables, or
    /// 2. Add API_BASE_URL to Info.plist in Xcode build settings
    static var apiBaseURL: String {
        // Check environment variable first (for CI/CD)
        if let envURL = ProcessInfo.processInfo.environment["API_BASE_URL"],
           !envURL.isEmpty {
            return envURL
        }

        // Check Info.plist (can be set via xcconfig or build settings)
        if let plistURL = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
           !plistURL.isEmpty {
            return plistURL
        }

        // Default based on build configuration
        #if DEBUG
        return "http://localhost:8001"
        #else
        // TODO: Update this URL before App Store release
        // Examples:
        // - AWS API Gateway: https://abc123.execute-api.us-east-1.amazonaws.com/prod
        // - Railway: https://parks-finder-api.up.railway.app
        // - Render: https://parks-finder-api.onrender.com
        // - Custom domain: https://api.parksfinder.app
        return "https://api.parksfinder.app"
        #endif
    }

    /// App version string
    static var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }

    /// Build number
    static var buildNumber: String {
        Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
    }

    /// Full version string (e.g., "1.0.0 (42)")
    static var fullVersionString: String {
        "\(appVersion) (\(buildNumber))"
    }

    /// Whether running in debug mode
    static var isDebug: Bool {
        #if DEBUG
        return true
        #else
        return false
        #endif
    }
}
