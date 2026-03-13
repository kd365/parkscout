import SwiftUI

struct ChatView: View {
    @StateObject private var viewModel = ChatViewModel()
    @State private var weather: WeatherResponseModel?
    @State private var isLoadingWeather = false
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Weather badge (collapsible)
            if let weather = weather {
                WeatherBadgeView(weather: weather, onQueryTap: { query in
                    viewModel.inputText = query
                    Task { await viewModel.sendMessage() }
                })
            }

            // Chat messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        // Quick suggestions at the start (weather-aware)
                        if viewModel.messages.count <= 1 {
                            QuickSuggestionsView(viewModel: viewModel, weather: weather)
                        }

                        ForEach(viewModel.messages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }
                    }
                    .padding()
                }
                .onChange(of: viewModel.messages.count) { _, _ in
                    if let lastMessage = viewModel.messages.last {
                        withAnimation {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            // Input area
            ChatInputBar(
                text: $viewModel.inputText,
                isLoading: viewModel.isLoading,
                onSend: {
                    Task { await viewModel.sendMessage() }
                }
            )
            .focused($isInputFocused)
        }
        .background(Color.appBackground)
        .navigationTitle("ParkScout")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    Task { await viewModel.clearConversation() }
                } label: {
                    Image(systemName: "arrow.counterclockwise")
                        .foregroundColor(.appPrimary)
                }
            }
        }
        .task {
            await loadWeather()
        }
    }

    private func loadWeather() async {
        isLoadingWeather = true
        do {
            weather = try await APIService.shared.getCurrentWeather()
        } catch {
            print("Failed to load weather: \(error)")
            // Weather is optional - continue without it
        }
        isLoadingWeather = false
    }
}

// MARK: - Weather Badge View

struct WeatherBadgeView: View {
    let weather: WeatherResponseModel
    let onQueryTap: (String) -> Void
    @State private var isExpanded = false

    var body: some View {
        VStack(spacing: 0) {
            // Compact badge (always visible)
            Button {
                withAnimation(.spring(response: 0.3)) {
                    isExpanded.toggle()
                }
            } label: {
                HStack(spacing: 10) {
                    Image(systemName: weather.conditionIcon)
                        .font(.system(size: 20))
                        .foregroundColor(iconColor)

                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(Int(weather.temperatureF))°F")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(.appTextPrimary)

                        Text(weather.conditionDisplayName)
                            .font(.system(size: 12))
                            .foregroundColor(.appTextSecondary)
                    }

                    Spacer()

                    Text(weather.momTip)
                        .font(.system(size: 12))
                        .foregroundColor(.appTextSecondary)
                        .lineLimit(1)
                        .frame(maxWidth: 150, alignment: .trailing)

                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.system(size: 12))
                        .foregroundColor(.appTextSecondary)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Color.appCard)
            }

            // Expanded suggestions
            if isExpanded {
                VStack(alignment: .leading, spacing: 8) {
                    if !weather.suggestedActivities.isEmpty {
                        HStack(spacing: 6) {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                                .font(.system(size: 12))
                            Text("Great for: \(weather.suggestedActivities.prefix(2).joined(separator: ", "))")
                                .font(.system(size: 12))
                                .foregroundColor(.appTextSecondary)
                        }
                    }

                    if !weather.thingsToAvoid.isEmpty {
                        HStack(spacing: 6) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.orange)
                                .font(.system(size: 12))
                            Text("Avoid: \(weather.thingsToAvoid.prefix(2).joined(separator: ", "))")
                                .font(.system(size: 12))
                                .foregroundColor(.appTextSecondary)
                        }
                    }

                    // Quick weather-based queries
                    if !weather.suggestedQueries.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(weather.suggestedQueries.prefix(3), id: \.self) { query in
                                    Button {
                                        onQueryTap(query)
                                    } label: {
                                        Text(query)
                                            .font(.system(size: 11))
                                            .foregroundColor(.appPrimary)
                                            .padding(.horizontal, 10)
                                            .padding(.vertical, 6)
                                            .background(Color.appPrimary.opacity(0.1))
                                            .cornerRadius(12)
                                    }
                                }
                            }
                        }
                        .padding(.top, 4)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 12)
                .background(Color.appCard)
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    private var iconColor: Color {
        switch weather.condition {
        case "sunny": return .yellow
        case "partly_cloudy": return .orange
        case "cloudy": return .gray
        case "rainy", "stormy": return .blue
        case "snowy": return .cyan
        case "foggy": return .gray
        default: return .gray
        }
    }
}

// MARK: - Message Bubble

struct MessageBubble: View {
    let message: ChatMessage

    var isUser: Bool { message.role == .user }

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if isUser { Spacer(minLength: 60) }

