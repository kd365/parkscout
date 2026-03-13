import SwiftUI
import MapKit

struct ParkDetailView: View {
    let parkName: String
    var showCloseButton: Bool = false  // Set true when presented as sheet
    @Environment(\.dismiss) private var dismiss
    @State private var park: Park?
    @State private var aggregateRating: ParkAggregateRating?
    @State private var reviews: [ReviewResponseModel] = []
    @State private var reviewsResponse: ReviewListResponseModel?
    @State private var badges: [ParkBadge] = []
    @State private var isLoading = true
    @State private var showReviewSheet = false
    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 38.8462, longitude: -77.3064),
        span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05)
    )

    var body: some View {
        ScrollView {
            if isLoading {
                ProgressView()
                    .padding(.top, 100)
            } else if let park = park {
                VStack(alignment: .leading, spacing: 20) {
                    // Map header
                    Map(coordinateRegion: $region, annotationItems: [MapPin(coordinate: region.center)]) { pin in
                        MapMarker(coordinate: pin.coordinate, tint: .appPrimary)
                    }
                    .frame(height: 200)
                    .cornerRadius(16)

                    // Park info
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(park.parkName)
                                    .font(.appTitle)
                                    .foregroundColor(.appTextPrimary)

                                if let classification = park.classification {
                                    Text(classification)
                                        .font(.appSubheadline)
                                        .foregroundColor(.appTextSecondary)
                                }
                            }

                            Spacer()

                            // Distance badge
                            if let category = park.distanceCategory, let minutes = park.driveTimeMinutes {
                                DistanceBadge(category: category, minutes: minutes)
                            }
                        }

                        // Address
                        if let address = park.address {
                            HStack(spacing: 8) {
                                Image(systemName: "mappin.circle.fill")
                                    .foregroundColor(.appPrimary)
                                Text(address)
                                    .font(.appBody)
                                    .foregroundColor(.appTextSecondary)
                            }
                        }

                        // Parent Score
                        if let rating = aggregateRating {
                            ParentScoreCard(rating: rating)
                        }
                    }
                    .padding(.horizontal)

                    // ParkScout Badges Section
                    if !badges.isEmpty {
                        ParkBadgesSection(badges: badges, parkName: parkName)
                            .padding(.horizontal)
                    }

                    // Amenities grid
                    AmenitiesSection(amenities: park.amenities)
                        .padding(.horizontal)

                    // Description
                    if let description = park.description, !description.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("About")
                                .font(.appHeadline)
                                .foregroundColor(.appTextPrimary)

                            Text(description)
                                .font(.appBody)
                                .foregroundColor(.appTextSecondary)
                        }
                        .padding(.horizontal)
                    }

                    // Special features
                    if !park.amenities.specialFeatures.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Special Features")
                                .font(.appHeadline)
                                .foregroundColor(.appTextPrimary)

                            FlowLayout(spacing: 8) {
                                ForEach(park.amenities.specialFeatures, id: \.self) { feature in
                                    Text(feature)
                                        .font(.appCaption)
                                        .foregroundColor(.appPrimary)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 6)
                                        .background(Color.appPrimary.opacity(0.1))
                                        .cornerRadius(16)
                                }
                            }
                        }
                        .padding(.horizontal)
                    }

                    // Reviews Section
                    ReviewsSection(
                        parkName: parkName,
                        reviews: reviews,
                        totalCount: reviewsResponse?.totalCount ?? 0,
                        onWriteReview: { showReviewSheet = true }
                    )
                    .padding(.horizontal)

                    // Actions
                    VStack(spacing: 12) {
                        Button {
                            openDirections()
                        } label: {
                            HStack {
                                Image(systemName: "arrow.triangle.turn.up.right.circle.fill")
                                Text("Get Directions")
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PrimaryButtonStyle())

                        Button {
                            showReviewSheet = true
                        } label: {
                            HStack {
                                Image(systemName: "star.circle.fill")
                                Text("Write a Review")
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(SecondaryButtonStyle())
                    }
                    .padding()
                }
            }
        }
        .background(Color.appBackground)
        .navigationTitle("Park Details")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if showCloseButton {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") {
                        dismiss()
                    }
                }
            }
        }
        .task {
            await loadPark()
            await loadReviews()
            await loadBadges()
        }
        .sheet(isPresented: $showReviewSheet) {
            ReviewSheet(parkName: parkName)
        }
        .onChange(of: showReviewSheet) { _, isShowing in
            if !isShowing {
                // Reload reviews after submitting
                Task { await loadReviews() }
            }
        }
    }

    private func loadPark() async {
        isLoading = true
        do {
            park = try await APIService.shared.getPark(name: parkName)
        } catch {
            print("Error loading park: \(error)")
        }
        isLoading = false
    }

    private func loadReviews() async {
        do {
            print("[ParkDetail] Loading reviews for: \(parkName)")
            let response = try await APIService.shared.getReviews(parkName: parkName, limit: 5)
            print("[ParkDetail] Got \(response.reviews.count) reviews, totalCount: \(response.totalCount)")
            reviewsResponse = response
            reviews = response.reviews

            // Update aggregate rating from reviews response
            if let momScore = response.momScore {
                aggregateRating = ParkAggregateRating(
                    parkName: parkName,
                    momScore: momScore,
                    totalReviews: response.totalCount,
                    avgShade: nil,
                    avgSeating: nil,
                    avgRestroomCleanliness: nil,
                    avgPlaygroundQuality: nil,
                    avgTrailQuality: nil,
                    avgSafety: nil,
                    popularTags: response.topTags
                )
            }
        } catch {
            print("[ParkDetail] ERROR loading reviews: \(error)")
        }
    }

    private func loadBadges() async {
        do {
            print("[ParkDetail] Loading badges for: \(parkName)")
            badges = try await APIService.shared.getParkBadges(parkName: parkName)
            print("[ParkDetail] Got \(badges.count) badges (\(badges.filter { $0.isEarned }.count) earned)")
        } catch {
            print("[ParkDetail] ERROR loading badges: \(error)")
        }
    }

    private func openDirections() {
        guard let address = park?.address else { return }
        let encoded = address.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? address
        if let url = URL(string: "maps://?daddr=\(encoded)") {
            UIApplication.shared.open(url)
        }
    }
}

