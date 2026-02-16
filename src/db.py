"""
Database helpers

Purpose:
- Create SQLAlchemy engine
- Run basic connectivity checks

TODO (Team):
- Insert/query helpers should go in db_writer.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(db_url: str) -> Engine:
    """Part 1: Create engine"""
    return create_engine(db_url, pool_pre_ping=True, future=True)


def health_check(engine: Engine) -> None:
    """Part 2: Simple DB check"""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1;"))
        conn.commit()