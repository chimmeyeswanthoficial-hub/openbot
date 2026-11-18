// OpenBot Control — owner-selected HTTPS WebView2 control host. No agent runtime.
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <shlobj.h>
#include <objbase.h>
#include <string>
#include <functional>
#include <utility>
#include <cwctype>
#include "WebView2.h"

static HWND windowHandle = nullptr;
static HMODULE loaderModule = nullptr;
static ICoreWebView2Environment* environment = nullptr;
static ICoreWebView2Controller* controller = nullptr;
static ICoreWebView2* webview = nullptr;
static bool closing = false;
static std::wstring serverOrigin;
static bool sameOrigin(const std::wstring& uri) {
    return !serverOrigin.empty() && uri.rfind(serverOrigin + L"/", 0) == 0;
}

// Owner-controlled adjacent UTF-8/ASCII file, never a URL passed by web content.
// Missing file leaves the bundled offline workspace completely network-blocked.
static bool selectServer(const std::wstring& directory) {
    std::wstring config = directory + L"server-origin.txt";
    HANDLE file = CreateFileW(config.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr);
    if (file == INVALID_HANDLE_VALUE) return GetLastError() == ERROR_FILE_NOT_FOUND;
    BY_HANDLE_FILE_INFORMATION info{};
    char buffer[513]{}; DWORD size = 0;
    bool ok = GetFileInformationByHandle(file, &info) && !(info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) &&
        info.nFileSizeHigh == 0 && info.nFileSizeLow <= 512 && ReadFile(file, buffer, 512, &size, nullptr);
    CloseHandle(file);
    if (!ok || !size) return false;
    std::wstring origin;
    for (DWORD i = 0; i < size; i++) { if (static_cast<unsigned char>(buffer[i]) > 127 || buffer[i] == 0) return false; origin += wchar_t(buffer[i]); }
    while (!origin.empty() && (origin.back() == L'\n' || origin.back() == L'\r')) origin.pop_back();
    if (origin.rfind(L"https://", 0) != 0 || origin.size() < 9) return false;
    std::wstring host = origin.substr(8), port;
    auto colon = host.find(L':');
    if (colon != std::wstring::npos) { port = host.substr(colon + 1); host.resize(colon); }
    if (host.empty() || host.size() > 253 || host.front() == L'.' || host.back() == L'.') return false;
    for (auto& c : host) {
        if (!((c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') || (c >= L'0' && c <= L'9') || c == L'-' || c == L'.')) return false;
        c = std::towlower(c);
    }
    unsigned number = 443;
    if (colon != std::wstring::npos) {
        if (port.empty() || port.size() > 5) return false;
        number = 0;
        for (auto c : port) { if (c < L'0' || c > L'9') return false; number = number * 10 + unsigned(c - L'0'); }
        if (!number || number > 65535) return false;
    }
    origin = L"https://" + host + (number == 443 ? L"" : L":" + std::to_wstring(number));
    std::wstring message = L"Connect this control window to:\n\n" + origin +
        L"\n\nProceed only if this is your owner-approved server. Windows must validate its HTTPS certificate. "
        L"No certificate bypass is available. You will still need a scoped one-use pairing code. "
        L"Choose No for the offline offline workspace.";
    if (MessageBoxW(windowHandle, message.c_str(), L"Confirm the trusted OpenBot server", MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2) == IDYES) serverOrigin = origin;
    return true;
}

template<class Interface, class... Args> class Callback final : public Interface {
    volatile LONG references = 1;
    GUID interfaceId;
    std::function<HRESULT(Args...)> function;
public:
    Callback(REFIID id, std::function<HRESULT(Args...)> fn) : interfaceId(id), function(std::move(fn)) {}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id, void** object) override {
        if (!object) return E_POINTER;
        *object = nullptr;
        if (IsEqualIID(id, IID_IUnknown) || IsEqualIID(id, interfaceId)) {
            *object = static_cast<Interface*>(this); AddRef(); return S_OK;
        }
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&references); }
    ULONG STDMETHODCALLTYPE Release() override {
        ULONG left = InterlockedDecrement(&references);
        if (!left) delete this;
        return left;
    }
    HRESULT STDMETHODCALLTYPE Invoke(Args... args) override { return function(args...); }
};

template<class Interface, class... Args, class F> static Interface* callback(REFIID id, F fn) {
    return new Callback<Interface, Args...>(id, std::move(fn));
}

static void fail(const wchar_t* message) {
    if (closing) return;
    MessageBoxW(windowHandle, message, L"OpenBot Control Preview — unable to start", MB_OK | MB_ICONWARNING);
    if (windowHandle) PostMessageW(windowHandle, WM_CLOSE, 0, 0);
}

static std::wstring bundledHtml() {
    HRSRC resource = FindResourceW(nullptr, MAKEINTRESOURCEW(101), RT_RCDATA);
    if (!resource) return {};
    DWORD size = SizeofResource(nullptr, resource);
    const char* bytes = static_cast<const char*>(LockResource(LoadResource(nullptr, resource)));
    if (!bytes || !size || size > 2 * 1024 * 1024) return {};
    int length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, bytes, size, nullptr, 0);
    if (!length) return {};
    std::wstring html(length, L'\0');
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, bytes, size, html.data(), length)) return {};
    return html;
}

