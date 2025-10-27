#!/usr/bin/env python3
"""
Test runner for Document Processing Pipeline tests.
"""

import os
import sys
import unittest
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests(verbose=False):
    """Run all test modules."""
    # Test modules to run
    test_modules = [
        'test_document',
        'test_document_pipeline', 
        'test_web_page_retriever',
        'test_rss_feed_retriever',
        'test_rss_feed_monitor',
        'test_config'
    ]
    
    # Load and run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module = __import__(module_name)
            suite.addTests(loader.loadTestsFromModule(module))
            if verbose:
                print(f"✓ Loaded tests from {module_name}")
        except ImportError as e:
            print(f"⚠️  Could not import {module_name}: {e}")
        except Exception as e:
            print(f"❌ Error loading {module_name}: {e}")
    
    # Run the tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Document Processing Pipeline tests")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--module", "-m", help="Run tests from specific module only")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Document Processing Pipeline - Test Suite")
    print("=" * 60)
    
    if args.module:
        # Run specific module
        try:
            loader = unittest.TestLoader()
            module = __import__(args.module)
            suite = loader.loadTestsFromModule(module)
            verbosity = 2 if args.verbose else 1
            runner = unittest.TextTestRunner(verbosity=verbosity)
            result = runner.run(suite)
            success = result.wasSuccessful()
        except ImportError as e:
            print(f"❌ Could not import module {args.module}: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error running module {args.module}: {e}")
            return 1
    else:
        # Run all tests
        success = run_all_tests(verbose=args.verbose)
    
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 