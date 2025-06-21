#!/usr/bin/env python3
"""
Convenience script to run callback tests with different options.

Usage:
    python run_callback_tests.py                    # Run all callback tests
    python run_callback_tests.py --coverage         # Run with coverage report
    python run_callback_tests.py --verbose          # Run with verbose output
    python run_callback_tests.py --fast             # Run only fast tests
    python run_callback_tests.py --help             # Show help
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Info:", result.stderr)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Run callback tests for the Blue Thumb Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_callback_tests.py                    # Run all callback tests
    python run_callback_tests.py --coverage         # Run with coverage report  
    python run_callback_tests.py --verbose          # Run with verbose output
    python run_callback_tests.py --shared-only      # Run only shared callback tests
        """
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Run tests with coverage report'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true', 
        help='Run tests with verbose output'
    )
    
    parser.add_argument(
        '--shared-only', '-s',
        action='store_true',
        help='Run only shared callback tests'
    )
    
    parser.add_argument(
        '--fail-fast', '-x',
        action='store_true',
        help='Stop on first failure'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output'
    )
    
    args = parser.parse_args()
    
    # Verify we're in the right directory
    if not Path('callbacks').exists():
        print("❌ Error: Please run this script from the project root directory.")
        print("   (The directory should contain a 'callbacks' folder)")
        sys.exit(1)
    
    # Build the pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Determine test path
    if args.shared_only:
        test_path = 'tests/callbacks/test_shared_callbacks.py'
        description = "Running shared callback tests"
    else:
        test_path = 'tests/callbacks/'
        description = "Running all callback tests"
    
    cmd.append(test_path)
    
    # Add options
    if args.verbose:
        cmd.append('-v')
    elif args.quiet:
        cmd.append('-q')
    else:
        cmd.append('-v')  # Default to verbose
    
    if args.fail_fast:
        cmd.append('-x')
    
    if args.coverage:
        cmd.extend(['--cov=callbacks', '--cov-report=term-missing', '--cov-report=html'])
        description += " with coverage"
    
    # Add some useful default options
    cmd.extend(['--tb=short'])  # Shorter traceback format
    
    print("🧪 Blue Thumb Dashboard - Callback Test Runner")
    print("=" * 50)
    
    # Run the tests
    success = run_command(cmd, description)
    
    if args.coverage and success:
        print("\n📊 Coverage report generated!")
        print("   • Terminal report shown above")
        print("   • HTML report: htmlcov/index.html")
        print("   • Open with: open htmlcov/index.html")
    
    if success:
        print(f"\n🎉 All tests passed! Your callback logic is working correctly.")
        sys.exit(0)
    else:
        print(f"\n💥 Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == '__main__':
    main() 