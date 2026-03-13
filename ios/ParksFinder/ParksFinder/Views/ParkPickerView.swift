import SwiftUI

// MARK: - Park Picker View (Roulette Wheel)
struct ParkPickerView: View {
    @StateObject private var viewModel = ParkPickerViewModel()
    @State private var showingParkDetail = false

    var body: some View {
        ZStack {
            Color.appBackground.ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                VStack(spacing: 8) {
                    Text("Park Picker")
                        .font(.appTitle)
                        .foregroundColor(.appTextPrimary)

                    Text("Spin the wheel for a fun adventure!")
                        .font(.appBody)
                        .foregroundColor(.appTextSecondary)
                }
                .padding(.top, 20)
                .padding(.bottom, 10)

                // Filter chips
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(ParkPickerFilter.allCases, id: \.self) { filter in
                            PickerFilterChip(
                                title: filter.label,
                                icon: filter.icon,
                                isSelected: viewModel.selectedFilter == filter
                            ) {
                                viewModel.selectFilter(filter)
                            }
                        }
                    }
                    .padding(.horizontal)
                }
                .padding(.vertical, 16)

                Spacer()

                // Wheel
                ZStack {
                    // Pointer at top
                    VStack {
                        Image(systemName: "arrowtriangle.down.fill")
                            .font(.system(size: 32))
                            .foregroundColor(.appPrimary)
                            .shadow(color: .black.opacity(0.2), radius: 2, x: 0, y: 2)
                        Spacer()
                    }
                    .zIndex(1)

                    // The wheel
                    SpinWheel(
                        parks: viewModel.filteredParks,
                        rotation: viewModel.rotation,
                        isSpinning: viewModel.isSpinning
                    )
                    .frame(width: 300, height: 300)
                }
                .frame(height: 340)

                Spacer()

                // Result or Spin button
                VStack(spacing: 16) {
                    if let selectedPark = viewModel.selectedPark, !viewModel.isSpinning {
                        // Show selected park
                        VStack(spacing: 12) {
                            Text("Your Adventure:")
                                .font(.appCaption)
                                .foregroundColor(.appTextSecondary)

                            Text(selectedPark.parkName)
                                .font(.appHeadline)
                                .foregroundColor(.appTextPrimary)
                                .multilineTextAlignment(.center)

                            if !selectedPark.amenities.specialFeatures.isEmpty {
                                HStack(spacing: 8) {
                                    ForEach(selectedPark.amenities.specialFeatures.prefix(3), id: \.self) { feature in
                                        Text(feature)
                                            .font(.system(size: 11))
                                            .foregroundColor(.appSecondary)
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 4)
                                            .background(Color.appSecondary.opacity(0.15))
                                            .cornerRadius(8)
                                    }
                                }
                            }

                            Button {
                                showingParkDetail = true
                            } label: {
                                Text("View Park Details")
                                    .font(.appSubheadline)
                            }
                            .buttonStyle(PrimaryButtonStyle())
                            .padding(.horizontal, 40)
                        }
                        .padding()
                        .background(Color.appCard)
                        .cornerRadius(16)
                        .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 4)
                        .padding(.horizontal)
                        .transition(.scale.combined(with: .opacity))
                    }

                    // Spin button
                    Button {
                        viewModel.spin()
                    } label: {
                        HStack(spacing: 8) {
                            if viewModel.isSpinning {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Image(systemName: "arrow.triangle.2.circlepath")
                            }
                            Text(viewModel.isSpinning ? "Spinning..." : "Spin the Wheel!")
                        }
                        .font(.appHeadline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(
                            LinearGradient(
                                colors: [Color.appPrimary, Color.appSecondary],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .cornerRadius(16)
                    }
                    .disabled(viewModel.isSpinning || viewModel.filteredParks.isEmpty)
                    .opacity(viewModel.filteredParks.isEmpty ? 0.5 : 1)
                    .padding(.horizontal)
                }
                .padding(.bottom, 30)
            }
        }
        .navigationTitle("")
        .navigationBarHidden(true)
        .sheet(isPresented: $showingParkDetail) {
            if let park = viewModel.selectedPark {
                NavigationStack {
                    ParkDetailView(parkName: park.parkName, showCloseButton: true)
                }
            }
        }
        .task {
            await viewModel.loadParks()
        }
    }
}

