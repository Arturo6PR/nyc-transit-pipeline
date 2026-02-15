"""
NYC Transit Delay Prediction Project
Config module

Purpose:
- Load environment variables
- Centralize API and DB settings
"""

from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Part 1: Load .env file
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """
    Part 2: Settings container

    TODO (Team):
    - Add new config fields here if more data sources are introduced
    """

    # MTA
    mta_api_key: str
    mta_base_url: str
    mta_feeds: list[str]

    # Database
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    @property
    def db_url(self) -> str:
        """Part 3: SQLAlchemy DB URL"""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


def _split_csv(value: str) -> list[str]:
    """Part 4: Helper for comma-separated env vars"""
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def get_settings() -> Settings:
    """Part 5: Build Settings from environment"""
    return Settings(
        mta_api_key=os.getenv("MTA_API_KEY", ""),
        mta_base_url=os.getenv(
            "MTA_BASE_URL",
            "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds",
        ),
        mta_feeds=_split_csv(os.getenv("MTA_FEEDS", "")),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "nyc_transit"),
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=os.getenv("DB_PASSWORD", "postgres"),
    )