static bool configureWebView() {
    ICoreWebView2Settings* settings = nullptr;
    if (FAILED(webview->get_Settings(&settings)) || !settings) return false;
    bool ok = SUCCEEDED(settings->put_IsScriptEnabled(TRUE)) &&
        SUCCEEDED(settings->put_AreDevToolsEnabled(FALSE)) &&
        SUCCEEDED(settings->put_AreDefaultContextMenusEnabled(FALSE)) &&
        SUCCEEDED(settings->put_AreDefaultScriptDialogsEnabled(FALSE)) &&
        SUCCEEDED(settings->put_AreHostObjectsAllowed(FALSE)) &&
        SUCCEEDED(settings->put_IsWebMessageEnabled(FALSE)) &&
        SUCCEEDED(settings->put_IsStatusBarEnabled(FALSE));
    ICoreWebView2Settings2* settings2 = nullptr;
    if (SUCCEEDED(settings->QueryInterface(IID_ICoreWebView2Settings2, reinterpret_cast<void**>(&settings2))) && settings2) {
        LPWSTR agent = nullptr;
        if (SUCCEEDED(settings2->get_UserAgent(&agent)) && agent) {
            std::wstring tagged = std::wstring(agent) + L" OpenBotNative/0.3.0";
            ok = ok && SUCCEEDED(settings2->put_UserAgent(tagged.c_str()));
        } else { ok = false; }
        CoTaskMemFree(agent); settings2->Release();
    } else { ok = false; }
    settings->Release();
    if (!ok) return false;

    EventRegistrationToken token{};
    auto navigation = callback<ICoreWebView2NavigationStartingEventHandler, ICoreWebView2*, ICoreWebView2NavigationStartingEventArgs*>(IID_ICoreWebView2NavigationStartingEventHandler,
        [](ICoreWebView2*, ICoreWebView2NavigationStartingEventArgs* args)->HRESULT {
            LPWSTR uri = nullptr;
            HRESULT hr = args->get_Uri(&uri);
            std::wstring target = uri ? uri : L"";
            bool allowed = SUCCEEDED(hr) && (target == L"about:blank" || (!serverOrigin.empty() &&
                (target == serverOrigin + L"/control/" || target.rfind(serverOrigin + L"/control/#", 0) == 0)));
            CoTaskMemFree(uri);
            return args->put_Cancel(!allowed);
        });
    HRESULT hr = webview->add_NavigationStarting(navigation, &token); navigation->Release();
    if (FAILED(hr)) return false;

    auto popup = callback<ICoreWebView2NewWindowRequestedEventHandler, ICoreWebView2*, ICoreWebView2NewWindowRequestedEventArgs*>(IID_ICoreWebView2NewWindowRequestedEventHandler,
        [](ICoreWebView2*, ICoreWebView2NewWindowRequestedEventArgs* args)->HRESULT { return args->put_Handled(TRUE); });
    hr = webview->add_NewWindowRequested(popup, &token); popup->Release();
    if (FAILED(hr)) return false;

    auto permission = callback<ICoreWebView2PermissionRequestedEventHandler, ICoreWebView2*, ICoreWebView2PermissionRequestedEventArgs*>(IID_ICoreWebView2PermissionRequestedEventHandler,
        [](ICoreWebView2*, ICoreWebView2PermissionRequestedEventArgs* args)->HRESULT { return args->put_State(COREWEBVIEW2_PERMISSION_STATE_DENY); });
    hr = webview->add_PermissionRequested(permission, &token); permission->Release();
    if (FAILED(hr)) return false;

    auto resource = callback<ICoreWebView2WebResourceRequestedEventHandler, ICoreWebView2*, ICoreWebView2WebResourceRequestedEventArgs*>(IID_ICoreWebView2WebResourceRequestedEventHandler,
        [](ICoreWebView2*, ICoreWebView2WebResourceRequestedEventArgs* args)->HRESULT {
            if (!environment || closing) return E_ABORT;
            ICoreWebView2WebResourceRequest* request = nullptr;
            LPWSTR uri = nullptr;
            if (SUCCEEDED(args->get_Request(&request)) && request) {
                request->get_Uri(&uri); request->Release();
            }
            bool allowed = uri && sameOrigin(uri);
            CoTaskMemFree(uri);
            if (allowed) return S_OK; // platform TLS validation is never overridden
            ICoreWebView2WebResourceResponse* response = nullptr;
            HRESULT result = environment->CreateWebResourceResponse(nullptr, 403, L"Origin blocked", L"Content-Type: text/plain\r\nCache-Control: no-store", &response);
            if (FAILED(result) || !response) return E_FAIL;
            result = args->put_Response(response); response->Release(); return result;
        });
    hr = webview->add_WebResourceRequested(resource, &token); resource->Release();
    if (FAILED(hr) || FAILED(webview->AddWebResourceRequestedFilter(L"*", COREWEBVIEW2_WEB_RESOURCE_CONTEXT_ALL))) return false;

    ICoreWebView2_4* downloadView = nullptr;
    if (FAILED(webview->QueryInterface(IID_ICoreWebView2_4, reinterpret_cast<void**>(&downloadView))) || !downloadView) return false;
    auto download = callback<ICoreWebView2DownloadStartingEventHandler, ICoreWebView2*, ICoreWebView2DownloadStartingEventArgs*>(IID_ICoreWebView2DownloadStartingEventHandler,
        [](ICoreWebView2*, ICoreWebView2DownloadStartingEventArgs* args)->HRESULT { return args->put_Cancel(TRUE); });
    hr = downloadView->add_DownloadStarting(download, &token); download->Release(); downloadView->Release();
    return SUCCEEDED(hr);
}

