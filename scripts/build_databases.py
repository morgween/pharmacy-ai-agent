"""build sqlite databases from json sources"""
import argparse
import os
import sys

from backend.config import settings
from backend.data_sources.medications_db import MedicationsDB
from backend.models.user import UserDatabase


def _remove_file(path: str) -> None:
    """remove file if it exists."""
    if os.path.exists(path):
        os.remove(path)


def main() -> int:
    """build and seed medication and user databases."""
    parser = argparse.ArgumentParser(description="build local sqlite databases")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete existing database files before rebuilding"
    )
    parser.add_argument(
        "--skip-prescriptions",
        action="store_true",
        help="skip seeding demo prescriptions"
    )
    args = parser.parse_args()

    if args.reset:
        _remove_file(settings.medications_db_path)
        _remove_file(settings.user_db_path)

    medications_db = MedicationsDB(db_path=settings.medications_db_path)
    medications_db.seed_from_json(force=args.reset)

    user_db = UserDatabase(db_path=settings.user_db_path)
    user_db.seed_users(force=args.reset)
    if not args.skip_prescriptions:
        user_db.seed_prescriptions(force=args.reset)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