// MARK: - Park Badges Section

struct ParkBadgesSection: View {
    let badges: [ParkBadge]
    let parkName: String
    @State private var showAllBadges = false

    var earnedBadges: [ParkBadge] {
        badges.filter { $0.isEarned }
    }

    var inProgressBadges: [ParkBadge] {
        badges.filter { !$0.isEarned && $0.confirmationCount > 0 }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "rosette")
                    .foregroundColor(.appPrimary)
                Text("ParkScout Badges")
                    .font(.appHeadline)
                    .foregroundColor(.appTextPrimary)

                Spacer()

                if badges.count > 3 {
                    Button("See All") {
                        showAllBadges = true
                    }
                    .font(.appCaption)
                    .foregroundColor(.appPrimary)
                }
            }

            if earnedBadges.isEmpty && inProgressBadges.isEmpty {
                HStack {
                    Image(systemName: "checkmark.seal")
                        .foregroundColor(.appTextSecondary)
                    Text("No badges earned yet. Be the first to verify!")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                }
                .padding(.vertical, 8)
            } else {
                // Show earned badges as chips
                if !earnedBadges.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Verified by ParkScouts")
                            .font(.caption)
                            .foregroundColor(.appTextSecondary)

                        BadgeRow(badges: earnedBadges)
                    }
                }

                // Show progress on unearned badges
                if !inProgressBadges.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("In Progress")
                            .font(.caption)
                            .foregroundColor(.appTextSecondary)

                        ForEach(inProgressBadges.prefix(2)) { badge in
                            BadgeProgressRow(badge: badge)
                        }
                    }
                }
            }
        }
        .padding()
        .cardStyle()
        .sheet(isPresented: $showAllBadges) {
            AllBadgesView(badges: badges, parkName: parkName)
        }
    }
}

// MARK: - Badge Progress Row

