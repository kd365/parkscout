import SwiftUI

// MARK: - Color Palette (ParkScout Theme)
extension Color {
    static let appPrimary = Color(hex: "5AA89A")      // Teal/Turquoise (compass inner)
    static let appSecondary = Color(hex: "C9A227")    // Gold (compass frame accent)
    static let appBackground = Color(hex: "F5F7F5")   // Soft sage-tinted white
    static let appCard = Color.white
    static let appTextPrimary = Color(hex: "2D3E36")  // Dark sage/forest
    static let appTextSecondary = Color(hex: "5C6F63") // Medium sage
    static let appAccent = Color(hex: "6B9080")       // Sage green (background)
    static let appGold = Color(hex: "B8860B")         // Dark gold for highlights

    // Distance category colors
    static let distanceNear = Color.green
    static let distanceModerate = Color.orange
    static let distanceDriveable = Color.gray

    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Typography
extension Font {
    static let appTitle = Font.system(size: 28, weight: .bold, design: .rounded)
    static let appTitle2 = Font.system(size: 24, weight: .bold, design: .rounded)
    static let appHeadline = Font.system(size: 20, weight: .semibold, design: .rounded)
    static let appSubheadline = Font.system(size: 16, weight: .medium)
    static let appBody = Font.system(size: 15, weight: .regular)
    static let appCaption = Font.system(size: 13, weight: .regular)
    static let appButton = Font.system(size: 16, weight: .semibold)
}

// MARK: - Card Style
struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(Color.appCard)
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 2)
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(CardStyle())
    }
}

// MARK: - Primary Button Style
struct PrimaryButtonStyle: ButtonStyle {
    var isEnabled: Bool = true

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.appButton)
            .foregroundColor(.white)
            .padding(.horizontal, 24)
            .padding(.vertical, 14)
            .background(isEnabled ? Color.appPrimary : Color.gray)
            .cornerRadius(12)
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - Secondary Button Style
struct SecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.appButton)
            .foregroundColor(.appPrimary)
            .padding(.horizontal, 24)
            .padding(.vertical, 14)
            .background(Color.appPrimary.opacity(0.1))
            .cornerRadius(12)
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - Filter Chip Style
struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.appCaption)
                .foregroundColor(isSelected ? .white : .appTextPrimary)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(isSelected ? Color.appPrimary : Color.appCard)
                .cornerRadius(20)
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(isSelected ? Color.clear : Color.gray.opacity(0.3), lineWidth: 1)
                )
        }
    }
}

// MARK: - Distance Badge
struct DistanceBadge: View {
    let category: DistanceCategory
    let minutes: Int

    var backgroundColor: Color {
        switch category {
        case .near: return .green.opacity(0.15)
        case .moderate: return .orange.opacity(0.15)
        case .driveable: return .gray.opacity(0.15)
        }
    }

    var textColor: Color {
        switch category {
        case .near: return .green
        case .moderate: return .orange
        case .driveable: return .gray
        }
    }

    var body: some View {
        HStack(spacing: 4) {
            Text(category.emoji)
            Text("\(minutes) min")
                .font(.appCaption)
                .fontWeight(.medium)
        }
        .foregroundColor(textColor)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(backgroundColor)
        .cornerRadius(12)
    }
}

// MARK: - Rating Stars
struct RatingStars: View {
    let rating: Double
    let maxRating: Int = 5

    var body: some View {
        HStack(spacing: 2) {
            ForEach(1...maxRating, id: \.self) { index in
                Image(systemName: starType(for: index))
                    .foregroundColor(.yellow)
                    .font(.system(size: 12))
            }
        }
    }

    private func starType(for index: Int) -> String {
        let value = Double(index)
        if rating >= value {
            return "star.fill"
        } else if rating >= value - 0.5 {
            return "star.leadinghalf.filled"
        } else {
            return "star"
        }
    }
}

// MARK: - Loading Dots Animation
struct LoadingDots: View {
    @State private var animating = false

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { index in
                Circle()
                    .fill(Color.appPrimary)
                    .frame(width: 8, height: 8)
                    .scaleEffect(animating ? 1.0 : 0.5)
                    .animation(
                        Animation.easeInOut(duration: 0.6)
                            .repeatForever()
                            .delay(Double(index) * 0.2),
                        value: animating
                    )
            }
        }
        .onAppear { animating = true }
    }
}

// MARK: - Amenity Icon
struct AmenityIcon: View {
    let icon: String
    let label: String
    let isAvailable: Bool

    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(isAvailable ? .appPrimary : .gray.opacity(0.4))

            Text(label)
                .font(.system(size: 10))
                .foregroundColor(isAvailable ? .appTextSecondary : .gray.opacity(0.4))
        }
        .frame(width: 60)
    }
}

// MARK: - Offline Banner
struct OfflineBanner: View {
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "wifi.slash")
                .font(.system(size: 14))
            Text("No internet connection")
                .font(.appCaption)
            Spacer()
        }
        .foregroundColor(.white)
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color.appSecondary)
    }
}

