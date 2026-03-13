import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @StateObject private var locationService = LocationService.shared
    @ObservedObject private var networkMonitor = NetworkMonitor.shared
    @AppStorage("hasSeenOnboarding") private var hasSeenOnboarding = false
    @State private var showOnboarding = false

    var body: some View {
        VStack(spacing: 0) {
            // Offline banner at top
            if !networkMonitor.isConnected {
                OfflineBanner()
                    .transition(.move(edge: .top).combined(with: .opacity))
            }

            TabView(selection: $selectedTab) {
            // Parks List Tab - Primary content
            NavigationStack {
                ParksListView()
            }
            .tabItem {
                Image(systemName: "tree.fill")
                Text("Parks")
            }
            .tag(0)

            // Map Tab - Explore
            NavigationStack {
                MapView()
            }
            .tabItem {
                Image(systemName: "map.fill")
                Text("Explore")
            }
            .tag(1)

            // Park Picker Tab (Compass/Roulette)
            NavigationStack {
                ParkPickerView()
            }
            .tabItem {
                Image(systemName: "safari.fill")
                Text("Discover")
            }
            .tag(2)

            // Chat Tab - Scout AI Guide
            NavigationStack {
                ChatView()
            }
            .tabItem {
                Image(systemName: "bubble.left.and.text.bubble.right.fill")
                Text("Scout")
            }
            .tag(3)

            // Profile Tab - Scout Profile (includes Saved Parks)
            NavigationStack {
                ProfileView()
            }
            .tabItem {
                Image(systemName: "person.crop.circle.fill")
                Text("Profile")
            }
            .tag(4)
        }
        }
        .animation(.easeInOut(duration: 0.3), value: networkMonitor.isConnected)
        .tint(.appPrimary)
        .onAppear {
            // Request location permission
            locationService.requestPermission()

            // Customize tab bar appearance
            let appearance = UITabBarAppearance()
            appearance.configureWithOpaqueBackground()
            appearance.backgroundColor = UIColor(Color.appCard)
            UITabBar.appearance().standardAppearance = appearance
            UITabBar.appearance().scrollEdgeAppearance = appearance
        }
        .fullScreenCover(isPresented: $showOnboarding) {
            OnboardingView(hasSeenOnboarding: $hasSeenOnboarding) {
                showOnboarding = false
            }
        }
        .onAppear {
            // Show onboarding every launch unless user toggled "Don't show again"
            // Delay so splash screen finishes first (splash is ~2.3s total)
            print("[Onboarding] hasSeenOnboarding=\(hasSeenOnboarding)")
            if !hasSeenOnboarding {
                DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                    print("[Onboarding] Showing onboarding")
                    showOnboarding = true
                }
            }
        }
    }
}

// MARK: - Saved Parks View (used inside Profile)

struct SavedParksView: View {
    @StateObject private var viewModel = ParksViewModel()
    @State private var savedParksList: [SavedParkResponse] = []
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if savedParksList.isEmpty {
                EmptyStateView(
                    icon: "heart",
                    title: "No Saved Parks",
                    message: "Save parks you want to visit by tapping the heart icon."
                )
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(savedParksList) { saved in
                            NavigationLink(destination: ParkDetailView(parkName: saved.parkName)) {
                                SavedParkCard(saved: saved)
                            }
                        }
                    }
                    .padding()
                }
            }
        }
        .background(Color.appBackground)
        .navigationTitle("Saved Parks")
        .task {
            await loadSaved()
        }
        .refreshable {
            await loadSaved()
        }
    }

    private func loadSaved() async {
        isLoading = true
        do {
            savedParksList = try await APIService.shared.getSavedParks(userId: 1)
        } catch {
            print("Error loading saved parks: \(error)")
        }
        isLoading = false
    }
}

struct SavedParkCard: View {
    let saved: SavedParkResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(saved.parkName)
                        .font(.appSubheadline)
                        .foregroundColor(.appTextPrimary)