struct BadgeProgressRow: View {
    let badge: ParkBadge

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: badge.icon)
                .font(.system(size: 16))
                .foregroundColor(badgeColor)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(badge.name)
                    .font(.appCaption)
                    .foregroundColor(.appTextPrimary)

                HStack(spacing: 4) {
                    ForEach(0..<3) { index in
                        Circle()
                            .fill(index < badge.confirmationCount ? badgeColor : Color.gray.opacity(0.3))
                            .frame(width: 8, height: 8)
                    }
                    Text("\(badge.confirmationCount)/3")
                        .font(.caption2)
                        .foregroundColor(.appTextSecondary)
                }
            }

            Spacer()
        }
    }

    var badgeColor: Color {
        switch badge.category {
        case "comfort": return Color(hex: "5AA89A")
        case "safety": return Color(hex: "6B9080")
        case "facilities": return Color(hex: "C9A227")
        case "age_range": return Color(hex: "7BA38F")
        case "accessibility": return Color(hex: "4A8B7C")
        case "features": return Color(hex: "8FBC8F")
        case "pets": return Color(hex: "B8860B")
        default: return Color(hex: "5C6F63")
        }
    }
}

// MARK: - All Badges View

struct AllBadgesView: View {
    let badges: [ParkBadge]
    let parkName: String
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 12) {
                    ForEach(badges) { badge in
                        BadgeCard(badge: badge, onConfirm: {
                            confirmBadge(badge)
                        })
                        .padding(.horizontal)
                    }
                }
                .padding(.vertical)
            }
            .background(Color.appBackground)
            .navigationTitle("Park Badges")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private func confirmBadge(_ badge: ParkBadge) {
        Task {
            do {
                _ = try await APIService.shared.confirmBadge(parkName: parkName, badgeId: badge.badgeId)
            } catch {
                print("Error confirming badge: \(error)")
            }
        }
    }
}

// MARK: - Map Pin

struct MapPin: Identifiable {
    let id = UUID()
    let coordinate: CLLocationCoordinate2D
}

// MARK: - Parent Score Card

struct ParentScoreCard: View {
    let rating: ParkAggregateRating

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Parent Score")
                        .font(.appSubheadline)
                        .foregroundColor(.appTextSecondary)

                    HStack(spacing: 8) {
                        Text(String(format: "%.1f", rating.momScore))
                            .font(.system(size: 32, weight: .bold))
                            .foregroundColor(.appPrimary)

                        RatingStars(rating: rating.momScore)
                    }
                }

                Spacer()

                Text("\(rating.totalReviews) reviews")
                    .font(.appCaption)
                    .foregroundColor(.appTextSecondary)
            }

            // Rating breakdown
            VStack(spacing: 8) {
                if let shade = rating.avgShade {
                    RatingRow(label: "Shade", value: shade, icon: "sun.max")
                }
                if let seating = rating.avgSeating {
                    RatingRow(label: "Seating", value: seating, icon: "chair")
                }
                if let restroom = rating.avgRestroomCleanliness {
                    RatingRow(label: "Restrooms", value: restroom, icon: "toilet")
                }
                if let playground = rating.avgPlaygroundQuality {
                    RatingRow(label: "Playground", value: playground, icon: "figure.play")
                }
                if let safety = rating.avgSafety {
                    RatingRow(label: "Safety", value: safety, icon: "shield.checkered")
                }
            }

            // Popular tags
            if !rating.popularTags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(rating.popularTags, id: \.self) { tag in
                            Text(tag)
                                .font(.system(size: 11))
                                .foregroundColor(.appSecondary)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.appSecondary.opacity(0.1))
                                .cornerRadius(8)
                        }
                    }
                }
            }
        }
        .padding()
        .cardStyle()
    }
}

struct RatingRow: View {
    let label: String
    let value: Double
    let icon: String

    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundColor(.appPrimary)
                .frame(width: 24)

            Text(label)
                .font(.appCaption)
                .foregroundColor(.appTextSecondary)

            Spacer()

            // Progress bar
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 6)
                        .cornerRadius(3)

                    Rectangle()
                        .fill(Color.appPrimary)
                        .frame(width: geo.size.width * (value / 5.0), height: 6)
                        .cornerRadius(3)
                }
            }
            .frame(width: 80, height: 6)

            Text(String(format: "%.1f", value))
                .font(.appCaption)
                .foregroundColor(.appTextPrimary)
                .frame(width: 30, alignment: .trailing)
        }
    }
}

