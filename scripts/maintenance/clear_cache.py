#!/usr/bin/env python
"""
Clear the requests cache that may contain stale forecast data.
This solves the issue where forecast data was cached on Oct 11, 2025
and never refreshed due to expire_after=-1 setting.
"""

import os
import sys
from pathlib import Path


def main():
    """Clear the requests cache files."""
    print("=" * 80)
    print("CLEAR REQUESTS CACHE")
    print("=" * 80)
    print()

    # Find all cache files
    cache_files = [
        ".cache",
        ".cache.sqlite",
        ".cache.sqlite-shm",
        ".cache.sqlite-wal",
    ]

    deleted_count = 0
    for cache_file in cache_files:
        cache_path = Path(cache_file)
        if cache_path.exists():
            try:
                size = cache_path.stat().st_size
                os.remove(cache_path)
                print(f"✅ Deleted: {cache_file} ({size:,} bytes)")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {cache_file}: {e}")
        else:
            print(f"ℹ️  Not found: {cache_file}")

    print()
    if deleted_count > 0:
        print(f"✅ Successfully cleared {deleted_count} cache file(s)")
        print()
        print("IMPORTANT: The next API call will fetch fresh data from Open-Meteo.")
        print("Run this before the next forecast ingestion to ensure fresh data.")
    else:
        print("ℹ️  No cache files found to delete.")
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
