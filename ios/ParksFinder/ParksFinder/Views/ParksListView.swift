import SwiftUI

struct ParksListView: View {
    @StateObject private var viewModel = ParksViewModel()
    @State private var showFilters = false

    var body: some View {
        VStack(spacing: 0) {
            // Filter bar
            FilterBar(viewModel: viewModel, showFilters: $showFilters)

            if viewModel.isLoading {
                Spacer()
                ProgressView()
                    .scaleEffect(1.5)
                Spacer()
            } else if let error = viewModel.error {
                Spacer()
                ErrorView(message: error) {
                    Task { await viewModel.loadParks() }
                }
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        // Nearby parks section
                        if !viewModel.nearbyParks.isEmpty {
                            ParkSection(
                                title: "Near You",
                                subtitle: "Less than 10 min drive",
                                parks: viewModel.nearbyParks,
                                viewModel: viewModel
                            )
                        }

                        // Moderately close section
                        if !viewModel.moderateParks.isEmpty {
                            ParkSection(
                                title: "Moderately Close",
                                subtitle: "10-15 min drive",
                                parks: viewModel.moderateParks,
                                viewModel: viewModel
                            )
                        }

                        // Driveable section
                        if !viewModel.driveableParks.isEmpty {
                            ParkSection(
                                title: "Driveable",
                                subtitle: "15+ min drive",
                                parks: viewModel.driveableParks,
                                viewModel: viewModel
                            )
                        }

                        // All parks if no location
                        if viewModel.nearbyParks.isEmpty &&
                           viewModel.moderateParks.isEmpty &&
                           viewModel.driveableParks.isEmpty {
                            ForEach(viewModel.parks) { park in
                                NavigationLink(destination: ParkDetailView(parkName: park.parkName)) {
                                    ParkCard(park: park, viewModel: viewModel)
                                }
                            }
                        }
                    }
                    .padding()
                }
            }
        }
        .background(Color.appBackground)
        .navigationTitle("Parks")
        .navigationBarTitleDisplayMode(.large)
        .task {
            await viewModel.loadParks()
        }
        .refreshable {
            await viewModel.loadParks()
        }
    }
}

// MARK: - Filter Bar

struct FilterBar: View {
    @ObservedObject var viewModel: ParksViewModel
    @Binding var showFilters: Bool

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                FilterChip(
                    title: "Playground",
                    isSelected: viewModel.filterPlayground == true
                ) {
                    viewModel.filterPlayground = viewModel.filterPlayground == true ? nil : true
                    Task { await viewModel.loadParks() }
                }

                FilterChip(
                    title: "Dog-Friendly",
                    isSelected: viewModel.filterDogFriendly == true
                ) {
                    viewModel.filterDogFriendly = viewModel.filterDogFriendly == true ? nil : true
                    Task { await viewModel.loadParks() }
                }

                FilterChip(
                    title: "Restrooms",
                    isSelected: viewModel.filterRestrooms == true
                ) {
                    viewModel.filterRestrooms = viewModel.filterRestrooms == true ? nil : true
                    Task { await viewModel.loadParks() }
                }

                FilterChip(
                    title: "Trails",
                    isSelected: viewModel.filterTrails == true
                ) {
                    viewModel.filterTrails = viewModel.filterTrails == true ? nil : true
                    Task { await viewModel.loadParks() }
                }

                if viewModel.hasActiveFilters {
                    Button {
                        viewModel.clearFilters()
                        Task { await viewModel.loadParks() }
                    } label: {
                        Text("Clear")
                            .font(.appCaption)
                            .foregroundColor(.appSecondary)
                    }
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 12)
        }
        .background(Color.appCard)
    }
}

// MARK: - Park Section

struct ParkSection: View {
    let title: String
    let subtitle: String
    let parks: [Park]
    @ObservedObject var viewModel: ParksViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.appHeadline)
                    .foregroundColor(.appTextPrimary)

                Text(subtitle)
                    .font(.appCaption)
                    .foregroundColor(.appTextSecondary)
            }

            ForEach(parks) { park in
                NavigationLink(destination: ParkDetailView(parkName: park.parkName)) {
                    ParkCard(park: park, viewModel: viewModel)
                }
            }
        }
    }
}

