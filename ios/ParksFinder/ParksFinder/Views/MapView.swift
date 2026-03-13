import SwiftUI
import MapKit

struct MapView: View {
    @StateObject private var viewModel = ParksViewModel()
    @StateObject private var locationService = LocationService.shared

    // Default to Fairfax County center
    private static let fairfaxCenter = CLLocationCoordinate2D(latitude: 38.8462, longitude: -77.3064)

    @State private var region = MKCoordinateRegion(
        center: fairfaxCenter,
        span: MKCoordinateSpan(latitudeDelta: 0.15, longitudeDelta: 0.15)
    )
    @State private var selectedPark: Park?
    @State private var showParkDetail = false
    @State private var searchText = ""
    @State private var isSearching = false

    var body: some View {
        ZStack(alignment: .bottom) {
            // Map
            Map(coordinateRegion: $region, showsUserLocation: true, annotationItems: parkAnnotations) { annotation in
                MapAnnotation(coordinate: annotation.coordinate) {
                    ParkMarker(park: annotation.park, isSelected: selectedPark?.id == annotation.park.id)
                        .onTapGesture {
                            withAnimation(.spring()) {
                                selectedPark = annotation.park
                            }
                        }
                }
            }
            .ignoresSafeArea(edges: .top)

            // Search bar and filter chips at top
            VStack(spacing: 0) {
                // Search bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.gray)
                    TextField("Search parks or addresses...", text: $searchText)
                        .textFieldStyle(.plain)
                        .submitLabel(.search)
                        .onSubmit {
                            searchAddress()
                        }
                    if !searchText.isEmpty {
                        Button {
                            searchAddress()
                        } label: {
                            Image(systemName: "arrow.right.circle.fill")
                                .foregroundColor(.appPrimary)
                        }
                        Button {
                            searchText = ""
                            selectedPark = nil
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.gray)
                        }
                    }
                }
                .padding(12)
                .background(Color.appCard)
                .cornerRadius(10)
                .padding(.horizontal)
                .padding(.top, 8)

                // Filter chips
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        FilterChip(title: "Playground", isSelected: viewModel.filterPlayground == true) {
                            viewModel.filterPlayground = viewModel.filterPlayground == true ? nil : true
                            Task { await viewModel.loadParks() }
                        }
                        FilterChip(title: "Dog-Friendly", isSelected: viewModel.filterDogFriendly == true) {
                            viewModel.filterDogFriendly = viewModel.filterDogFriendly == true ? nil : true
                            Task { await viewModel.loadParks() }
                        }
                        FilterChip(title: "Trails", isSelected: viewModel.filterTrails == true) {
                            viewModel.filterTrails = viewModel.filterTrails == true ? nil : true
                            Task { await viewModel.loadParks() }
                        }
                    }
                    .padding(.horizontal)
                }
                .padding(.vertical, 12)

                Spacer()
            }
            .background(
                VStack {
                    Color.appCard.opacity(0.95)
                        .frame(height: 120)
                    Spacer()
                }
            )

            // Selected park card
            if let park = selectedPark {
                VStack {
                    ParkMapCard(park: park) {
                        showParkDetail = true
                    }
                    .padding()
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }

            // Center on user button
            VStack {
                Spacer()
                HStack {
                    Spacer()
                    Button {
                        centerOnUser()
                    } label: {
                        Image(systemName: "location.fill")
                            .font(.system(size: 20))
                            .foregroundColor(.appPrimary)
                            .padding(12)
                            .background(Color.appCard)
                            .clipShape(Circle())
                            .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
                    }
                    .padding(.trailing)
                    .padding(.bottom, selectedPark != nil ? 180 : 20)
                }
            }
        }
        .navigationTitle("Map")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadParks()
            centerOnUser()
        }
        .sheet(isPresented: $showParkDetail) {
            if let park = selectedPark {
                NavigationStack {
                    ParkDetailView(parkName: park.parkName, showCloseButton: true)
                }
            }
        }
    }

    // Convert parks to map annotations - uses coordinates from API
    var parkAnnotations: [ParkAnnotation] {
        return viewModel.parks.compactMap { park in
            // Use coordinates from API if available
            if let coord = park.coordinate {
                return ParkAnnotation(park: park, coordinate: coord)
            }
            // Skip parks without coordinates
            return nil
        }
    }

    private func centerOnUser() {
        if let location = locationService.currentLocation {
            // Check if location is in/near Fairfax County area (not default SF)
            let isNearFairfax = location.latitude > 38.5 && location.latitude < 39.2 &&
                                location.longitude > -77.6 && location.longitude < -77.0
            if isNearFairfax {
                withAnimation {
                    region.center = location
                }
            }
            // Otherwise keep Fairfax default
        }
    }

    private func searchAddress() {
        guard !searchText.isEmpty else { return }

        // First, search parks by name
        let query = searchText.lowercased()
        print("[MapSearch] Searching for '\(query)' in \(viewModel.parks.count) parks")
        if let matchedPark = viewModel.parks.first(where: {
            $0.parkName.lowercased().contains(query)
        }) {
            print("[MapSearch] Found park: \(matchedPark.parkName), coordinate: \(String(describing: matchedPark.coordinate))")
            if let coord = matchedPark.coordinate {
                selectedPark = matchedPark
                withAnimation {
                    region = MKCoordinateRegion(
                        center: coord,
                        span: MKCoordinateSpan(latitudeDelta: 0.02, longitudeDelta: 0.02)
                    )
                }
                return
            }
        } else {
            print("[MapSearch] No park name match found")
        }

        // Fall back to address geocoding
        let geocoder = CLGeocoder()
        let searchQuery = searchText.contains("VA") || searchText.contains("Virginia")
            ? searchText
            : "\(searchText), Fairfax County, VA"

        geocoder.geocodeAddressString(searchQuery) { placemarks, error in
            if let placemark = placemarks?.first,
               let location = placemark.location {
                withAnimation {
                    region.center = location.coordinate
                    region.span = MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05)
                }
            }
        }
    }
}

