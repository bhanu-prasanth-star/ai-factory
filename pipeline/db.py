"""Thin helpers around psycopg2 so the rest of the pipeline never
touches connection/cursor boilerplate directly."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def fetch_one(query, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


def fetch_all(query, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def execute(query, params=None, returning=False):
    """For INSERT/UPDATE. Pass returning=True if the query ends in
    RETURNING <col> and you want that row back."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            result = cur.fetchone() if returning else None
            conn.commit()
            return result