// MARK: - Amenities Section

struct AmenitiesSection: View {
    let amenities: ParkAmenities

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Amenities")
                .font(.appHeadline)
                .foregroundColor(.appTextPrimary)

            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 16) {
                AmenityIcon(icon: "figure.play", label: "Playground", isAvailable: amenities.hasPlayground)
                AmenityIcon(icon: "toilet", label: "Restrooms", isAvailable: amenities.hasRestrooms)
                AmenityIcon(icon: "dog", label: "Dogs OK", isAvailable: amenities.isDogFriendly)
                AmenityIcon(icon: "figure.hiking", label: "Trails", isAvailable: amenities.hasTrails)
            }

            // Additional details
            VStack(alignment: .leading, spacing: 8) {
                if amenities.playground != "No" {
                    DetailRow(icon: "figure.play", label: "Playground", value: amenities.playground)
                }
                if amenities.trails != "None" {
                    DetailRow(icon: "figure.hiking", label: "Trails", value: amenities.trails)
                }
                if amenities.waterActivities != "None" {
                    DetailRow(icon: "drop.fill", label: "Water", value: amenities.waterActivities)
                }
                DetailRow(icon: "car.fill", label: "Parking", value: amenities.parking)
            }
        }
        .padding()
        .cardStyle()
    }
}

struct DetailRow: View {
    let icon: String
    let label: String
    let value: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.appPrimary)
                .frame(width: 24)

            Text(label)
                .font(.appBody)
                .foregroundColor(.appTextSecondary)

            Spacer()

            Text(value)
                .font(.appBody)
                .foregroundColor(.appTextPrimary)
        }
    }
}

// MARK: - Review Sheet

struct ReviewSheet: View {
    let parkName: String
    @Environment(\.dismiss) var dismiss

    // Ratings
    @State private var overallRating = 0
    @State private var shadeRating = 0
    @State private var seatingRating = 0
    @State private var restroomRating = 0
    @State private var playgroundRating = 0
    @State private var safetyRating = 0
    @State private var trailRating = 0
    @State private var crowdednessRating = 0

    // Age range
    @State private var bestAgeMin: Int?
    @State private var bestAgeMax: Int?

    // Tags
    @State private var selectedTags: Set<String> = []
    @State private var availableTags: [String] = []
    @State private var tagCategories: [String: [String]] = [:]

    // Badge confirmations
    @State private var selectedBadges: Set<String> = []

    // Text
    @State private var tips = ""
    @State private var reviewText = ""

    // Visit context
    @State private var visitTimeOfDay = "Morning"
    @State private var wouldRecommend = true

    // State
    @State private var isSubmitting = false
    @State private var showError = false
    @State private var errorMessage = ""

    private let timeOptions = ["Morning", "Afternoon", "Evening"]
    private let ageOptions = Array(0...12)

