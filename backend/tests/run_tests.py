#!/usr/bin/env python3
"""
Script to run all tests for the backend.
"""

import os
import sys
import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_all_tests():
    """Run all tests for the backend"""
    
    # Get the directory of this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the parent directory to the path
    sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..')))
    
    # Run the tests
    pytest_args = [
        test_dir,
        '-v',
        '--no-header',
        '--no-summary',
        '--tb=short'
    ]
    
    logger.info("Running all tests...")
    result = pytest.main(pytest_args)
    
    if result == 0:
        logger.info("All tests passed!")
    else:
        logger.error(f"Tests failed with exit code {result}")
    
    return result

def run_specific_tests(test_modules):
    """Run specific test modules"""
    
    # Get the directory of this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the parent directory to the path
    sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..')))
    
    # Build the list of test files
    test_files = []
    for module in test_modules:
        test_files.append(os.path.join(test_dir, f"test_{module}.py"))
    
    # Run the tests
    pytest_args = [
        *test_files,
        '-v',
        '--no-header',
        '--no-summary',
        '--tb=short'
    ]
    
    logger.info(f"Running tests for modules: {', '.join(test_modules)}")
    result = pytest.main(pytest_args)
    
    if result == 0:
        logger.info("All specified tests passed!")
    else:
        logger.error(f"Tests failed with exit code {result}")
    
    return result

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        # Run specific test modules
        modules = sys.argv[1:]
        run_specific_tests(modules)
    else:
        # Run all tests
        run_all_tests() 