// MARK: - Park Card

struct ParkCard: View {
    let park: Park
    @ObservedObject var viewModel: ParksViewModel
    @State private var earnedBadges: [ParkBadge] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(park.parkName)
                        .font(.appSubheadline)
                        .foregroundColor(.appTextPrimary)
                        .lineLimit(2)

                    if let classification = park.classification {
                        Text(classification)
                            .font(.appCaption)
                            .foregroundColor(.appTextSecondary)
                    }

                    // Rating badge or "be the first" prompt
                    if let score = park.momScore, score > 0 {
                        HStack(spacing: 4) {
                            Image(systemName: "star.fill")
                                .font(.system(size: 10))
                                .foregroundColor(.yellow)
                            Text(String(format: "%.1f", score))
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundColor(.appTextPrimary)
                            if let reviews = park.totalReviews, reviews > 0 {
                                Text("(\(reviews))")
                                    .font(.system(size: 11))
                                    .foregroundColor(.appTextSecondary)
                            }
                        }
                    } else {
                        HStack(spacing: 4) {
                            Image(systemName: "star")
                                .font(.system(size: 10))
                                .foregroundColor(.appTextSecondary)
                            Text("Be the first to review!")
                                .font(.system(size: 11))
                                .foregroundColor(.appSecondary)
                                .italic()
                        }
                    }
                }

                Spacer()

                // Save button
                Button {
                    Task { await viewModel.toggleSaved(park: park) }
                } label: {
                    Image(systemName: park.isSaved ? "heart.fill" : "heart")
                        .foregroundColor(park.isSaved ? .appSecondary : .gray)
                        .font(.system(size: 20))
                }

                // Distance badge
                if let category = park.distanceCategory, let minutes = park.driveTimeMinutes {
                    DistanceBadge(category: category, minutes: minutes)
                }
            }

            // Earned badges row
            if !earnedBadges.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(earnedBadges) { badge in
                            BadgeChip(badge: badge)
                        }
                    }
                }
            }

            // Amenities row
            HStack(spacing: 16) {
                AmenityIcon(
                    icon: "figure.play",
                    label: "Playground",
                    isAvailable: park.amenities.hasPlayground
                )
                AmenityIcon(
                    icon: "toilet",
                    label: "Restrooms",
                    isAvailable: park.amenities.hasRestrooms
                )
                AmenityIcon(
                    icon: "dog",
                    label: "Dogs",
                    isAvailable: park.amenities.isDogFriendly
                )
                AmenityIcon(
                    icon: "figure.hiking",
                    label: "Trails",
                    isAvailable: park.amenities.hasTrails
                )
            }

            // Special features
            if !park.amenities.specialFeatures.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(park.amenities.specialFeatures, id: \.self) { feature in
                            Text(feature)
                                .font(.system(size: 11))
                                .foregroundColor(.appPrimary)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.appPrimary.opacity(0.1))
                                .cornerRadius(8)
                        }
                    }
                }
            }
        }
        .padding()
        .cardStyle()
        .task {
            await loadBadges()
        }
    }

    private func loadBadges() async {
        do {
            let allBadges = try await APIService.shared.getParkBadges(parkName: park.parkName)
            earnedBadges = allBadges.filter { $0.isEarned }
        } catch {
            // Badges are optional — silently fail
        }
    }
}

// MARK: - Error View

struct ErrorView: View {
    let message: String
    let retry: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.appSecondary)

            Text(message)
                .font(.appBody)
                .foregroundColor(.appTextSecondary)
                .multilineTextAlignment(.center)

            Button("Try Again", action: retry)
                .buttonStyle(PrimaryButtonStyle())
        }
        .padding()
    }
}

#Preview {
    NavigationStack {
        ParksListView()
    }
}