// MARK: - Picker Filter Chip (renamed to avoid conflict with DesignSystem.FilterChip)
struct PickerFilterChip: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 12))
                Text(title)
                    .font(.appCaption)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(isSelected ? Color.appPrimary : Color.appCard)
            .foregroundColor(isSelected ? .white : .appTextPrimary)
            .cornerRadius(20)
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .stroke(isSelected ? Color.clear : Color.gray.opacity(0.3), lineWidth: 1)
            )
        }
    }
}

// MARK: - Spin Wheel
struct SpinWheel: View {
    let parks: [Park]
    let rotation: Double
    let isSpinning: Bool

    private let colors: [Color] = [
        .appPrimary,
        .appSecondary,
        .orange,
        .pink,
        .purple,
        .cyan,
        .mint,
        .indigo
    ]

    var body: some View {
        GeometryReader { geometry in
            let size = min(geometry.size.width, geometry.size.height)
            let center = CGPoint(x: size / 2, y: size / 2)
            let radius = size / 2

            ZStack {
                // Wheel segments
                if parks.isEmpty {
                    // Empty state
                    Circle()
                        .fill(Color.gray.opacity(0.2))

                    Text("No parks found")
                        .font(.appCaption)
                        .foregroundColor(.appTextSecondary)
                } else {
                    ForEach(0..<min(parks.count, 8), id: \.self) { index in
                        WheelSegment(
                            index: index,
                            total: min(parks.count, 8),
                            color: colors[index % colors.count],
                            parkName: parks[index].parkName,
                            center: center,
                            radius: radius
                        )
                    }
                }

                // Center circle
                Circle()
                    .fill(Color.white)
                    .frame(width: 60, height: 60)
                    .shadow(color: .black.opacity(0.15), radius: 4, x: 0, y: 2)

                // Center icon
                Image(systemName: "leaf.fill")
                    .font(.system(size: 24))
                    .foregroundColor(.appPrimary)
            }
            .rotationEffect(.degrees(rotation))
            .animation(
                isSpinning ? .easeOut(duration: 3.0) : .none,
                value: rotation
            )
        }
    }
}

// MARK: - Wheel Segment
struct WheelSegment: View {
    let index: Int
    let total: Int
    let color: Color
    let parkName: String
    let center: CGPoint
    let radius: CGFloat

    var body: some View {
        let anglePerSegment = 360.0 / Double(total)
        let startAngle = Double(index) * anglePerSegment - 90 // Start from top
        let endAngle = startAngle + anglePerSegment

        ZStack {
            // Segment path
            Path { path in
                path.move(to: center)
                path.addArc(
                    center: center,
                    radius: radius,
                    startAngle: .degrees(startAngle),
                    endAngle: .degrees(endAngle),
                    clockwise: false
                )
                path.closeSubpath()
            }
            .fill(color)
            .overlay(
                Path { path in
                    path.move(to: center)
                    path.addArc(
                        center: center,
                        radius: radius,
                        startAngle: .degrees(startAngle),
                        endAngle: .degrees(endAngle),
                        clockwise: false
                    )
                    path.closeSubpath()
                }
                .stroke(Color.white, lineWidth: 2)
            )

            // Park name label
            let midAngle = (startAngle + endAngle) / 2
            let labelRadius = radius * 0.6
            let labelX = center.x + labelRadius * cos(midAngle * .pi / 180)
            let labelY = center.y + labelRadius * sin(midAngle * .pi / 180)

            Text(abbreviateParkName(parkName))
                .font(.system(size: 10, weight: .semibold))
                .foregroundColor(.white)
                .shadow(color: .black.opacity(0.3), radius: 1, x: 0, y: 1)
                .rotationEffect(.degrees(midAngle + 90))
                .position(x: labelX, y: labelY)
        }
    }

