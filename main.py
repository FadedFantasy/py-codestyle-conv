"""
Main entry point for Python Style Converter.
Coordinates all components to transform Python code according to configuration.
"""

import sys
import argparse
from pathlib import Path

from config.config_manager import ConfigManager, ConfigValidationError
from core.file_scanner import FileScanner
from core.rule_engine import RuleEngine
from core.output_manager import OutputManager


def main():
    """Main entry point for the Python Style Converter."""
    parser = argparse.ArgumentParser(
        description="Python Style Converter - Transform Python code according to configurable rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s config.json /path/to/project
  %(prog)s config.json file.py
  %(prog)s config.json . --dry-run
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
        '--dry-run',
        action='store_true',
        help='Show what would be changed without actually modifying files'
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
            print(f"Loading configuration from: {args.config}")

        config_manager = ConfigManager(args.config)
        file_scanner = FileScanner(config_manager)
        rule_engine = RuleEngine(config_manager)
        output_manager = OutputManager(config_manager)

        # Validate patterns
        pattern_errors = file_scanner.validate_patterns()
        if pattern_errors:
            print("Configuration errors in file patterns:")
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
            print(f"Error: Target path does not exist: {target_path}")
            sys.exit(1)

        if not files_to_process:
            print("No Python files found matching the configured patterns.")
            sys.exit(0)

        if args.verbose:
            print(f"Found {len(files_to_process)} files to process:")
            for file_path in files_to_process:
                print(f"  - {file_path}")
            print()

        # Process files
        print(f"Processing {len(files_to_process)} files...")

        processing_results = []
        for i, file_path in enumerate(files_to_process, 1):
            if args.verbose:
                print(f"[{i}/{len(files_to_process)}] Processing: {file_path}")

            result = rule_engine.process_file(file_path)
            processing_results.append(result)

            if not result.success:
                print(f"Error processing {file_path}: {result.error_message}")
            elif args.verbose and result.changes_made:
                print(f"  Changes: {', '.join(result.changes_made)}")

        # Handle dry run
        if args.dry_run:
            print("\n" + "="*60)
            print("DRY RUN - No files were modified")
            print("="*60)

            changes_found = False
            for result in processing_results:
                if result.success and result.changes_made:
                    changes_found = True
                    print(f"\nFile: {result.file_path}")
                    print("Changes that would be made:")
                    for change in result.changes_made:
                        print(f"  - {change}")

            if not changes_found:
                print("No changes would be made to any files.")

            return

        # Apply changes (if not dry run)
        output_results = output_manager.process_results(processing_results)

        # Print summary
        output_manager.print_summary(output_results)

        # Exit with appropriate code
        failed_count = len([r for r in output_results if not r.success])
        if failed_count > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except ConfigValidationError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()