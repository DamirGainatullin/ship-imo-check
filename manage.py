import argparse
import asyncio
import logging

from app.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ship IMO Check bot and indexing tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index files from sources directory")
    index_parser.add_argument(
        "--force",
        action="store_true",
        help="Reindex all files even when content hash is unchanged",
    )

    run_bot_parser = subparsers.add_parser("run-bot", help="Run Telegram bot")
    run_bot_parser.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Drop pending updates on start",
    )

    check_parser = subparsers.add_parser("check", help="Check IMO in local index")
    check_parser.add_argument("imo", help="IMO number")

    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    logging.getLogger("pdfplumber").setLevel(logging.ERROR)
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "index":
        from app.indexer import index_sources

        index_sources(settings, force=args.force)
        return

    if args.command == "check":
        from app.search import find_imo

        matches = find_imo(settings, args.imo)
        if not matches:
            print("No matches found")
            return

        for match in matches:
            print(
                f"{match.document_path} | location={match.location} | "
                f"snippet={match.snippet}"
            )
        return

    if args.command == "run-bot":
        from app.bot import run_bot

        asyncio.run(
            run_bot(
                settings=settings,
                drop_pending_updates=args.drop_pending_updates,
            )
        )
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