// MARK: - Park Annotation

struct ParkAnnotation: Identifiable {
    var id: String { park.id }
    let park: Park
    let coordinate: CLLocationCoordinate2D
}

// MARK: - Park Marker

struct ParkMarker: View {
    let park: Park
    let isSelected: Bool

    var markerColor: Color {
        switch park.distanceCategory {
        case .near: return .green
        case .moderate: return .orange
        case .driveable: return .gray
        case .none: return .appPrimary
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            ZStack {
                Circle()
                    .fill(isSelected ? Color.appSecondary : markerColor)
                    .frame(width: isSelected ? 44 : 32, height: isSelected ? 44 : 32)

                Image(systemName: markerIcon)
                    .foregroundColor(.white)
                    .font(.system(size: isSelected ? 18 : 14))
            }
            .shadow(color: .black.opacity(0.2), radius: 2, x: 0, y: 2)

            // Triangle pointer
            Triangle()
                .fill(isSelected ? Color.appSecondary : markerColor)
                .frame(width: 12, height: 8)
                .offset(y: -2)
        }
        .animation(.spring(response: 0.3), value: isSelected)
    }

    var markerIcon: String {
        if park.amenities.hasPlayground { return "figure.play" }
        if park.amenities.isDogFriendly { return "dog" }
        if park.amenities.hasTrails { return "figure.hiking" }
        return "leaf.fill"
    }
}

struct Triangle: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.midX, y: rect.maxY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY))
        path.closeSubpath()
        return path
    }
}

// MARK: - Park Map Card

struct ParkMapCard: View {
    let park: Park
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(park.parkName)
                            .font(.appSubheadline)
                            .foregroundColor(.appTextPrimary)

                        if let classification = park.classification {
                            Text(classification)
                                .font(.appCaption)
                                .foregroundColor(.appTextSecondary)
                        }
                    }

                    Spacer()

                    if let category = park.distanceCategory, let minutes = park.driveTimeMinutes {
                        DistanceBadge(category: category, minutes: minutes)
                    }
                }

                // Quick amenities
                HStack(spacing: 16) {
                    if park.amenities.hasPlayground {
                        Label("Playground", systemImage: "figure.play")
                            .font(.appCaption)
                            .foregroundColor(.appPrimary)
                    }
                    if park.amenities.isDogFriendly {
                        Label("Dog-Friendly", systemImage: "dog")
                            .font(.appCaption)
                            .foregroundColor(.appPrimary)
                    }
                    if park.amenities.hasTrails {
                        Label("Trails", systemImage: "figure.hiking")
                            .font(.appCaption)
                            .foregroundColor(.appPrimary)
                    }
                }

                // View details button
                HStack {
                    Spacer()
                    Text("View Details")
                        .font(.appCaption)
                        .foregroundColor(.appPrimary)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12))
                        .foregroundColor(.appPrimary)
                }
            }
            .padding()
            .background(Color.appCard)
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.15), radius: 8, x: 0, y: 4)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    NavigationStack {
        MapView()
    }
}
