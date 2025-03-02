#!/usr/bin/env python
"""
Script to run all backend tests.
"""
import os
import sys
import subprocess

def run_tests():
    """Run all tests in the tests directory"""
    # Get the directory of this script
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(tests_dir, '..'))
    
    print("Running backend tests...")
    print(f"Tests directory: {tests_dir}")
    print(f"Backend directory: {backend_dir}")
    
    # Change to the backend directory
    os.chdir(backend_dir)
    
    # Run the tests using pytest
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        print("All tests completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print("Test execution failed:")
        print(e.stdout)
        print("Errors:", e.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(run_tests()) 