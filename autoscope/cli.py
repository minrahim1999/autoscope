"""Command-line entry point."""

import argparse
import os
import sys

from autoscope.config.loader import load_config
from autoscope.core.runner import run_tests
from autoscope.crawler import crawl, save_crawl_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="autoscope",
        description="Run web and Android tests, or crawl a website.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser("run", help="Discover and run unittest-based tests.")
    run_parser.add_argument(
        "--config",
        "-c",
        default="config.yaml",
        help="Path to config file (YAML or JSON).",
    )
    run_parser.add_argument(
        "--tag",
        "-t",
        action="append",
        default=[],
        help="Filter tests by tag (web, mobile). Can be repeated.",
    )
    run_parser.add_argument(
        "--pattern",
        "-p",
        default="test_*.py",
        help="Test file discovery pattern.",
    )
    run_parser.add_argument(
        "--start-dir",
        "-d",
        default=".",
        help="Directory to discover tests from.",
    )

    # crawl
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a website starting from a URL.")
    crawl_parser.add_argument(
        "--config",
        "-c",
        default="config.yaml",
        help="Path to config file (YAML or JSON).",
    )
    crawl_parser.add_argument(
        "--url",
        "-u",
        required=True,
        help="Starting URL to crawl.",
    )
    crawl_parser.add_argument(
        "--username",
        default=os.environ.get("CRAWL_USERNAME"),
        help="Username for automatic login. Falls back to CRAWL_USERNAME env var.",
    )
    crawl_parser.add_argument(
        "--password",
        default=os.environ.get("CRAWL_PASSWORD"),
        help="Password for automatic login. Falls back to CRAWL_PASSWORD env var.",
    )
    crawl_parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum crawl depth (default: 3).",
    )
    crawl_parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum pages to visit (default: 50).",
    )
    crawl_parser.add_argument(
        "--no-screenshot",
        action="store_true",
        help="Disable per-page screenshots.",
    )

    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "run":
        success = run_tests(
            config=config,
            start_dir=args.start_dir,
            pattern=args.pattern,
            tags=args.tag,
        )
        return 0 if success else 1

    if args.command == "crawl":
        result = crawl(
            url=args.url,
            username=args.username,
            password=args.password,
            config=config,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            screenshot=not args.no_screenshot,
        )
        json_path, html_path = save_crawl_report(result, config)
        data = result.to_dict()
        summary = data["summary"]
        print(
            f"\nCrawl finished: {summary['total']} pages, "
            f"{summary['ok']} OK, {summary['broken']} broken"
        )
        print(f"Reports written:\n  JSON: {json_path}\n  HTML: {html_path}")
        return 0 if summary["broken"] == 0 else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