static void startWebView() {
    wchar_t executable[32768]{};
    DWORD length = GetModuleFileNameW(nullptr, executable, 32768);
    if (!length || length >= 32768) { fail(L"The application path could not be resolved."); return; }
    std::wstring loaderPath(executable, length);
    auto slash = loaderPath.find_last_of(L"\\/");
    if (slash == std::wstring::npos) { fail(L"The application directory could not be resolved."); return; }
    loaderPath.resize(slash + 1);
    if (!selectServer(loaderPath)) { fail(L"server-origin.txt must contain one valid HTTPS origin, without a path, credentials or a symlink. Startup refused."); return; }
    loaderPath += L"WebView2Loader.dll";
    loaderModule = LoadLibraryExW(loaderPath.c_str(), nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!loaderModule) {
        fail(L"WebView2Loader.dll must be beside this executable. Extract the complete Windows ZIP first. Nothing was connected or executed."); return;
    }
    using CreateEnvironment = HRESULT (STDAPICALLTYPE *)(PCWSTR, PCWSTR, ICoreWebView2EnvironmentOptions*, ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler*);
    auto create = reinterpret_cast<CreateEnvironment>(GetProcAddress(loaderModule, "CreateCoreWebView2EnvironmentWithOptions"));
    if (!create) { fail(L"The WebView2 loader is unavailable or incompatible. Use the x64 DLL supplied with this preview."); return; }

    PWSTR local = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_CREATE, nullptr, &local))) { fail(L"A separate preview cache could not be created."); return; }
    std::wstring profile(local); CoTaskMemFree(local);
    profile += L"\\OpenBotControlLocal";
    if (!CreateDirectoryW(profile.c_str(), nullptr) && GetLastError() != ERROR_ALREADY_EXISTS) { fail(L"A separate preview cache could not be created."); return; }
    profile += L"\\WebView2";

    // Do not inherit script-debugging or alternate-browser overrides from the shell.
    for (const auto* key : {L"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", L"WEBVIEW2_PIPE_FOR_SCRIPT_DEBUGGER", L"WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", L"WEBVIEW2_USER_DATA_FOLDER", L"WEBVIEW2_RELEASE_CHANNEL_PREFERENCE"}) SetEnvironmentVariableW(key, nullptr);

    auto ready = callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler, HRESULT, ICoreWebView2Environment*>(IID_ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler,
        [](HRESULT result, ICoreWebView2Environment* created)->HRESULT {
            if (closing) return S_OK;
            if (FAILED(result) || !created) { fail(L"Microsoft Edge WebView2 Runtime is required. Install the current Evergreen x64 Runtime from Microsoft's official WebView2 download page, then reopen this preview. No runtime is downloaded automatically."); return S_OK; }
            environment = created; environment->AddRef();
            auto readyController = callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler, HRESULT, ICoreWebView2Controller*>(IID_ICoreWebView2CreateCoreWebView2ControllerCompletedHandler,
                [](HRESULT result, ICoreWebView2Controller* createdController)->HRESULT {
                    if (closing) return S_OK;
                    if (FAILED(result) || !createdController) { fail(L"The WebView2 window could not be created. No server was contacted."); return S_OK; }
                    controller = createdController; controller->AddRef();
                    if (FAILED(controller->get_CoreWebView2(&webview)) || !webview || !configureWebView()) { fail(L"Required offline restrictions could not be installed. Preview startup was stopped."); return S_OK; }
                    RECT bounds{}; GetClientRect(windowHandle, &bounds);
                    controller->put_Bounds(bounds);
                    controller->put_IsVisible(TRUE);
                    if (!serverOrigin.empty()) {
                        std::wstring target = serverOrigin + L"/control/";
                        if (FAILED(webview->Navigate(target.c_str()))) fail(L"The selected HTTPS server could not be opened. No certificate bypass or offline authority fallback exists.");
                    } else {
                        std::wstring html = bundledHtml();
                        if (html.empty() || FAILED(webview->NavigateToString(html.c_str()))) fail(L"The bundled offline workspace could not be loaded.");
                    }
                    return S_OK;
                });
            HRESULT hr = environment->CreateCoreWebView2Controller(windowHandle, readyController); readyController->Release();
            if (FAILED(hr)) fail(L"The WebView2 controller could not start.");
            return S_OK;
        });
    HRESULT result = create(nullptr, profile.c_str(), nullptr, ready); ready->Release();
    if (FAILED(result)) fail(L"Microsoft Edge WebView2 Runtime is required. Extract the complete ZIP and install the current Evergreen x64 Runtime from Microsoft. This preview has no browser fallback and does not download a runtime automatically.");
}