    // Available badges for confirmation
    private let confirmableBadges: [(id: String, name: String, icon: String, description: String)] = [
        ("solar_shield", "Solar Shield", "sun.max.trianglebadge.exclamationmark", "Great shade coverage"),
        ("the_fortress", "The Fortress", "shield.lefthalf.filled", "Fully fenced playground"),
        ("golden_throne", "Golden Throne", "toilet.fill", "Clean, well-stocked restrooms"),
        ("tiny_explorer", "Tiny Explorer", "figure.and.child.holdinghands", "Great for toddlers (1-3)"),
        ("smooth_sailing", "Smooth Sailing", "figure.roll", "Accessible paths & equipment"),
        ("feast_grounds", "Feast Grounds", "fork.knife", "Picnic tables & pavilions"),
        ("splash_zone", "Splash Zone", "drop.fill", "Water play features"),
        ("paws_welcome", "Paws Welcome", "pawprint.fill", "Dog-friendly with bags/water")
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section("Overall Rating *") {
                    StarRatingPicker(rating: $overallRating)
                    Toggle("Would recommend", isOn: $wouldRecommend)
                }

                Section("Mom Ratings (optional)") {
                    RatingPickerRow(label: "Shade", rating: $shadeRating, icon: "sun.max")
                    RatingPickerRow(label: "Seating", rating: $seatingRating, icon: "chair")
                    RatingPickerRow(label: "Restrooms", rating: $restroomRating, icon: "toilet")
                    RatingPickerRow(label: "Playground", rating: $playgroundRating, icon: "figure.play")
                    RatingPickerRow(label: "Trails", rating: $trailRating, icon: "figure.hiking")
                    RatingPickerRow(label: "Safety", rating: $safetyRating, icon: "shield.checkered")
                    RatingPickerRow(label: "Crowdedness", rating: $crowdednessRating, icon: "person.3")
                }

                Section("Best Ages for Playground") {
                    HStack {
                        Picker("From", selection: Binding(
                            get: { bestAgeMin ?? 0 },
                            set: { bestAgeMin = $0 == 0 ? nil : $0 }
                        )) {
                            Text("Any").tag(0)
                            ForEach(1...12, id: \.self) { age in
                                Text("\(age)").tag(age)
                            }
                        }
                        Text("to")
                        Picker("To", selection: Binding(
                            get: { bestAgeMax ?? 0 },
                            set: { bestAgeMax = $0 == 0 ? nil : $0 }
                        )) {
                            Text("Any").tag(0)
                            ForEach(1...12, id: \.self) { age in
                                Text("\(age)").tag(age)
                            }
                        }
                        Text("years")
                    }
                }

                Section("Tags") {
                    if availableTags.isEmpty {
                        ProgressView("Loading tags...")
                    } else {
                        TagSelectionView(
                            availableTags: availableTags,
                            categories: tagCategories,
                            selectedTags: $selectedTags
                        )
                    }
                }

                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Help other ParkScouts by confirming what you saw:")
                            .font(.caption)
                            .foregroundColor(.appTextSecondary)

                        FlowLayout(spacing: 8) {
                            ForEach(confirmableBadges, id: \.id) { badge in
                                BadgeConfirmChip(
                                    name: badge.name,
                                    icon: badge.icon,
                                    isSelected: selectedBadges.contains(badge.id),
                                    onTap: {
                                        if selectedBadges.contains(badge.id) {
                                            selectedBadges.remove(badge.id)
                                        } else {
                                            selectedBadges.insert(badge.id)
                                        }
                                    }
                                )
                            }
                        }
                    }
                } header: {
                    HStack {
                        Image(systemName: "rosette")
                        Text("Confirm Badges")
                    }
                }

                Section("When did you visit?") {
                    Picker("Time of day", selection: $visitTimeOfDay) {
                        ForEach(timeOptions, id: \.self) { time in
                            Text(time).tag(time)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Section("Tips for Other Parents") {
                    TextField("e.g., Best parking is on the east side", text: $tips, axis: .vertical)
                        .lineLimit(3...6)
                }

                Section("Full Review (optional)") {
                    TextEditor(text: $reviewText)
                        .frame(minHeight: 80)
                }
            }
            .navigationTitle("Review")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Submit") {
                        Task { await submitReview() }
                    }
                    .disabled(overallRating == 0 || isSubmitting)
                }
            }
            .task {
                await loadTags()
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") { }
            } message: {
                Text(errorMessage)
            }
            .overlay {
                if isSubmitting {
                    ZStack {
                        Color.black.opacity(0.3)
                        ProgressView("Submitting...")
                            .padding()
                            .background(Color.appCard)
                            .cornerRadius(10)
                    }
                    .ignoresSafeArea()
                }
            }
        }
    }

    private func loadTags() async {
        do {
            let response = try await APIService.shared.getAvailableTags()
            availableTags = response.tags
            tagCategories = response.categories
        } catch {
            // Use default tags if API fails
            availableTags = [
                "stroller-friendly", "shaded-playground", "clean-restrooms",
                "good-for-toddlers-1-3", "good-for-preschool-3-5", "fenced-playground",
                "usually-quiet", "can-get-crowded", "good-for-birthday-parties"
            ]
        }
    }

    private func submitReview() async {
        isSubmitting = true

        // Get user ID from UserDefaults
        guard let userId = UserDefaults.standard.object(forKey: "parks_finder_anonymous_user_id") as? Int else {
            errorMessage = "Please restart the app to enable reviews"
            showError = true
            isSubmitting = false
            return
        }

        let review = ReviewSubmission(
            overallRating: overallRating,
            shadeRating: shadeRating > 0 ? shadeRating : nil,
            seatingRating: seatingRating > 0 ? seatingRating : nil,
            restroomCleanlinessRating: restroomRating > 0 ? restroomRating : nil,
            playgroundQualityRating: playgroundRating > 0 ? playgroundRating : nil,
            trailQualityRating: trailRating > 0 ? trailRating : nil,
            crowdednessRating: crowdednessRating > 0 ? crowdednessRating : nil,
            safetyRating: safetyRating > 0 ? safetyRating : nil,
            playgroundBestAgeMin: bestAgeMin,
            playgroundBestAgeMax: bestAgeMax,
            tags: Array(selectedTags),
            tips: tips.isEmpty ? nil : tips,
            reviewText: reviewText.isEmpty ? nil : reviewText,
            visitTimeOfDay: visitTimeOfDay,
            wouldRecommend: wouldRecommend
        )

        do {
            let submittedReview = try await APIService.shared.submitReview(parkName: parkName, userId: userId, review: review)

            // Submit badge confirmations
            for badgeId in selectedBadges {
                _ = try? await APIService.shared.confirmBadge(
                    parkName: parkName,
                    badgeId: badgeId,
                    reviewId: submittedReview.id
                )
            }

            dismiss()
        } catch {
            errorMessage = "Failed to submit review: \(error.localizedDescription)"
            showError = true
        }

        isSubmitting = false
    }
}

