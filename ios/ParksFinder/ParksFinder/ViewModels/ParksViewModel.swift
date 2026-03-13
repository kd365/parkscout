import Foundation
import CoreLocation

@MainActor
class ParksViewModel: ObservableObject {
    @Published var parks: [Park] = []
    @Published var savedParks: Set<String> = []
    @Published var isLoading: Bool = false
    @Published var error: String?

    // Filters
    @Published var filterPlayground: Bool? = nil
    @Published var filterDogFriendly: Bool? = nil
    @Published var filterRestrooms: Bool? = nil
    @Published var filterTrails: Bool? = nil

    private let apiService = APIService.shared
    private let locationService = LocationService.shared
    private var userId: Int?

    // MARK: - Computed Properties

    var nearbyParks: [Park] {
        parks.filter { $0.distanceCategory == .near }
    }

    var moderateParks: [Park] {
        parks.filter { $0.distanceCategory == .moderate }
    }

    var driveableParks: [Park] {
        parks.filter { $0.distanceCategory == .driveable }
    }

    var hasActiveFilters: Bool {
        filterPlayground != nil ||
        filterDogFriendly != nil ||
        filterRestrooms != nil ||
        filterTrails != nil
    }

    // MARK: - Data Loading

    func loadParks() async {
        isLoading = true
        error = nil

        do {
            let response = try await apiService.listParks(
                playground: filterPlayground,
                dogFriendly: filterDogFriendly,
                restrooms: filterRestrooms,
                trails: filterTrails
            )

            // Add distance calculations
            var parksWithDistance = response.parks
            if let location = locationService.currentLocation {
                parksWithDistance = parksWithDistance.map { park in
                    var p = park
                    // For now, use mock coordinates - in production, parks would have real coordinates
                    // This is a placeholder until we integrate real park coordinates
                    if let distance = calculateMockDistance(for: park.parkName, from: location) {
                        p.distanceMiles = distance
                        let driveTime = locationService.estimateDriveTime(distanceMiles: distance)
                        p.driveTimeMinutes = driveTime
                        p.distanceCategory = locationService.distanceCategory(driveTimeMinutes: driveTime)
                    }
                    p.isSaved = savedParks.contains(park.parkName)
                    return p
                }

                // Sort by distance
                parksWithDistance.sort { ($0.distanceMiles ?? 999) < ($1.distanceMiles ?? 999) }
            }

            parks = parksWithDistance

        } catch {
            // Fall back to demo data when server is unavailable
            print("Server unavailable, using demo data: \(error)")
            var demoParks = DemoData.parks

            // Apply filters to demo data
            if filterPlayground == true {
                demoParks = demoParks.filter { $0.amenities.hasPlayground }
            }
            if filterDogFriendly == true {
                demoParks = demoParks.filter { $0.amenities.isDogFriendly }
            }
            if filterRestrooms == true {
                demoParks = demoParks.filter { $0.amenities.hasRestrooms }
            }
            if filterTrails == true {
                demoParks = demoParks.filter { $0.amenities.hasTrails }
            }

            // Add distance calculations to demo data
            if let location = locationService.currentLocation {
                demoParks = demoParks.map { park in
                    var p = park
                    if let lat = park.latitude, let lng = park.longitude,
                       let distance = locationService.distanceToLocation(lat: lat, lng: lng) {
                        p.distanceMiles = distance
                        let driveTime = locationService.estimateDriveTime(distanceMiles: distance)
                        p.driveTimeMinutes = driveTime
                        p.distanceCategory = locationService.distanceCategory(driveTimeMinutes: driveTime)
                    }
                    return p
                }
                demoParks.sort { ($0.distanceMiles ?? 999) < ($1.distanceMiles ?? 999) }
            }

            parks = demoParks
            self.error = nil  // Don't show error when demo data is available
        }

        isLoading = false
    }

    func loadSavedParks() async {
        guard let userId = userId else { return }

        do {
            let saved = try await apiService.getSavedParks(userId: userId)
            savedParks = Set(saved.map { $0.parkName })

            // Update saved status in parks list
            parks = parks.map { park in
                var p = park
                p.isSaved = savedParks.contains(park.parkName)
                return p
            }
        } catch {
            print("Error loading saved parks: \(error)")
        }
    }

    // MARK: - Actions

    func toggleSaved(park: Park) async {
        guard let userId = userId else { return }

        if savedParks.contains(park.parkName) {
            // Remove from saved
            do {
                try await apiService.unsavePark(userId: userId, parkName: park.parkName)
                savedParks.remove(park.parkName)
                updateParkSavedStatus(parkName: park.parkName, isSaved: false)
            } catch {
                self.error = "Failed to unsave park"
            }
        } else {
            // Add to saved
            do {
                _ = try await apiService.savePark(
                    userId: userId,
                    parkName: park.parkName,
                    notes: nil,
                    tags: []
                )
                savedParks.insert(park.parkName)
                updateParkSavedStatus(parkName: park.parkName, isSaved: true)
            } catch {
                self.error = "Failed to save park"
            }
        }
    }

    func clearFilters() {
        filterPlayground = nil
        filterDogFriendly = nil
        filterRestrooms = nil
        filterTrails = nil
    }

    func setUser(id: Int) {
        userId = id
    }

    // MARK: - Private Helpers

    private func updateParkSavedStatus(parkName: String, isSaved: Bool) {
        parks = parks.map { park in
            if park.parkName == parkName {
                var p = park
                p.isSaved = isSaved
                return p
            }
            return park
        }
    }

    // Mock distance calculator - replace with real coordinates
    private func calculateMockDistance(for parkName: String, from location: CLLocationCoordinate2D) -> Double? {
        // Sample park coordinates from the backend
        let parkCoordinates: [String: (Double, Double)] = [
            "Burke Lake Park": (38.7608, -77.2997),
            "Clemyjontri Park": (38.9547, -77.1847),
            "Great Falls Park": (38.9985, -77.2519),
            "Lake Fairfax Park": (38.9647, -77.3386),
            "Huntley Meadows Park": (38.7561, -77.1019),
        ]

        // Check if we have coordinates for this park
        if let coords = parkCoordinates[parkName] {
            return locationService.distanceToLocation(lat: coords.0, lng: coords.1)
        }

        // Generate semi-random but consistent distance for other parks
        let hash = abs(parkName.hashValue)
        return Double(hash % 20) + Double(hash % 100) / 100.0 + 1.0
    }
}