static LRESULT CALLBACK windowProc(HWND hwnd, UINT message, WPARAM wp, LPARAM lp) {
    switch (message) {
    case WM_CREATE: PostMessageW(hwnd, WM_APP + 1, 0, 0); return 0;
    case WM_APP + 1: startWebView(); return 0;
    case WM_DPICHANGED: {
        auto suggested = reinterpret_cast<RECT*>(lp);
        SetWindowPos(hwnd, nullptr, suggested->left, suggested->top, suggested->right - suggested->left,
                     suggested->bottom - suggested->top, SWP_NOZORDER | SWP_NOACTIVATE); return 0;
    }
    case WM_SIZE:
        if (controller) { RECT bounds{}; GetClientRect(hwnd, &bounds); controller->put_Bounds(bounds); }
        return 0;
    case WM_GETMINMAXINFO: {
        auto info = reinterpret_cast<MINMAXINFO*>(lp); info->ptMinTrackSize = {390, 560}; return 0;
    }
    case WM_ACTIVATE:
        if (webview) webview->ExecuteScript(LOWORD(wp) == WA_INACTIVE ?
            L"window.dispatchEvent(new Event('openbotpause'))" :
            L"window.dispatchEvent(new Event('openbotresume'))", nullptr);
        return 0;
    case WM_CLOSE: DestroyWindow(hwnd); return 0;
    case WM_DESTROY:
        closing = true;
        if (controller) controller->Close();
        if (webview) { webview->Release(); webview = nullptr; }
        if (controller) { controller->Release(); controller = nullptr; }
        if (environment) { environment->Release(); environment = nullptr; }
        PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd, message, wp, lp);
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int show) {
    if (FAILED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED))) return 1;
    SetProcessDPIAware();
    WNDCLASSW wc{};
    wc.lpfnWndProc = windowProc; wc.hInstance = instance; wc.lpszClassName = L"OpenBotControlLocal";
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW); wc.hIcon = LoadIconW(instance, MAKEINTRESOURCEW(201));
    HBRUSH background = CreateSolidBrush(RGB(255, 255, 255)); wc.hbrBackground = background;
    if (!RegisterClassW(&wc)) { DeleteObject(background); CoUninitialize(); return 1; }
    windowHandle = CreateWindowExW(0, wc.lpszClassName, L"OpenBot Workspace — light interface (unsigned test build)", WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 1360, 940, nullptr, nullptr, instance, nullptr);
    if (!windowHandle) { DeleteObject(background); CoUninitialize(); return 1; }
    ShowWindow(windowHandle, show); UpdateWindow(windowHandle);
    MSG message{};
    while (GetMessageW(&message, nullptr, 0, 0) > 0) { TranslateMessage(&message); DispatchMessageW(&message); }
    CoUninitialize();
    // The loader stays mapped until exit so pending COM destructors cannot call unloaded code.
    DeleteObject(background);
    return static_cast<int>(message.wParam);
}