// MARK: - Badge Confirm Chip

struct BadgeConfirmChip: View {
    let name: String
    let icon: String
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 12))
                Text(name)
                    .font(.system(size: 12))
            }
            .foregroundColor(isSelected ? .white : .appPrimary)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(isSelected ? Color.appPrimary : Color.appPrimary.opacity(0.1))
            .cornerRadius(14)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Tag Selection View

struct TagSelectionView: View {
    let availableTags: [String]
    let categories: [String: [String]]
    @Binding var selectedTags: Set<String>

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Show by category if available
            if !categories.isEmpty {
                ForEach(Array(categories.keys.sorted()), id: \.self) { category in
                    if let tags = categories[category], !tags.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(category.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)

                            FlowLayout(spacing: 6) {
                                ForEach(tags, id: \.self) { tag in
                                    TagChip(
                                        tag: formatTag(tag),
                                        isSelected: selectedTags.contains(tag),
                                        onTap: { toggleTag(tag) }
                                    )
                                }
                            }
                        }
                    }
                }
            } else {
                // Flat list
                FlowLayout(spacing: 6) {
                    ForEach(availableTags, id: \.self) { tag in
                        TagChip(
                            tag: formatTag(tag),
                            isSelected: selectedTags.contains(tag),
                            onTap: { toggleTag(tag) }
                        )
                    }
                }
            }
        }
    }

    private func toggleTag(_ tag: String) {
        if selectedTags.contains(tag) {
            selectedTags.remove(tag)
        } else {
            selectedTags.insert(tag)
        }
    }

    private func formatTag(_ tag: String) -> String {
        tag.replacingOccurrences(of: "-", with: " ").capitalized
    }
}

struct TagChip: View {
    let tag: String
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            Text(tag)
                .font(.system(size: 12))
                .foregroundColor(isSelected ? .white : .appPrimary)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(isSelected ? Color.appPrimary : Color.appPrimary.opacity(0.1))
                .cornerRadius(14)
        }
        .buttonStyle(.plain)
    }
}

struct StarRatingPicker: View {
    @Binding var rating: Int

