"""
Main entry point for Python Style Converter.
Always uses cross-file mode with smart GUI behavior.
"""

import sys
import argparse
from pathlib import Path

from config.config_manager import ConfigManager, ConfigValidationError
from core.file_scanner import FileScanner
from core.rule_engine import RuleEngine
from core.output_manager import OutputManager
from core.global_symbol_tracker import GlobalSymbolTracker


def main():
    """Main entry point for the Python Style Converter."""
    parser = argparse.ArgumentParser(
        description="Python Style Converter - Transform Python code with cross-file coordination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s config.json /path/to/project
  %(prog)s config.json file.py
  %(prog)s config.json . --verbose
        """
    )

    parser.add_argument(
        'config',
        help='Path to JSON configuration file'
    )

    parser.add_argument(
        'target',
        help='Target file or directory to process'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    try:
        # Initialize components
        if args.verbose:
            print(f"📋 Loading configuration from: {args.config}")

        config_manager = ConfigManager(args.config)
        file_scanner = FileScanner(config_manager)

        # Validate patterns
        pattern_errors = file_scanner.validate_patterns()
        if pattern_errors:
            print("❌ Configuration errors in file patterns:")
            for error in pattern_errors:
                print(f"  - {error}")
            sys.exit(1)

        # Discover files to process
        target_path = Path(args.target)

        if target_path.is_file():
            files_to_process = file_scanner.scan_file(str(target_path))
        elif target_path.is_dir():
            files_to_process = file_scanner.scan_directory(str(target_path))
        else:
            print(f"❌ Error: Target path does not exist: {target_path}")
            sys.exit(1)

        if not files_to_process:
            print("ℹ️  No Python files found matching the configured patterns.")
            sys.exit(0)

        if args.verbose:
            print(f"📁 Found {len(files_to_process)} files to process:")
            for file_path in files_to_process:
                print(f"  - {file_path}")
            print()

        # Always use cross-file processing
        result = process_cross_file_mode(config_manager, files_to_process, args)

        # Handle results
        if result['success']:
            print(f"✅ Processing completed successfully!")
            sys.exit(0)
        else:
            print(f"❌ Processing completed with errors.")
            sys.exit(1)

    except ConfigValidationError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def process_cross_file_mode(config_manager: ConfigManager,
                          files_to_process: list,
                          args) -> dict:
    """
    Process files with cross-file coordination and smart GUI behavior.
    """
    try:
        # Step 1: Analyze project for cross-file symbols
        print("🔍 Step 1: Analyzing project for cross-file symbols...")
        project_root = Path(args.target) if Path(args.target).is_dir() else Path(args.target).parent

        symbol_tracker = GlobalSymbolTracker(project_root)
        global_symbol_map = symbol_tracker.analyze_project(files_to_process)

        if args.verbose:
            print(f"   📊 Analysis complete: found symbols across {len(files_to_process)} files")

        # Step 2: Process all files with RuleEngine
        print("🎯 Step 2: Processing files with cross-file transformations...")

        rule_engine = RuleEngine(config_manager, global_symbol_map)
        project_result = rule_engine.process_project(files_to_process)

        if not project_result.success:
            print(f"❌ Error in transformation processing: {project_result.error_message}")
            return {'success': False}

        if not project_result.file_results:
            print("ℹ️  No changes needed - all files already follow the configured conventions")
            return {'success': True}

        if args.verbose and project_result.global_transformations:
            print(f"   🎯 Generated {len(project_result.global_transformations)} global transformations")

        # Step 3: Apply changes with smart output manager
        print("💾 Step 3: Applying changes with smart GUI...")
        print("   📋 GUI will show only definition files")
        print("   🔄 Usage files will be updated automatically")

        output_manager = OutputManager(config_manager)
        output_results = output_manager.process_cross_file_results(project_result.file_results)

        # Print summary
        output_manager.print_cross_file_summary(output_results)

        # Check for failures
        failed_count = len([r for r in output_results if not r.success])
        user_quit = any(r.error_message == "USER_QUIT" for r in output_results)

        if user_quit:
            print("⚠️  Processing stopped by user")
            return {'success': False}

        return {
            'success': failed_count == 0,
            'failed_count': failed_count,
            'total_count': len(output_results)
        }

    except Exception as e:
        print(f"❌ Error in cross-file processing: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return {'success': False}


if __name__ == "__main__":
    main()