/* OpenBot OS opt-in debugger payload probe. MIT; source-only, not a loader fix.
 * Build only with an already approved Windows toolchain, then record this owned
 * test process with --debug-strings. No registry, network or filesystem writes.
 * Check exact ANSI and UTF-16 text AND raw bytes before any loader-snaps proposal.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

int main(void) {
    OutputDebugStringA("OpenBot OS ANSI probe 0123456789");
    OutputDebugStringW(L"OpenBot OS Unicode probe \u0C05 \u20AC");
    return 0;
}
