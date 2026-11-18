package dev.openbot.controlpreview;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageInfo;
import android.graphics.Color;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Bundle;
import android.text.InputType;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Locale;

/** Owner-selected HTTPS control client. No native JS bridge or on-device agent. */
public final class MainActivity extends Activity {
    private WebView webView;
    private TextView status;
    private String origin = "";
    private String offlineHtml;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(255, 255, 255));
        getWindow().setNavigationBarColor(Color.rgb(255, 255, 255));
        try {
            PackageInfo implementation = WebView.getCurrentWebViewPackage();
            if (implementation == null || Integer.parseInt(implementation.versionName.split("\\.")[0]) < 100) {
                fail("Update Android System WebView through your trusted system store. Chromium 100+ is required. No server was contacted."); return;
            }
            try (InputStream input = getAssets().open("index.html"); ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                byte[] block = new byte[8192]; int read;
                while ((read = input.read(block)) != -1) buffer.write(block, 0, read);
                offlineHtml = new String(buffer.toByteArray(), StandardCharsets.UTF_8);
            }
            LinearLayout root = new LinearLayout(this);
            root.setOrientation(LinearLayout.VERTICAL); root.setFitsSystemWindows(true);
            root.setBackgroundColor(Color.rgb(255, 255, 255));
            LinearLayout bar = new LinearLayout(this); bar.setPadding(12, 3, 12, 3);
            Button select = new Button(this); select.setText("Server / Session");
            select.setContentDescription("Choose the trusted HTTPS control server or offline workspace");
            select.setOnClickListener(view -> chooseServer());
            status = new TextView(this); status.setTextColor(Color.rgb(75, 80, 72));
            status.setTextSize(11); status.setPadding(14, 14, 4, 3);
            bar.addView(select); bar.addView(status, new LinearLayout.LayoutParams(0, -2, 1));
            root.addView(bar);
            WebView.setWebContentsDebuggingEnabled(false);
            webView = new WebView(this); webView.setBackgroundColor(Color.rgb(255, 255, 255));
            WebSettings s = webView.getSettings();
            s.setUserAgentString(s.getUserAgentString() + " OpenBotNative/0.3.0");
            s.setJavaScriptEnabled(true); s.setDomStorageEnabled(false); s.setDatabaseEnabled(false);
            s.setAllowFileAccess(false); s.setAllowContentAccess(false);
            s.setAllowFileAccessFromFileURLs(false); s.setAllowUniversalAccessFromFileURLs(false);
            s.setBlockNetworkLoads(true); s.setBlockNetworkImage(true);
            s.setCacheMode(WebSettings.LOAD_NO_CACHE); s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
            s.setJavaScriptCanOpenWindowsAutomatically(false); s.setSupportMultipleWindows(false);
            s.setMediaPlaybackRequiresUserGesture(true); s.setSaveFormData(false); s.setGeolocationEnabled(false);
            // Respect the user's system font scale; do not force setTextZoom(100).
            webView.setWebViewClient(new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                    return !allowedNavigation(request.getUrl());
                }
                @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                    return !allowedNavigation(Uri.parse(url));
                }
                @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                    if (sameOrigin(request.getUrl())) return null;
                    return new WebResourceResponse("text/plain", "UTF-8", 403, "Origin blocked", Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
                }
                @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                    handler.cancel(); runOnUiThread(() -> status.setText("TLS refused · no bypass"));
                }
                @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                    if (request.isForMainFrame()) runOnUiThread(() -> status.setText("Unavailable · no authority"));
                }
            });
            webView.setWebChromeClient(new WebChromeClient() {
                @Override public void onPermissionRequest(PermissionRequest request) { request.deny(); }
                @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                    callback.onReceiveValue(null); return true;
                }
            });
            webView.setDownloadListener((url, userAgent, disposition, type, length) -> {
                status.setText("Native downloads not enabled · use verified owner tooling");
            });
            root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1)); setContentView(root);
            recordedPreview();
        } catch (Exception error) { fail("Local control could not start safely. No certificate override or agent fallback is available."); }
    }

    private boolean sameOrigin(Uri target) {
        if (origin.isEmpty() || !"https".equals(target.getScheme()) || target.getUserInfo() != null) return false;
        Uri selected = Uri.parse(origin);
        int a = target.getPort() == -1 ? 443 : target.getPort();
        int b = selected.getPort() == -1 ? 443 : selected.getPort();
        return target.getHost() != null && target.getHost().equalsIgnoreCase(selected.getHost()) && a == b;
    }
    private boolean allowedNavigation(Uri uri) {
        return "about:blank".equals(uri.toString()) || (sameOrigin(uri) && "/control/".equals(uri.getPath()) && uri.getQuery() == null);
    }
    private void chooseServer() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setSingleLine(true); input.setHint("https://YOUR-APPROVED-HOST"); input.setText(origin);
        new AlertDialog.Builder(this).setTitle("Owner-approved HTTPS server")
            .setMessage("Only connect to a server you trust. Android must validate its TLS certificate. Enter an origin only, never credentials. Pairing is a separate scoped step. Device keys are memory-only, not hardware-backed.")
            .setView(input).setNegativeButton("Cancel", null)
            .setNeutralButton("Offline workspace", (dialog, which) -> recordedPreview())
            .setPositiveButton("Connect", (dialog, which) -> {
                try {
                    String value = input.getText().toString().trim();
                    Uri uri = Uri.parse(value);
                    if (!"https".equals(uri.getScheme()) || uri.getHost() == null || !uri.getHost().matches("[A-Za-z0-9.-]{1,253}") ||
                        uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null ||
                        (uri.getPath() != null && !uri.getPath().isEmpty() && !"/".equals(uri.getPath())) ||
                        uri.getPort() == 0 || uri.getPort() < -1 || uri.getPort() > 65535 || value.contains("\\")) throw new IllegalArgumentException();
                    origin = "https://" + uri.getHost().toLowerCase(Locale.ROOT) + ((uri.getPort() == -1 || uri.getPort() == 443) ? "" : ":" + uri.getPort());
                    webView.stopLoading(); webView.clearHistory(); webView.clearCache(true);
                    webView.getSettings().setBlockNetworkLoads(false);
                    status.setText("HTTPS · pairing required"); webView.loadUrl(origin + "/control/");
                } catch (Exception invalid) { status.setText("Invalid HTTPS origin · previous view unchanged"); }
            }).show();
    }
    private void recordedPreview() {
        origin = ""; webView.stopLoading(); webView.clearHistory(); webView.clearCache(true);
        webView.getSettings().setBlockNetworkLoads(true); status.setText("Offline · no authority");
        webView.loadDataWithBaseURL("https://openbot-offline.invalid/", offlineHtml, "text/html", "UTF-8", null);
    }
    private void fail(String message) {
        TextView text = new TextView(this); text.setText("OpenBot Local Control\n\n" + message);
        text.setTextSize(17); text.setTextColor(Color.rgb(45, 48, 43));
        text.setBackgroundColor(Color.rgb(255, 255, 255)); text.setPadding(32, 64, 32, 32); setContentView(text);
    }
    @Override public void onBackPressed() {
        if (webView == null) { super.onBackPressed(); return; }
        webView.evaluateJavascript("Boolean(window.openbotBack && window.openbotBack())", result -> {
            if (!"true".equals(result)) closeOrBack();
        });
    }
    private void closeOrBack() { if (webView.canGoBack()) webView.goBack(); else super.onBackPressed(); }
    @Override protected void onPause() {
        if (webView != null) { webView.evaluateJavascript("window.dispatchEvent(new Event('openbotpause'))", null); webView.onPause(); }
        super.onPause();
    }
    @Override protected void onResume() {
        super.onResume(); if (webView != null) { webView.onResume(); webView.evaluateJavascript("window.dispatchEvent(new Event('openbotresume'))", null); }
    }
    @Override protected void onDestroy() {
        if (webView != null) { webView.stopLoading(); webView.clearHistory(); webView.clearCache(true); webView.removeAllViews(); webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