    var body: some View {
        HStack(spacing: 8) {
            ForEach(1...5, id: \.self) { star in
                Image(systemName: star <= rating ? "star.fill" : "star")
                    .font(.system(size: 32))
                    .foregroundColor(star <= rating ? .yellow : .gray)
                    .onTapGesture {
                        rating = star
                    }
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .padding(.vertical, 8)
    }
}

struct RatingPickerRow: View {
    let label: String
    @Binding var rating: Int
    var icon: String? = nil

    var body: some View {
        HStack {
            if let icon = icon {
                Image(systemName: icon)
                    .foregroundColor(.appPrimary)
                    .frame(width: 24)
            }
            Text(label)
            Spacer()
            HStack(spacing: 4) {
                ForEach(1...5, id: \.self) { star in
                    Image(systemName: star <= rating ? "star.fill" : "star")
                        .font(.system(size: 20))
                        .foregroundColor(star <= rating ? .yellow : .gray)
                        .onTapGesture {
                            rating = star
                        }
                }
            }
        }
    }
}

// MARK: - Reviews Section

struct ReviewsSection: View {
    let parkName: String
    let reviews: [ReviewResponseModel]
    let totalCount: Int
    let onWriteReview: () -> Void
    @State private var showAllReviews = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Reviews")
                    .font(.appHeadline)
                    .foregroundColor(.appTextPrimary)

                Spacer()

                if totalCount > 0 {
                    Text("\(totalCount) reviews")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                }
            }

            if reviews.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "star.bubble")
                        .font(.system(size: 40))
                        .foregroundColor(.gray.opacity(0.5))

                    Text("No reviews yet")
                        .font(.appBody)
                        .foregroundColor(.appTextSecondary)

                    Button("Be the first to review") {
                        onWriteReview()
                    }
                    .font(.appBody)
                    .foregroundColor(.appPrimary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 24)
            } else {
                ForEach(reviews) { review in
                    ReviewCard(review: review)
                }

                if totalCount > reviews.count {
                    Button {
                        showAllReviews = true
                    } label: {
                        Text("See all \(totalCount) reviews")
                            .font(.appBody)
                            .foregroundColor(.appPrimary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 8)
                }
            }
        }
        .padding()
        .cardStyle()
        .sheet(isPresented: $showAllReviews) {
            AllReviewsView(parkName: parkName, onWriteReview: onWriteReview)
        }
    }
}

// MARK: - All Reviews View

struct AllReviewsView: View {
    let parkName: String
    let onWriteReview: () -> Void
    @Environment(\.dismiss) var dismiss
    @State private var reviews: [ReviewResponseModel] = []
    @State private var isLoading = true
    @State private var hasMore = false
    @State private var offset = 0
    private let pageSize = 20

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && reviews.isEmpty {
                    ProgressView("Loading reviews...")
                } else if reviews.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "star.bubble")
                            .font(.system(size: 50))
                            .foregroundColor(.gray.opacity(0.5))

                        Text("No reviews yet")
                            .font(.appHeadline)
                            .foregroundColor(.appTextSecondary)

                        Button("Write the first review") {
                            dismiss()
                            onWriteReview()
                        }
                        .buttonStyle(PrimaryButtonStyle())
                    }
                    .padding()
                } else {
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(reviews) { review in
                                ReviewCard(review: review)
                                    .padding(.horizontal)
                            }

                            if hasMore {
                                Button {
                                    Task { await loadMore() }
                                } label: {
                                    if isLoading {
                                        ProgressView()
                                    } else {
                                        Text("Load more reviews")
                                            .font(.appBody)
                                            .foregroundColor(.appPrimary)
                                    }
                                }
                                .padding()
                            }
                        }
                        .padding(.vertical)
                    }
                }
            }
            .background(Color.appBackground)
            .navigationTitle("Reviews")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        dismiss()
                        onWriteReview()
                    } label: {
                        Image(systemName: "square.and.pencil")
                    }
                }
            }
            .task {
                await loadReviews()
            }
        }
    }

    private func loadReviews() async {
        isLoading = true
        do {
            let response = try await APIService.shared.getReviews(parkName: parkName, limit: pageSize, offset: 0)
            reviews = response.reviews
            hasMore = response.totalCount > response.reviews.count
            offset = response.reviews.count
        } catch {
            print("Error loading reviews: \(error)")
        }
        isLoading = false
    }

    private func loadMore() async {
        guard !isLoading else { return }
        isLoading = true
        do {
            let response = try await APIService.shared.getReviews(parkName: parkName, limit: pageSize, offset: offset)
            reviews.append(contentsOf: response.reviews)
            hasMore = reviews.count < response.totalCount
            offset = reviews.count
        } catch {
            print("Error loading more reviews: \(error)")
        }
        isLoading = false
    }
}

