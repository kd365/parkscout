import SwiftUI

struct AuthView: View {
    @ObservedObject var authService = AuthService.shared
    @State private var isLoginMode = true
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var displayName = ""
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "safari.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.appPrimary)

                        Text("ParkScout")
                            .font(.appTitle)
                            .foregroundColor(.appTextPrimary)

                        Text(isLoginMode ? "Welcome back, Scout!" : "Join the ParkScout community")
                            .font(.appSubheadline)
                            .foregroundColor(.appTextSecondary)
                    }
                    .padding(.top, 40)

                    // Form
                    VStack(spacing: 16) {
                        // Email field
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Email")
                                .font(.appCaption)
                                .foregroundColor(.appTextSecondary)

                            TextField("mom@example.com", text: $email)
                                .textContentType(.emailAddress)
                                .keyboardType(.emailAddress)
                                .autocapitalization(.none)
                                .padding()
                                .background(Color.appCard)
                                .cornerRadius(12)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12)
                                        .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                                )
                        }

                        // Display name (register only)
                        if !isLoginMode {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Display Name (optional)")
                                    .font(.appCaption)
                                    .foregroundColor(.appTextSecondary)

                                TextField("Sarah", text: $displayName)
                                    .textContentType(.name)
                                    .padding()
                                    .background(Color.appCard)
                                    .cornerRadius(12)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12)
                                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                                    )
                            }
                        }

                        // Password field
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Password")
                                .font(.appCaption)
                                .foregroundColor(.appTextSecondary)

                            SecureField("Password", text: $password)
                                .textContentType(isLoginMode ? .password : .newPassword)
                                .padding()
                                .background(Color.appCard)
                                .cornerRadius(12)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12)
                                        .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                                )
                        }

                        // Confirm password (register only)
                        if !isLoginMode {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Confirm Password")
                                    .font(.appCaption)
                                    .foregroundColor(.appTextSecondary)

                                SecureField("Confirm Password", text: $confirmPassword)
                                    .textContentType(.newPassword)
                                    .padding()
                                    .background(Color.appCard)
                                    .cornerRadius(12)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12)
                                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                                    )
                            }
                        }
                    }
                    .padding(.horizontal)

                    // Error message
                    if let error = authService.errorMessage {
                        Text(error)
                            .font(.appCaption)
                            .foregroundColor(.appSecondary)
                            .padding(.horizontal)
                    }

                    // Submit button
                    Button {
                        Task {
                            await submitForm()
                        }
                    } label: {
                        HStack {
                            if authService.isLoading {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text(isLoginMode ? "Sign In" : "Create Account")
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                    }
                    .buttonStyle(PrimaryButtonStyle(isEnabled: isFormValid && !authService.isLoading))
                    .disabled(!isFormValid || authService.isLoading)
                    .padding(.horizontal)

                    // Toggle mode
                    Button {
                        withAnimation {
                            isLoginMode.toggle()
                            authService.errorMessage = nil
                        }
                    } label: {
                        Text(isLoginMode ? "Don't have an account? Sign up" : "Already have an account? Sign in")
                            .font(.appBody)
                            .foregroundColor(.appPrimary)
                    }

                    Spacer()
                }
            }
            .background(Color.appBackground)
            .navigationTitle(isLoginMode ? "Sign In" : "Sign Up")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var isFormValid: Bool {
        if isLoginMode {
            return !email.isEmpty && !password.isEmpty && email.contains("@")
        } else {
            return !email.isEmpty && !password.isEmpty && email.contains("@") &&
                   password.count >= 6 && password == confirmPassword
        }
    }

    private func submitForm() async {
        if isLoginMode {
            let success = await authService.login(email: email, password: password)
            if success {
                dismiss()
            }
        } else {
            let success = await authService.register(
                email: email,
                password: password,
                displayName: displayName.isEmpty ? nil : displayName
            )
            if success {
                dismiss()
            }
        }
    }
}

#Preview {
    AuthView()
}
