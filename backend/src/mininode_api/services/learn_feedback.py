"""PostgreSQL persistence for anonymous Mininode Learn feedback."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator
from uuid import UUID, uuid4

import psycopg


@contextmanager
def _connection() -> Iterator[psycopg.Connection]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    with psycopg.connect(database_url) as connection:
        yield connection


def create_feedback(*, ebook_id: str, rating: int) -> UUID:
    feedback_id = uuid4()
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learn_feedback (
                id UUID PRIMARY KEY,
                ebook_id TEXT NOT NULL,
                rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
                topic TEXT,
                comment VARCHAR(500),
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "INSERT INTO learn_feedback (id, ebook_id, rating) VALUES (%s, %s, %s)",
            (feedback_id, ebook_id, rating),
        )
    return feedback_id


def update_feedback(
    feedback_id: UUID, *, topic: str | None = None, comment: str | None = None
) -> bool:
    assignments: list[str] = []
    values: list[object] = []
    if topic is not None:
        assignments.append("topic = %s")
        values.append(topic)
    if comment is not None:
        assignments.append("comment = %s")
        values.append(comment)
    if not assignments:
        return True

    values.append(feedback_id)
    with _connection() as connection, connection.cursor() as cursor:
        if comment is not None:
            cursor.execute("SELECT rating FROM learn_feedback WHERE id = %s", (feedback_id,))
            result = cursor.fetchone()
            if result and result[0] > 3:
                raise ValueError("Comments are only accepted for ratings from 1 to 3")
        cursor.execute(
            f"UPDATE learn_feedback SET {', '.join(assignments)} WHERE id = %s",
            values,
        )
        return cursor.rowcount == 1
