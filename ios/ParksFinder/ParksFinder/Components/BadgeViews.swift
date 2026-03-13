import SwiftUI

// MARK: - Badge Chip (Small inline badge)

struct BadgeChip: View {
    let badge: ParkBadge

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: badge.icon)
                .font(.system(size: 10))
            Text(badge.name)
                .font(.system(size: 11, weight: .medium))
        }
        .foregroundColor(.white)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(badgeColor)
        .cornerRadius(12)
    }

    var badgeColor: Color {
        switch badge.category {
        case "comfort": return Color(hex: "5AA89A")      // Teal (primary)
        case "safety": return Color(hex: "6B9080")       // Sage green
        case "facilities": return Color(hex: "C9A227")   // Gold
        case "age_range": return Color(hex: "7BA38F")    // Soft green
        case "accessibility": return Color(hex: "4A8B7C") // Deep teal
        case "features": return Color(hex: "8FBC8F")     // Dark sea green
        case "pets": return Color(hex: "B8860B")         // Dark gold
        default: return Color(hex: "5C6F63")             // Medium sage
        }
    }
}

// MARK: - Badge Row (Horizontal scrolling badges)

struct BadgeRow: View {
    let badges: [ParkBadge]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(badges) { badge in
                    BadgeChip(badge: badge)
                }
            }
        }
    }
}

// MARK: - Badge Card (Detailed badge view)

struct BadgeCard: View {
    let badge: ParkBadge
    let onConfirm: (() -> Void)?

    init(badge: ParkBadge, onConfirm: (() -> Void)? = nil) {
        self.badge = badge
        self.onConfirm = onConfirm
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                // Badge icon
                ZStack {
                    Circle()
                        .fill(badgeColor.opacity(0.2))
                        .frame(width: 50, height: 50)

                    Image(systemName: badge.icon)
                        .font(.system(size: 24))
                        .foregroundColor(badgeColor)
                }

                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(badge.name)
                            .font(.appHeadline)
                            .foregroundColor(.appTextPrimary)

                        if badge.isEarned {
                            Image(systemName: "checkmark.seal.fill")
                                .foregroundColor(.green)
                                .font(.system(size: 14))
                        }
                    }

                    Text(badge.description)
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                }

                Spacer()
            }

            // Progress bar
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("\(badge.confirmationCount) confirmations")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)

                    Spacer()

                    if badge.isEarned {
                        Text("Verified")
                            .font(.appCaption)
                            .fontWeight(.semibold)
                            .foregroundColor(.green)
                    } else {
                        Text("Need \(3 - badge.confirmationCount) more")
                            .font(.appCaption)
                            .foregroundColor(.appTextSecondary)
                    }
                }

                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.gray.opacity(0.2))
                            .frame(height: 8)

                        RoundedRectangle(cornerRadius: 4)
                            .fill(badge.isEarned ? Color.green : badgeColor)
                            .frame(width: geometry.size.width * CGFloat(min(badge.confirmationCount, 3)) / 3, height: 8)
                    }
                }
                .frame(height: 8)
            }

            // Confirm button (if not earned and callback provided)
            if !badge.isEarned, let onConfirm = onConfirm {
                Button(action: onConfirm) {
                    HStack {
                        Image(systemName: "hand.thumbsup.fill")
                        Text("Confirm this badge")
                    }
                    .font(.appCaption)
                    .foregroundColor(badgeColor)
                }
            }
        }
        .padding()
        .background(Color.appCard)
        .cornerRadius(12)
    }

    var badgeColor: Color {
        switch badge.category {
        case "comfort": return Color(hex: "5AA89A")      // Teal (primary)
        case "safety": return Color(hex: "6B9080")       // Sage green
        case "facilities": return Color(hex: "C9A227")   // Gold
        case "age_range": return Color(hex: "7BA38F")    // Soft green
        case "accessibility": return Color(hex: "4A8B7C") // Deep teal
        case "features": return Color(hex: "8FBC8F")     // Dark sea green
        case "pets": return Color(hex: "B8860B")         // Dark gold
        default: return Color(hex: "5C6F63")             // Medium sage
        }
    }
}

// MARK: - User Tier Badge

