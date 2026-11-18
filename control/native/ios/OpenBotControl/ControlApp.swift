import SwiftUI

@main
struct OpenBotControlApp: App {
    var body: some Scene {
        WindowGroup {
            ControlRootView()
                .background(Color.white)
                .preferredColorScheme(.light)
        }
    }
}

/// Source-only until an actual Xcode build and iPhone/simulator tests exist.
struct ControlRootView: View {
    @State private var typedOrigin = ""
    @State private var selectedOrigin = ""
    @State private var pendingOrigin = ""
    @State private var confirmServer = false
    @State private var message = "Offline workspace · no authority"

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                TextField("https://YOUR-APPROVED-HOST", text: $typedOrigin)
                    .keyboardType(.URL).textInputAutocapitalization(.never)
                    .autocorrectionDisabled().textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Owner-approved HTTPS server origin, without credentials")
                Button("Connect") { chooseServer() }
                Button("Offline") {
                    selectedOrigin = ""
                    message = "Offline workspace · no authority"
                }
            }.padding(.horizontal)
            Text(message).font(.caption2).foregroundStyle(.secondary)
                .accessibilityAddTraits(.updatesFrequently)
            PreviewWebView(origin: selectedOrigin).id(selectedOrigin)
        }
        .confirmationDialog("Trust this HTTPS server?", isPresented: $confirmServer, titleVisibility: .visible) {
            Button("Connect to the selected server") {
                selectedOrigin = pendingOrigin
                message = "HTTPS origin selected · scoped pairing still required"
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Only proceed for your owner-approved server: \(pendingOrigin). Apple must validate TLS. There is no certificate bypass. No provider key belongs in this app. Device keys are renderer-memory only, not Secure Enclave identities.")
        }
    }

    private func chooseServer() {
        let value = typedOrigin.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URLComponents(string: value), url.scheme == "https",
              let host = url.host, !host.isEmpty, host.count <= 253,
              host.range(of: "^[A-Za-z0-9.-]+$", options: .regularExpression) != nil,
              url.user == nil, url.password == nil, url.query == nil, url.fragment == nil,
              url.path.isEmpty || url.path == "/", !value.contains("\\"),
              url.port == nil || ((url.port ?? 0) > 0 && (url.port ?? 0) <= 65535)
        else { message = "Invalid HTTPS origin · previous view unchanged"; return }
        let port = url.port == nil || url.port == 443 ? "" : ":\(url.port!)"
        pendingOrigin = "https://" + host.lowercased() + port
        confirmServer = true
    }
}
