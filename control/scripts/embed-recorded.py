#!/usr/bin/env python3
"""Historical tool, intentionally disabled for the new shared companion UI.

Old recorded QA/media evidence remains in prior evidence packets, not preloaded as
current work. Build the shared source using studio/scripts/build-web.py instead.
A recording must never create pairing scope, approvals or a live computer screen.
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_known_args()
    parser.exit(
        2,
        "Recorded-data injection is disabled for the shared UI. Use the raw historical receipts for inspection; rebuild with studio/scripts/build-web.py.\n",
    )


if __name__ == "__main__":
    main()