struct UserTierBadge: View {
    let tier: UserTier
    var showName: Bool = true

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: tier.icon)
                .font(.system(size: 12))
            if showName {
                Text(tier.name)
                    .font(.system(size: 12, weight: .semibold))
            }
        }
        .foregroundColor(tierColor)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(tierColor.opacity(0.15))
        .cornerRadius(8)
    }

    var tierColor: Color {
        switch tier.id {
        case "tenderfoot": return Color(hex: "8FBC8F")   // Light sage (beginner)
        case "trailblazer": return Color(hex: "5AA89A")  // Teal (intermediate)
        case "pathfinder": return Color(hex: "6B9080")   // Sage green (advanced)
        case "park_legend": return Color(hex: "C9A227")  // Gold (legendary)
        default: return Color(hex: "5C6F63")
        }
    }
}

// MARK: - Tier Progress Card

struct TierProgressCard: View {
    let currentTier: UserTier
    let reviewCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Your Scout Rank")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)

                    HStack {
                        Image(systemName: currentTier.icon)
                            .font(.system(size: 24))
                            .foregroundColor(tierColor)

                        Text(currentTier.name)
                            .font(.appHeadline)
                            .foregroundColor(.appTextPrimary)
                    }
                }

                Spacer()

                VStack(alignment: .trailing) {
                    Text("\(reviewCount)")
                        .font(.system(size: 28, weight: .bold))
                        .foregroundColor(.appPrimary)
                    Text("reviews")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                }
            }

            // Progress to next tier
            if let nextTier = nextTierInfo {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Next: \(nextTier.name) (\(nextTier.minReviews - reviewCount) more reviews)")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)

                    GeometryReader { geometry in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 4)
                                .fill(Color.gray.opacity(0.2))
                                .frame(height: 8)

                            RoundedRectangle(cornerRadius: 4)
                                .fill(tierColor)
                                .frame(width: geometry.size.width * progressToNextTier, height: 8)
                        }
                    }
                    .frame(height: 8)
                }
            } else {
                Text("You've reached the highest rank!")
                    .font(.appCaption)
                    .foregroundColor(.green)
            }
        }
        .padding()
        .background(Color.appCard)
        .cornerRadius(12)
    }

    var tierColor: Color {
        switch currentTier.id {
        case "tenderfoot": return Color(hex: "8FBC8F")   // Light sage (beginner)
        case "trailblazer": return Color(hex: "5AA89A")  // Teal (intermediate)
        case "pathfinder": return Color(hex: "6B9080")   // Sage green (advanced)
        case "park_legend": return Color(hex: "C9A227")  // Gold (legendary)
        default: return Color(hex: "5C6F63")
        }
    }

    var nextTierInfo: (name: String, minReviews: Int)? {
        switch currentTier.id {
        case "tenderfoot": return ("Trailblazer", 5)
        case "trailblazer": return ("Pathfinder", 15)
        case "pathfinder": return ("Park Legend", 30)
        default: return nil
        }
    }

    var progressToNextTier: CGFloat {
        guard let next = nextTierInfo else { return 1.0 }
        let rangeStart = currentTier.minReviews
        let rangeEnd = next.minReviews
        let progress = CGFloat(reviewCount - rangeStart) / CGFloat(rangeEnd - rangeStart)
        return min(max(progress, 0), 1)
    }
}

// MARK: - Previews

#Preview("Badge Chip") {
    BadgeChip(badge: ParkBadge(
        badgeId: "solar_shield",
        name: "Solar Shield",
        description: "Excellent shade coverage",
        icon: "sun.max.trianglebadge.exclamationmark",
        category: "comfort",
        confirmationCount: 5,
        isEarned: true,
        earnedAt: Date()
    ))
}

#Preview("Badge Card") {
    BadgeCard(badge: ParkBadge(
        badgeId: "solar_shield",
        name: "Solar Shield",
        description: "Excellent shade coverage",
        icon: "sun.max.trianglebadge.exclamationmark",
        category: "comfort",
        confirmationCount: 2,
        isEarned: false,
        earnedAt: nil
    ), onConfirm: {})
    .padding()
}

#Preview("User Tier Badge") {
    UserTierBadge(tier: UserTier(
        id: "trailblazer",
        name: "Trailblazer",
        icon: "flame",
        minReviews: 5,
        maxReviews: 14
    ))
}