struct ReviewCard: View {
    let review: ReviewResponseModel
    @State private var helpfulCount: Int

    init(review: ReviewResponseModel) {
        self.review = review
        self._helpfulCount = State(initialValue: review.helpfulCount)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(review.userDisplayName ?? "Anonymous")
                        .font(.appSubheadline)
                        .foregroundColor(.appTextPrimary)

                    Text(review.createdAt, style: .date)
                        .font(.caption2)
                        .foregroundColor(.appTextSecondary)
                }

                Spacer()

                // Rating
                HStack(spacing: 2) {
                    ForEach(1...5, id: \.self) { star in
                        Image(systemName: star <= review.overallRating ? "star.fill" : "star")
                            .font(.system(size: 12))
                            .foregroundColor(star <= review.overallRating ? .yellow : .gray)
                    }
                }
            }

            // Tags
            if !review.tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 4) {
                        ForEach(review.tags, id: \.self) { tag in
                            Text(tag.replacingOccurrences(of: "-", with: " ").capitalized)
                                .font(.system(size: 10))
                                .foregroundColor(.appSecondary)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 3)
                                .background(Color.appSecondary.opacity(0.1))
                                .cornerRadius(6)
                        }
                    }
                }
            }

            // Tips
            if let tips = review.tips, !tips.isEmpty {
                HStack(alignment: .top, spacing: 6) {
                    Image(systemName: "lightbulb.fill")
                        .font(.system(size: 12))
                        .foregroundColor(.yellow)

                    Text(tips)
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                        .lineLimit(3)
                }
                .padding(8)
                .background(Color.yellow.opacity(0.1))
                .cornerRadius(8)
            }

            // Review text
            if let text = review.reviewText, !text.isEmpty {
                Text(text)
                    .font(.appCaption)
                    .foregroundColor(.appTextSecondary)
                    .lineLimit(4)
            }

            // Age range
            if let minAge = review.playgroundBestAgeMin, let maxAge = review.playgroundBestAgeMax {
                Text("Best for ages \(minAge)-\(maxAge)")
                    .font(.caption2)
                    .foregroundColor(.appPrimary)
            }

            // Helpful button
            HStack {
                Spacer()
                Button {
                    markHelpful()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "hand.thumbsup")
                        Text("Helpful")
                        if helpfulCount > 0 {
                            Text("(\(helpfulCount))")
                        }
                    }
                    .font(.caption)
                    .foregroundColor(.appTextSecondary)
                }
            }
        }
        .padding()
        .background(Color.appBackground)
        .cornerRadius(12)
    }

    private func markHelpful() {
        Task {
            do {
                try await APIService.shared.markReviewHelpful(reviewId: review.id)
                helpfulCount += 1
            } catch {
                print("Error marking helpful: \(error)")
            }
        }
    }
}

// MARK: - Flow Layout

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(in: proposal.width ?? 0, spacing: spacing, subviews: subviews)
        return CGSize(width: proposal.width ?? 0, height: result.height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, spacing: spacing, subviews: subviews)

        for (index, subview) in subviews.enumerated() {
            let point = result.positions[index]
            subview.place(at: CGPoint(x: bounds.minX + point.x, y: bounds.minY + point.y), proposal: .unspecified)
        }
    }

    struct FlowResult {
        var positions: [CGPoint] = []
        var height: CGFloat = 0

        init(in width: CGFloat, spacing: CGFloat, subviews: Subviews) {
            var x: CGFloat = 0
            var y: CGFloat = 0
            var maxHeight: CGFloat = 0

            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)

                if x + size.width > width, x > 0 {
                    x = 0
                    y += maxHeight + spacing
                    maxHeight = 0
                }

                positions.append(CGPoint(x: x, y: y))
                maxHeight = max(maxHeight, size.height)
                x += size.width + spacing
            }

            height = y + maxHeight
        }
    }
}

#Preview {
    NavigationStack {
        ParkDetailView(parkName: "Burke Lake Park")
    }
}
