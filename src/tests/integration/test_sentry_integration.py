#!/usr/bin/env python3
"""
Test script to verify Sentry integration is working correctly.

Run this script to test the logging and Sentry setup:
    python scripts/test_sentry_integration.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flood_forecaster.utils.logging_config import (
    setup_logging,
    get_logger,
    capture_message,
    capture_exception,
    add_breadcrumb
)


def test_sentry_integration():
    """Test the Sentry integration setup."""

    print("=" * 70)
    print("Testing Sentry Integration for Saadaal Flood Forecaster")
    print("=" * 70)
    print()

    # Check environment variables
    sentry_dsn = os.getenv('SENTRY_DSN')
    sentry_env = os.getenv('SENTRY_ENVIRONMENT', 'not set (will use default: production)')
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    print("Configuration:")
    print(f"  - SENTRY_DSN: {'✓ Set' if sentry_dsn else '✗ Not Set'}")
    if sentry_dsn:
        # Show only first and last 10 chars for security
        masked_dsn = sentry_dsn[:15] + "..." + sentry_dsn[-10:] if len(sentry_dsn) > 25 else "***"
        print(f"    Value: {masked_dsn}")
    print(f"  - SENTRY_ENVIRONMENT: {sentry_env}")
    print(f"  - LOG_LEVEL: {log_level}")
    print()

    # Initialize logging
    print("Initializing logging system...")
    setup_logging(level=log_level)
    print("✓ Logging system initialized")
    print()

    # Create a logger
    logger = get_logger(__name__)
    print("Testing different log levels:")
    print()

    # Test different log levels
    print("1. Testing DEBUG level (not sent to Sentry)...")
    logger.debug("This is a debug message - for development only")

    print("2. Testing INFO level (sent as breadcrumb to Sentry)...")
    logger.info("This is an info message - routine information")

    print("3. Testing WARNING level (sent as breadcrumb to Sentry)...")
    logger.warning("This is a warning message - something to watch")

    print("4. Testing ERROR level (sent as event to Sentry)...")
    logger.error("This is an error message - something went wrong")

    print()
    print("Testing breadcrumb functionality...")
    add_breadcrumb(
        message="Test breadcrumb for station processing",
        category="test",
        level="info",
        station="Belet Weyne",
        test_run=True
    )
    print("✓ Breadcrumb added")
    print()

    print("Testing manual message capture...")
    capture_message(
        "Test message from integration test",
        level="info",
        test_type="integration_test",
        timestamp=str(os.times())
    )
    print("✓ Manual message captured")
    print()

    print("Testing exception capture...")
    try:
        # Intentionally raise an exception
        raise ValueError("This is a test exception - don't worry!")
    except Exception as e:
        print(f"✓ Exception raised: {e}")
        capture_exception(
            e,
            test_run=True,
            location="test_script",
            note="This is an intentional test exception"
        )
        print("✓ Exception captured and sent to Sentry")
    print()

    print("=" * 70)
    if sentry_dsn:
        print("✓ All tests completed!")
        print()
        print("Next steps:")
        print("1. Check your Sentry dashboard at https://sentry.io")
        print("2. You should see:")
        print("   - 1 error event (test exception)")
        print("   - 1 error event (error log message)")
        print("   - Breadcrumbs attached to events")
        print("   - INFO and WARNING logs as breadcrumbs")
        print()
        print("Note: It may take a few seconds for events to appear in Sentry.")
    else:
        print("⚠ Tests completed with warnings!")
        print()
        print("SENTRY_DSN is not set - logs are only local.")
        print()
        print("To enable Sentry:")
        print("1. Get your DSN from https://sentry.io")
        print("2. Set environment variable:")
        print("   export SENTRY_DSN='your-dsn-here'")
        print("3. Run this test again")
    print("=" * 70)


if __name__ == "__main__":
    test_sentry_integration()