            if !isUser {
                // AI avatar
                Circle()
                    .fill(Color.appPrimary)
                    .frame(width: 32, height: 32)
                    .overlay(
                        Image(systemName: "leaf.fill")
                            .foregroundColor(.white)
                            .font(.system(size: 14))
                    )
            }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 6) {
                if message.isLoading {
                    LoadingDots()
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .background(Color.appCard)
                        .cornerRadius(16)
                } else {
                    Text(message.content)
                        .font(.appBody)
                        .foregroundColor(isUser ? .white : .appTextPrimary)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .background(isUser ? Color.appPrimary : Color.appCard)
                        .cornerRadius(16)

                    // Park mentions
                    if !message.parksMentioned.isEmpty {
                        ParkMentionsRow(parks: message.parksMentioned)
                    }
                }
            }

            if !isUser { Spacer(minLength: 60) }
        }
    }
}

// MARK: - Park Mentions Row

struct ParkMentionsRow: View {
    let parks: [ParkMention]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(parks) { park in
                    NavigationLink(destination: ParkDetailView(parkName: park.name)) {
                        HStack(spacing: 4) {
                            Image(systemName: "mappin.circle.fill")
                                .foregroundColor(.appSecondary)
                            Text(park.name)
                                .font(.appCaption)
                                .foregroundColor(.appPrimary)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Color.appPrimary.opacity(0.1))
                        .cornerRadius(12)
                    }
                }
            }
        }
    }
}

// MARK: - Quick Suggestions

struct QuickSuggestionsView: View {
    @ObservedObject var viewModel: ChatViewModel
    var weather: WeatherResponseModel?

    let columns = [
        GridItem(.flexible()),
        GridItem(.flexible())
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Try asking about:")
                .font(.appSubheadline)
                .foregroundColor(.appTextSecondary)

            LazyVGrid(columns: columns, spacing: 10) {
                ForEach(effectiveSuggestions) { suggestion in
                    Button {
                        Task { await viewModel.useSuggestion(suggestion) }
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: suggestion.icon)
                                .foregroundColor(.appPrimary)
                                .font(.system(size: 16))

                            Text(suggestion.title)
                                .font(.appCaption)
                                .foregroundColor(.appTextPrimary)

                            Spacer()
                        }
                        .padding(12)
                        .background(Color.appCard)
                        .cornerRadius(12)
                    }
                }
            }
        }
        .padding(.vertical)
    }

    // Weather-aware suggestions
    private var effectiveSuggestions: [QuickSuggestion] {
        guard let weather = weather else {
            return QuickSuggestion.suggestions
        }

        // Customize suggestions based on weather
        var suggestions: [QuickSuggestion] = []

        if weather.temperatureF >= 85 {
            // Hot weather suggestions
            suggestions.append(QuickSuggestion(
                icon: "drop.fill",
                title: "Splash pads",
                query: "Find me a splash pad or water play area"
            ))
            suggestions.append(QuickSuggestion(
                icon: "leaf.fill",
                title: "Shaded playgrounds",
                query: "Which playgrounds have the best shade?"
            ))
        } else if weather.condition == "rainy" || weather.condition == "stormy" {
            // Rainy weather suggestions
            suggestions.append(QuickSuggestion(
                icon: "building.fill",
                title: "Indoor options",
                query: "What indoor play areas are nearby?"
            ))
            suggestions.append(QuickSuggestion(
                icon: "umbrella.fill",
                title: "Covered pavilions",
                query: "Parks with covered pavilions"
            ))
        } else if weather.temperatureF < 50 {
            // Cold weather suggestions
            suggestions.append(QuickSuggestion(
                icon: "toilet.fill",
                title: "Near restrooms",
                query: "Playgrounds with restrooms nearby for quick visits"
            ))
            suggestions.append(QuickSuggestion(
                icon: "building.2.fill",
                title: "Nature centers",
                query: "Nature centers with indoor exhibits"
            ))
        }

        // Always include some general suggestions
        suggestions.append(contentsOf: QuickSuggestion.suggestions.prefix(4 - suggestions.count))

        return Array(suggestions.prefix(4))
    }
}

// MARK: - Chat Input Bar

struct ChatInputBar: View {
    @Binding var text: String
    let isLoading: Bool
    let onSend: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            TextField("Ask about parks...", text: $text, axis: .vertical)
                .textFieldStyle(.plain)
                .padding(12)
                .background(Color.appCard)
                .cornerRadius(20)
                .lineLimit(1...4)

            Button(action: onSend) {
                Image(systemName: isLoading ? "hourglass" : "arrow.up.circle.fill")
                    .font(.system(size: 32))
                    .foregroundColor(text.isEmpty || isLoading ? .gray : .appPrimary)
            }
            .disabled(text.isEmpty || isLoading)
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color.appBackground)
    }
}

#Preview {
    NavigationStack {
        ChatView()
    }
}
