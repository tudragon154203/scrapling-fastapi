#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_dynamic_fetcher():
    """Test if DynamicFetcher is available and working."""
    print("=== Testing DynamicFetcher ===")

    try:
        from scrapling.fetchers import DynamicFetcher
        print("✅ DynamicFetcher imported successfully")
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        return False

    try:
        fetcher = DynamicFetcher()
        print("✅ DynamicFetcher instantiated successfully")
        print(f"   Type: {type(fetcher)}")
    except Exception as e:
        print(f"❌ Exception during instantiation: {e}")
        return False

    # Check the fetch method signature
    try:
        import inspect
        sig = inspect.signature(DynamicFetcher.fetch)
        print(f"✅ Fetch method signature: {sig}")
        print(f"   Parameters: {list(sig.parameters.keys())}")
    except Exception as e:
        print(f"❌ Exception checking signature: {e}")
        return False

    return True

if __name__ == "__main__":
    success = test_dynamic_fetcher()
    if not success:
        print("\n💡 Try installing: pip install 'scrapling[chromium]'")
    else:
        print("\n✅ DynamicFetcher is available")