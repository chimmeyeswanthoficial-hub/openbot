# Third-party components and build tools

The shared web UI has no runtime package, CDN, external font, tracking or icon dependency. Icons are small inline SVG paths authored for this preview; app icons are locally generated geometric artwork.

- **Microsoft WebView2Loader.dll**, x64, unmodified, from the public `Microsoft.Web.WebView2` NuGet **1.0.2903.40**. Its copyright/license is reproduced in `native/windows/WebView2-LICENSE.txt` and the Windows portable distribution. Microsoft's brand is not an endorsement. The Evergreen browser runtime is a separate device prerequisite and is not redistributed.
- **MinGW-w64 GCC 14.2.0** builds the Windows executable. GCC runtime portions are subject to the GCC Runtime Library Exception, https://www.gnu.org/licenses/gcc-exception-3.1.html ; relevant compilation is performed using GCC. Windows system libraries are not included in the archive.
- **Android SDK platform API 35 revision 2 / build-tools 35.0.0**, downloaded from Google's public SDK repository, used only as build tools and platform stubs. Build tools, Android platform implementations and SDK archives are not redistributed with the app. The device supplies Android System WebView. Refer to the downloaded SDK notices/terms.
- **OpenJDK/Javac 11** and **OpenSSL** are local build tools, not included in the APK/source archive.
- **Playwright 1.56.1** (Apache 2.0) / its Chromium and Linux WebKit test browsers are test tools only, installed into a cache. No browser executable or Playwright dependency is redistributed here.
- **openstep-parser 2.0.3** is a local test-only parser for the generated Xcode project, not bundled with the app.
- **Apple SwiftUI/WebKit/iOS SDK** are target platform prerequisites, not included or used to compile this project in this Linux delivery. Draft project/privacy files do not establish Apple certification.

Exact public SDK URLs, sizes and locally observed SHA-256 pins are in `scripts/fetch-build-tools.py`. SHA pins bind what was downloaded; they are not independent vendor-signature or execution proof. No third-party project under the pre-existing workspace's `repos/` has been incorporated into this new UI.
