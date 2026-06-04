import argparse
import logging
import sys
from src.indexing_tool.config import AppConfig
from src.indexing_tool.orchestrator import SmartIndexerOrchestrator


def setup_logging(log_file: str) -> None:
    """Configures logging to print to console and write to the configuration log file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Entry point for the Google and Bing indexing CLI utility."""
    parser = argparse.ArgumentParser(
        description="Unified Google & Bing Indexing Command Line Interface Tool"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Workflow commands"
    )

    # export sub-command
    subparsers.add_parser(
        "export",
        help="Find published Pelican articles and add new links to the CSV tracking database",
    )

    # inspect sub-command
    inspect_parser = subparsers.add_parser(
        "inspect", help="Check actual index status in Google Search Console"
    )
    group = inspect_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Inspect a specific single URL")
    group.add_argument(
        "--newest", type=int, metavar="N", help="Inspect the N newest URLs in the CSV"
    )
    group.add_argument(
        "--bulk", action="store_true", help="Inspect pending (non-PASS) URLs in the CSV"
    )
    inspect_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of URLs to check in bulk mode (default: 100)",
    )

    # smart sub-command
    smart_parser = subparsers.add_parser(
        "smart",
        help="Inspect status of pending URLs and submit non-indexed ones to Google Indexing API",
    )
    smart_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate indexation submission without invoking API write requests",
    )
    smart_parser.add_argument(
        "--limit",
        type=int,
        default=150,
        help="Maximum number of URLs to check (default: 150)",
    )

    # bing sub-command
    bing_parser = subparsers.add_parser(
        "bing", help="Submit new URLs to Bing IndexNow in a single batch"
    )
    bing_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate IndexNow submission without making API request",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = AppConfig.load_from_file("config.ini")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    setup_logging(config.log_file)
    logger = logging.getLogger("indexing_tool.cli")

    orchestrator = SmartIndexerOrchestrator(config)

    try:
        if args.command == "export":
            orchestrator.export_pelican_links()
        elif args.command == "inspect":
            if args.url:
                orchestrator.run_google_inspect(mode="single", specific_url=args.url)
            elif args.newest:
                orchestrator.run_google_inspect(mode="newest", limit=args.newest)
            elif args.bulk:
                orchestrator.run_google_inspect(mode="bulk", limit=args.limit)
        elif args.command == "smart":
            orchestrator.run_smart_google_indexing(
                limit=args.limit, dry_run=args.dry_run
            )
        elif args.command == "bing":
            orchestrator.run_bing_submission(dry_run=args.dry_run)
    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