                    Text("Saved \(saved.savedAt.formatted(date: .abbreviated, time: .omitted))")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                }

                Spacer()

                if saved.visitCount > 0 {
                    Text("\(saved.visitCount) visits")
                        .font(.appCaption)
                        .foregroundColor(.appPrimary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.appPrimary.opacity(0.1))
                        .cornerRadius(8)
                }
            }

            if let notes = saved.notes, !notes.isEmpty {
                Text(notes)
                    .font(.appCaption)
                    .foregroundColor(.appTextSecondary)
                    .lineLimit(2)
            }

            if !saved.tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(saved.tags, id: \.self) { tag in
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

// MARK: - Profile View (Scout Profile + Saved Parks)

struct ProfileView: View {
    @State private var showOnboarding = false
    @State private var showAuthSheet = false
    @State private var userProfile: UserProfileWithTier?
    @State private var isLoadingProfile = false
    @ObservedObject private var authService = AuthService.shared

    // Inline preferences (no navigation needed)
    @State private var childrenAges: [Int] = []
    @State private var hasDog = false
    @State private var accessibilityNeeds = false
    @State private var preferredDistance: Double = 15
    @State private var notificationsEnabled = true

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Profile Header Card
                VStack(spacing: 16) {
                    HStack(spacing: 16) {
                        Circle()
                            .fill(Color.appPrimary.opacity(0.2))
                            .frame(width: 70, height: 70)
                            .overlay(
                                Image(systemName: authService.isAuthenticated ? "person.fill.checkmark" : "person.fill")
                                    .foregroundColor(.appPrimary)
                                    .font(.system(size: 28))
                            )

                        VStack(alignment: .leading, spacing: 6) {
                            if authService.isAuthenticated {
                                HStack(spacing: 8) {
                                    Text(authService.displayName)
                                        .font(.appTitle2)
                                        .foregroundColor(.appTextPrimary)

                                    if let profile = userProfile {
                                        UserTierBadge(tier: profile.tier, showName: false)
                                    }
                                }

                                Text(authService.currentUser?.email ?? "")
                                    .font(.appCaption)
                                    .foregroundColor(.appTextSecondary)
                            } else {
                                Text("Welcome, Scout!")
                                    .font(.appTitle2)
                                    .foregroundColor(.appTextPrimary)

                                Text("Sign in to track your park adventures")
                                    .font(.appCaption)
                                    .foregroundColor(.appTextSecondary)
                            }
                        }

                        Spacer()
                    }

                    if !authService.isAuthenticated {
                        Button {
                            showAuthSheet = true
                        } label: {
                            HStack {
                                Image(systemName: "person.badge.plus")
                                Text("Sign In / Create Account")
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                        }
                        .buttonStyle(PrimaryButtonStyle())
                    }
                }
                .padding()
                .background(Color.appCard)
                .cornerRadius(16)
                .padding(.horizontal)

                // Scout Rank Card (for authenticated users)
                if authService.isAuthenticated, let profile = userProfile {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Your Scout Rank")
                            .font(.appHeadline)
                            .foregroundColor(.appTextPrimary)

                        TierProgressCard(
                            currentTier: profile.tier,
                            reviewCount: profile.reviewCount
                        )
                    }
                    .padding(.horizontal)
                }

                // Quick Stats (for authenticated users)
                if authService.isAuthenticated, let profile = userProfile {
                    HStack(spacing: 12) {
                        StatCard(
                            icon: "star.fill",
                            value: "\(profile.reviewCount)",
                            label: "Reviews",
                            color: .appSecondary
                        )

                        StatCard(
                            icon: "checkmark.seal.fill",
                            value: "\(profile.badgeConfirmationsCount)",
                            label: "Confirmations",
                            color: .appPrimary
                        )
                    }
                    .padding(.horizontal)
                }

                // Saved Parks link
                NavigationLink(destination: SavedParksView()) {
                    HStack(spacing: 12) {
                        Image(systemName: "bookmark.fill")
                            .font(.system(size: 18))
                            .foregroundColor(.appPrimary)
                            .frame(width: 32)

                        VStack(alignment: .leading, spacing: 2) {
                            Text("Saved Parks")
                                .font(.appBody)
                                .foregroundColor(.appTextPrimary)

                            Text("Parks you want to visit")
                                .font(.appCaption)
                                .foregroundColor(.appTextSecondary)
                        }

                        Spacer()

                        Image(systemName: "chevron.right")
                            .font(.system(size: 14))
                            .foregroundColor(.appTextSecondary)
                    }
                    .padding()
                    .background(Color.appCard)
                    .cornerRadius(16)
                }
                .padding(.horizontal)

                // Preferences Section (inline, no navigation)
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Image(systemName: "slider.horizontal.3")
                            .foregroundColor(.appPrimary)
                        Text("Preferences")
                            .font(.appHeadline)
                            .foregroundColor(.appTextPrimary)
                    }

                    VStack(spacing: 12) {
                        // Children ages
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Children's Ages")
                                .font(.appCaption)
                                .foregroundColor(.appTextSecondary)

                            ForEach(childrenAges.indices, id: \.self) { index in
                                HStack {
                                    Text("Child \(index + 1)")
                                        .font(.appBody)
                                        .foregroundColor(.appTextPrimary)
                                    Spacer()
                                    Stepper("\(childrenAges[index]) years", value: $childrenAges[index], in: 0...18)
                                        .labelsHidden()
                                    Text("\(childrenAges[index]) years")
                                        .font(.appBody)
                                        .foregroundColor(.appTextSecondary)
                                        .frame(width: 60)

                                    Button {
                                        childrenAges.remove(at: index)
                                    } label: {
                                        Image(systemName: "xmark.circle.fill")
                                            .foregroundColor(.gray)
                                    }
                                }
                            }

                            Button {
                                childrenAges.append(5)
                            } label: {
                                HStack {
                                    Image(systemName: "plus.circle.fill")
                                    Text("Add Child")
                                }
                                .font(.appCaption)
                                .foregroundColor(.appPrimary)
                            }
                        }

                        Divider()

                        // Toggles
                        Toggle(isOn: $hasDog) {
                            HStack {
                                Image(systemName: "dog.fill")
                                    .foregroundColor(.appAccent)
                                Text("I have a dog")
                                    .font(.appBody)
                            }
                        }
                        .tint(.appPrimary)

                        Toggle(isOn: $accessibilityNeeds) {
                            HStack {
                                Image(systemName: "figure.roll")
                                    .foregroundColor(.appAccent)
                                Text("Accessibility needs")
                                    .font(.appBody)
                            }
                        }
                        .tint(.appPrimary)

                        Toggle(isOn: $notificationsEnabled) {
                            HStack {
                                Image(systemName: "bell.fill")
                                    .foregroundColor(.appAccent)
                                Text("Notifications")
                                    .font(.appBody)
                            }
                        }
                        .tint(.appPrimary)

                        Divider()

                        // Distance slider
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Image(systemName: "location.circle.fill")
                                    .foregroundColor(.appAccent)
                                Text("Max search distance")
                                    .font(.appBody)
                                Spacer()
                                Text("\(Int(preferredDistance)) miles")
                                    .font(.appBody)
                                    .foregroundColor(.appPrimary)
                                    .fontWeight(.semibold)
                            }
                            Slider(value: $preferredDistance, in: 5...30, step: 5)
                                .tint(.appPrimary)
                        }
                    }
                }
                .padding()
                .background(Color.appCard)
                .cornerRadius(16)
                .padding(.horizontal)

                // Resources Section (inline)
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Image(systemName: "info.circle.fill")
                            .foregroundColor(.appPrimary)
                        Text("Resources")
                            .font(.appHeadline)
                            .foregroundColor(.appTextPrimary)
                    }

                    VStack(spacing: 0) {
                        ResourceRow(
                            icon: "safari.fill",
                            title: "About ParkScout",
                            subtitle: "Learn how to use the app"
                        ) {
                            showOnboarding = true
                        }

                        Divider().padding(.leading, 44)

                        Link(destination: URL(string: "https://www.fairfaxcounty.gov/parks/")!) {
                            ResourceRow(
                                icon: "link",
                                title: "Fairfax County Parks",
                                subtitle: "Official parks website",
                                showChevron: true
                            )
                        }

                        Divider().padding(.leading, 44)

                        Link(destination: URL(string: "https://www.fairfaxcounty.gov/parks/park-alerts")!) {
                            ResourceRow(
                                icon: "exclamationmark.triangle.fill",
                                title: "Park Alerts",
                                subtitle: "Check for closures and updates",
                                showChevron: true
                            )
                        }
                    }
                }
                .padding()
                .background(Color.appCard)
                .cornerRadius(16)
                .padding(.horizontal)

                // Sign Out Button (for authenticated users)
                if authService.isAuthenticated {
                    Button(role: .destructive) {
                        Task {
                            await authService.logout()
                        }
                    } label: {
                        HStack {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                            Text("Sign Out")
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .foregroundColor(.red)
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(12)
                    }
                    .padding(.horizontal)
                }

                // App Version
                Text("ParkScout v1.0")
                    .font(.appCaption)
                    .foregroundColor(.appTextSecondary)
                    .padding(.top, 8)
                    .padding(.bottom, 20)
            }
            .padding(.top)
        }
        .background(Color.appBackground)
        .navigationTitle("Scout Profile")
        .sheet(isPresented: $showOnboarding) {
            OnboardingView()
        }
        .sheet(isPresented: $showAuthSheet) {
            AuthView()
        }
        .task {
            await loadUserProfile()
        }
        .onChange(of: authService.isAuthenticated) { _, isAuthenticated in
            if isAuthenticated {
                Task { await loadUserProfile() }
            } else {
                userProfile = nil
            }
        }
    }

    private func loadUserProfile() async {
        guard authService.isAuthenticated, let userId = authService.userId else { return }
        isLoadingProfile = true
        do {
            userProfile = try await APIService.shared.getUserProfile(userId: userId)
        } catch {
            print("Error loading user profile: \(error)")
        }
        isLoadingProfile = false
    }
}

