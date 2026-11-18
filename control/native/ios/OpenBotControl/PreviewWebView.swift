import SwiftUI
import WebKit

/// Same-origin HTTPS control page or network-blocked bundled evidence preview.
/// No message handler/native bridge, persistent device key or on-device agent.
struct PreviewWebView: UIViewRepresentable {
    let origin: String
    func makeCoordinator() -> Coordinator { Coordinator(origin: origin) }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.applicationNameForUserAgent = "OpenBotNative/0.3.0"
        configuration.websiteDataStore = .nonPersistent()
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.mediaTypesRequiringUserActionForPlayback = .all
        let view = WKWebView(frame: .zero, configuration: configuration)
        context.coordinator.view = view
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        view.allowsLinkPreview = false
        view.allowsBackForwardNavigationGestures = false
        view.isOpaque = false
        view.backgroundColor = UIColor.white
        view.scrollView.backgroundColor = view.backgroundColor
        if #available(iOS 16.4, *) { view.isInspectable = false }

        var rules: [[String: Any]] = [["trigger": ["url-filter": "^https?://|^wss?://"], "action": ["type": "block"]]]
        if !origin.isEmpty {
            let exact = "^" + NSRegularExpression.escapedPattern(for: origin + "/")
            rules.append(["trigger": ["url-filter": exact], "action": ["type": "ignore-previous-rules"]])
        }
        guard let encoded = try? JSONSerialization.data(withJSONObject: rules),
              let text = String(data: encoded, encoding: .utf8) else {
            Coordinator.showFailure(in: view); return view
        }
        WKContentRuleListStore.default().compileContentRuleList(forIdentifier: "OpenBotLocal-\(origin.hashValue)", encodedContentRuleList: text) { [weak view] list, error in
            DispatchQueue.main.async {
                guard let view = view else { return }
                guard error == nil, let list = list else { Coordinator.showFailure(in: view); return }
                view.configuration.userContentController.add(list)
                if !origin.isEmpty, let url = URL(string: origin + "/control/") {
                    // Default platform TLS validation. No trust challenge override.
                    view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20))
                } else if let url = Bundle.main.url(forResource: "index", withExtension: "html"),
                          let html = try? String(contentsOf: url, encoding: .utf8) {
                    view.loadHTMLString(html, baseURL: nil)
                } else { Coordinator.showFailure(in: view) }
            }
        }
        return view
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
    static func dismantleUIView(_ view: WKWebView, coordinator: Coordinator) {
        view.stopLoading(); view.navigationDelegate = nil; view.uiDelegate = nil
        view.configuration.userContentController.removeAllUserScripts()
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        let origin: String
        weak var view: WKWebView?
        init(origin: String) {
            self.origin = origin
            super.init()
            NotificationCenter.default.addObserver(self, selector: #selector(pause), name: UIApplication.willResignActiveNotification, object: nil)
            NotificationCenter.default.addObserver(self, selector: #selector(resume), name: UIApplication.didBecomeActiveNotification, object: nil)
        }
        deinit { NotificationCenter.default.removeObserver(self) }
        @objc private func pause() { view?.evaluateJavaScript("window.dispatchEvent(new Event('openbotpause'))", completionHandler: nil) }
        @objc private func resume() { view?.evaluateJavaScript("window.dispatchEvent(new Event('openbotresume'))", completionHandler: nil) }
        static func showFailure(in view: WKWebView) {
            view.loadHTMLString("""
            <!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
            <body style="background:#ffffff;color:#30332e;padding:32px;font:17px -apple-system">
            <h2>OpenBot Local Control</h2><p>The control view could not start safely. No certificate bypass or offline authority fallback is available. Reconnect and pair after checking the trusted server.</p></body>
            """, baseURL: nil)
        }
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) { Self.showFailure(in: webView) }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { Self.showFailure(in: webView) }
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = action.request.url else { decisionHandler(.cancel); return }
            if url.absoluteString == "about:blank" { decisionHandler(.allow); return }
            let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
            let target = components.map { c in "https://" + (c.host ?? "").lowercased() + ((c.port == nil || c.port == 443) ? "" : ":\(c.port!)") }
            decisionHandler(!origin.isEmpty && target == origin && url.scheme == "https" && components?.user == nil && components?.password == nil && url.path == "/control/" && url.query == nil ? .allow : .cancel)
        }
        func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) { decisionHandler(response.canShowMIMEType ? .allow : .cancel) }
        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? { nil }
        func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin, initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType, decisionHandler: @escaping (WKPermissionDecision) -> Void) { decisionHandler(.deny) }
        func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) { completionHandler() }
        func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) { completionHandler(false) }
        func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) { completionHandler(nil) }
    }
}
