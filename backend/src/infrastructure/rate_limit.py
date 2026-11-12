import time

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.infrastructure.database import RateBucket


def limit(db: Session, key: str, maximum: int, seconds: int = 60):
    window = int(time.time()) // seconds
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    stmt = insert(RateBucket).values(key=key, window=window, count=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[RateBucket.key, RateBucket.window],
        set_={"count": RateBucket.count + 1},
    ).returning(RateBucket.count)
    count = db.scalar(stmt)
    # All buckets use a 60-second window; keep the table bounded.
    db.execute(delete(RateBucket).where(RateBucket.window < window - 2))
    db.commit()
    if count > maximum:
        raise HTTPException(
            429, "Слишком много запросов. Попробуйте через минуту", headers={"Retry-After": "60"}
        )