// MARK: - Supporting Views for Profile

struct StatCard: View {
    let icon: String
    let value: String
    let label: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 24))
                .foregroundColor(color)

            Text(value)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.appTextPrimary)

            Text(label)
                .font(.appCaption)
                .foregroundColor(.appTextSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 16)
        .background(Color.appCard)
        .cornerRadius(12)
    }
}

struct ResourceRow: View {
    let icon: String
    let title: String
    let subtitle: String
    var showChevron: Bool = false
    var action: (() -> Void)? = nil

    var body: some View {
        Button {
            action?()
        } label: {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 18))
                    .foregroundColor(.appPrimary)
                    .frame(width: 32)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.appBody)
                        .foregroundColor(.appTextPrimary)

                    Text(subtitle)
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                }

                Spacer()

                if showChevron {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14))
                        .foregroundColor(.appTextSecondary)
                }
            }
            .padding(.vertical, 12)
        }
        .buttonStyle(.plain)
    }
}


// MARK: - Onboarding View

struct OnboardingView: View {
    @Environment(\.dismiss) var dismiss
    @State private var currentPage = 0
    @State private var dontShowAgain = false
    @Binding var hasSeenOnboarding: Bool
    var onComplete: (() -> Void)? = nil

    init(hasSeenOnboarding: Binding<Bool> = .constant(false), onComplete: (() -> Void)? = nil) {
        self._hasSeenOnboarding = hasSeenOnboarding
        self.onComplete = onComplete
    }

