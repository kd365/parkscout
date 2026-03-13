import Foundation
import CoreLocation

class LocationService: NSObject, ObservableObject {
    static let shared = LocationService()

    private let locationManager = CLLocationManager()

    @Published var currentLocation: CLLocationCoordinate2D?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published var errorMessage: String?

    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    func requestPermission() {
        locationManager.requestWhenInUseAuthorization()
    }

    func startUpdating() {
        locationManager.startUpdatingLocation()
    }

    func stopUpdating() {
        locationManager.stopUpdatingLocation()
    }

    // Calculate distance from current location to a park
    func distanceToLocation(lat: Double, lng: Double) -> Double? {
        guard let current = currentLocation else { return nil }

        let currentLoc = CLLocation(latitude: current.latitude, longitude: current.longitude)
        let parkLoc = CLLocation(latitude: lat, longitude: lng)

        // Returns distance in meters, convert to miles
        return currentLoc.distance(from: parkLoc) / 1609.34
    }

    // Estimate drive time (same formula as backend)
    func estimateDriveTime(distanceMiles: Double) -> Int {
        let routeFactor = 1.3  // Suburban roads aren't straight
        let avgSpeedMph = 25.0 // Conservative suburban driving

        let actualDistance = distanceMiles * routeFactor
        let timeHours = actualDistance / avgSpeedMph
        return Int(timeHours * 60)
    }

    // Get distance category
    func distanceCategory(driveTimeMinutes: Int) -> DistanceCategory {
        if driveTimeMinutes <= 15 {
            return .near
        } else if driveTimeMinutes <= 20 {
            return .moderate
        } else {
            return .driveable
        }
    }
}

// MARK: - CLLocationManagerDelegate

extension LocationService: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        currentLocation = location.coordinate
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        errorMessage = error.localizedDescription
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus

        switch manager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways:
            startUpdating()
        case .denied, .restricted:
            errorMessage = "Location access denied. Enable in Settings to see nearby parks."
        case .notDetermined:
            break
        @unknown default:
            break
        }
    }
}