    private func abbreviateParkName(_ name: String) -> String {
        let words = name.components(separatedBy: " ")
        if words.count > 2 {
            return words.prefix(2).joined(separator: " ")
        }
        return name
    }
}

// MARK: - Filter Enum
enum ParkPickerFilter: CaseIterable {
    case all
    case carousel
    case waterPlay
    case natureTrails
    case playgrounds
    case dogParks

    var label: String {
        switch self {
        case .all: return "All Special"
        case .carousel: return "Carousels"
        case .waterPlay: return "Water Play"
        case .natureTrails: return "Nature Trails"
        case .playgrounds: return "Playgrounds"
        case .dogParks: return "Dog Parks"
        }
    }

    var icon: String {
        switch self {
        case .all: return "sparkles"
        case .carousel: return "circle.dotted"
        case .waterPlay: return "drop.fill"
        case .natureTrails: return "leaf.fill"
        case .playgrounds: return "figure.play"
        case .dogParks: return "dog.fill"
        }
    }
}

// MARK: - View Model
@MainActor
class ParkPickerViewModel: ObservableObject {
    @Published var allParks: [Park] = []
    @Published var filteredParks: [Park] = []
    @Published var selectedFilter: ParkPickerFilter = .all
    @Published var rotation: Double = 0
    @Published var isSpinning = false
    @Published var selectedPark: Park?

    func loadParks() async {
        do {
            let response = try await APIService.shared.listParks(limit: 200)
            allParks = response.parks
        } catch {
            // Fall back to demo data when server is unavailable
            print("Server unavailable for Park Picker, using demo data: \(error)")
            allParks = DemoData.parks
        }
        applyFilter()
    }

    func selectFilter(_ filter: ParkPickerFilter) {
        selectedFilter = filter
        applyFilter()
        selectedPark = nil
    }

    private func applyFilter() {
        switch selectedFilter {
        case .all:
            // Parks with any special features
            filteredParks = allParks.filter { !$0.amenities.specialFeatures.isEmpty }
        case .carousel:
            filteredParks = allParks.filter { park in
                park.amenities.specialFeatures.contains { $0.lowercased().contains("carousel") }
            }
        case .waterPlay:
            filteredParks = allParks.filter { park in
                park.amenities.waterActivities != "None" ||
                park.amenities.specialFeatures.contains {
                    $0.lowercased().contains("water") ||
                    $0.lowercased().contains("splash") ||
                    $0.lowercased().contains("spray")
                }
            }
        case .natureTrails:
            filteredParks = allParks.filter { park in
                park.amenities.hasTrails ||
                park.amenities.specialFeatures.contains {
                    $0.lowercased().contains("trail") ||
                    $0.lowercased().contains("nature")
                }
            }
        case .playgrounds:
            filteredParks = allParks.filter { $0.amenities.hasPlayground }
        case .dogParks:
            filteredParks = allParks.filter { $0.amenities.isDogFriendly }
        }

        // Shuffle for variety
        filteredParks.shuffle()
    }

    func spin() {
        guard !filteredParks.isEmpty else { return }

        isSpinning = true
        selectedPark = nil

        // Random number of full rotations (3-5) plus random segment
        let fullRotations = Double.random(in: 3...5) * 360
        let segmentAngle = 360.0 / Double(min(filteredParks.count, 8))
        let randomSegment = Double(Int.random(in: 0..<min(filteredParks.count, 8)))
        let targetRotation = fullRotations + (randomSegment * segmentAngle) + Double.random(in: 0..<segmentAngle)

        // Calculate which park will be selected (at the top, 0 degrees)
        let normalizedAngle = targetRotation.truncatingRemainder(dividingBy: 360)
        let selectedIndex = Int((360 - normalizedAngle) / segmentAngle) % min(filteredParks.count, 8)

        rotation += targetRotation

        // After animation completes, show result
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.2) {
            self.isSpinning = false
            if selectedIndex < self.filteredParks.count {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    self.selectedPark = self.filteredParks[selectedIndex]
                }
            }
        }
    }
}

#Preview {
    NavigationStack {
        ParkPickerView()
    }
}
