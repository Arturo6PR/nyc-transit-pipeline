"""
Database connectivity test

Purpose:
- Verify DB credentials and connection

TODO (Team):
- Keep this file simple
"""

from src.config import get_settings
from src.db import get_engine, health_check


def main() -> None:
    engine = get_engine(get_settings().db_url)
    health_check(engine)
    print("DB connection OK")


if __name__ == "__main__":
    main()