    let pages: [(icon: String, title: String, description: String)] = [
        ("tree.fill", "Discover Parks", "Browse 400+ Fairfax County parks with parent-verified amenity data, ratings, and Parent Scores."),
        ("map.fill", "Explore Nearby", "See parks on the map sorted by distance from you. Filter by playground, restrooms, trails, and more."),
        ("safari.fill", "Spin to Discover", "Can't decide? Spin the Park Picker wheel for a fun adventure suggestion!"),
        ("bubble.left.and.bubble.right.fill", "Ask the Scout AI", "Chat with our AI guide to find the perfect park for your family using natural language."),
        ("star.fill", "Rate & Review", "Help other parents by sharing your park experience. Earn Scout Badges and rank up!")
    ]

    var body: some View {
        VStack {
            // Skip button
            HStack {
                Spacer()
                Button {
                    if dontShowAgain { hasSeenOnboarding = true }
                    onComplete?()
                    dismiss()
                } label: {
                    Text("Skip")
                        .font(.appBody)
                        .foregroundColor(.appTextSecondary)
                }
                .padding()
            }

            TabView(selection: $currentPage) {
                ForEach(0..<pages.count, id: \.self) { index in
                    VStack(spacing: 32) {
                        Spacer()

                        Image(systemName: pages[index].icon)
                            .font(.system(size: 80))
                            .foregroundColor(.appPrimary)

                        VStack(spacing: 12) {
                            Text(pages[index].title)
                                .font(.appTitle)
                                .foregroundColor(.appTextPrimary)

                            Text(pages[index].description)
                                .font(.appBody)
                                .foregroundColor(.appTextSecondary)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 40)
                        }

                        Spacer()
                    }
                    .tag(index)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .always))

            // Don't show again toggle
            Toggle(isOn: $dontShowAgain) {
                Text("Don't show this again")
                    .font(.appCaption)
                    .foregroundColor(.appTextSecondary)
            }
            .tint(.appPrimary)
            .padding(.horizontal)

            Button {
                if currentPage < pages.count - 1 {
                    withAnimation {
                        currentPage += 1
                    }
                } else {
                    if dontShowAgain { hasSeenOnboarding = true }
                    onComplete?()
                    dismiss()
                }
            } label: {
                Text(currentPage < pages.count - 1 ? "Next" : "Get Started")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(PrimaryButtonStyle())
            .padding()
        }
        .background(Color.appBackground)
    }
}

// MARK: - Empty State View

struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 64))
                .foregroundColor(.gray.opacity(0.5))

            Text(title)
                .font(.appHeadline)
                .foregroundColor(.appTextPrimary)

            Text(message)
                .font(.appBody)
                .foregroundColor(.appTextSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
        }
    }
}

#Preview {
    ContentView()
}
