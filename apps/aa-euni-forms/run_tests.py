#!/usr/bin/env python
"""Simple test runner for euniforms tests."""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def setup_test_environment():
    """Set up Django test environment."""
    # Add the current directory to sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Configure Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'euniforms.tests.settings')
    django.setup()

def run_tests():
    """Run the test suite."""
    setup_test_environment()

    # Get Django's test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    # Run tests
    failures = test_runner.run_tests(["euniforms.tests"])

    if failures:
        return 1
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(run_tests())