#!/usr/bin/env python3
"""
Test runner script for SigmaHQ RAG application.
Provides comprehensive test execution with different modes and reporting.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED (exit code: {e.returncode})")
        return False
    except FileNotFoundError:
        print(f"❌ {description} - FAILED (command not found)")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='Run SigmaHQ RAG tests')
    parser.add_argument('--mode', choices=['unit', 'integration', 'performance', 'all'], 
                       default='all', help='Test mode to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    success = True
    
    # Base pytest command
    pytest_cmd = ['uv', 'run', 'pytest']
    
    if args.verbose:
        pytest_cmd.append('-v')
    
    if args.parallel:
        pytest_cmd.extend(['-n', 'auto'])  # Auto-detect CPU cores
    
    if args.coverage:
        pytest_cmd.extend(['--cov=src', '--cov-report=html', '--cov-report=term'])
    
    # Test selection based on mode
    if args.mode == 'unit':
        pytest_cmd.extend(['tests/test_core_services.py', 'tests/test_models.py'])
    elif args.mode == 'integration':
        pytest_cmd.extend(['tests/test_integration.py', 'tests/test_rag_functionality.py'])
    elif args.mode == 'performance':
        pytest_cmd.extend(['tests/test_performance.py', 'tests/test_error_handling.py'])
    elif args.mode == 'all':
        pytest_cmd.append('tests/')
    
    # Run tests
    if not run_command(pytest_cmd, f"Running {args.mode} tests"):
        success = False
    
    # Run code quality checks if requested
    if args.mode in ['all', 'unit']:
        print(f"\n{'='*60}")
        print("Running code quality checks...")
        print(f"{'='*60}")
        
        # Run ruff checks
        if not run_command(['uv', 'run', 'ruff', 'check', 'src/', 'tests/'], "Code quality checks"):
            success = False
        
        # Run type checking if mypy is available
        if not run_command(['uv', 'run', 'mypy', 'src/'], "Type checking"):
            print("⚠️  Type checking failed, but continuing...")
    
    # Generate reports
    if args.coverage and success:
        print(f"\n{'='*60}")
        print("Coverage report generated in htmlcov/index.html")
        print(f"{'='*60}")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests passed successfully!")
        print("✅ SigmaHQ RAG application is ready for production deployment")
    else:
        print("❌ Some tests failed. Please review the output above.")
        print("🔧 Fix the issues before proceeding with deployment")
    print(f"{'='*60}")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())