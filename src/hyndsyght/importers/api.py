"""/api/import/activitywatch — the dashboard's import wizard, one bucket per request.

One request per bucket keeps each under a minute and lets the wizard show
progress without a job queue.
"""

import sqlite3
import urllib.error
import urllib.parse
from contextlib import closing
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hyndsyght import paths
from hyndsyght.categorize.rules import load_rules
from hyndsyght.importers import activitywatch as aw
from hyndsyght.store import db


class BucketBody(BaseModel):
    url: str = aw.DEFAULT_URL
    bucket: str


def register_import_routes(router: APIRouter) -> None:
    @router.get("/api/import/activitywatch")
    def aw_overview(url: str = aw.DEFAULT_URL) -> dict[str, Any]:
        buckets = _buckets(url)
        with closing(_connect()) as conn:
            return {"url": url, **aw.overview(buckets, conn)}

    @router.post("/api/import/activitywatch")
    def aw_import_bucket(body: BucketBody) -> dict[str, Any]:
        bucket = _buckets(body.url).get(body.bucket)
        if bucket is None or bucket.get("client") not in aw.SOURCES:
            raise HTTPException(
                404, f"No window or AFK bucket {body.bucket} at {body.url}"
            )
        with closing(_connect()) as conn:
            until = aw.native_start(conn)
            source = aw.ApiSource(body.url)
            result = aw.import_bucket(
                conn, source, body.bucket, bucket, load_rules(), until, write=True
            )
        return asdict(result)

    @router.delete("/api/import/activitywatch")
    def aw_remove() -> dict[str, int]:
        with closing(_connect()) as conn:
            return {"removed": aw.remove_imported(conn)}


def _buckets(url: str) -> dict[str, aw.Bucket]:
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise HTTPException(400, f"{url} is not an http address")
    try:
        return aw.ApiSource(url).buckets()
    except urllib.error.URLError as error:
        raise HTTPException(502, f"Can't reach ActivityWatch at {url}.") from error


def _connect() -> sqlite3.Connection:
    return db.connect(paths.db_path())
