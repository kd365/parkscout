import SwiftUI

@main
struct ParksFinderApp: App {
    @State private var showSplash = true

    var body: some Scene {
        WindowGroup {
            ZStack {
                ContentView()

                if showSplash {
                    SplashScreen()
                        .transition(.opacity)
                        .zIndex(1)
                }
            }
            .onAppear {
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
                    withAnimation(.easeOut(duration: 0.5)) {
                        showSplash = false
                    }
                }
            }
        }
    }
}

// MARK: - Splash Screen

struct SplashScreen: View {
    @State private var scale: CGFloat = 0.8
    @State private var opacity: Double = 0

    var body: some View {
        ZStack {
            Color.appBackground
                .ignoresSafeArea()

            VStack(spacing: 20) {
                Image(systemName: "tree.fill")
                    .font(.system(size: 80))
                    .foregroundColor(.appPrimary)
                    .scaleEffect(scale)

                VStack(spacing: 6) {
                    Text("ParkScout")
                        .font(.system(size: 36, weight: .bold, design: .rounded))
                        .foregroundColor(.appTextPrimary)

                    Text("Discover family-friendly parks")
                        .font(.system(size: 16))
                        .foregroundColor(.appTextSecondary)
                }
                .opacity(opacity)
            }
        }
        .onAppear {
            withAnimation(.spring(response: 0.6, dampingFraction: 0.6)) {
                scale = 1.0
            }
            withAnimation(.easeIn(duration: 0.4).delay(0.3)) {
                opacity = 1.0
            }
        }
    }
}
