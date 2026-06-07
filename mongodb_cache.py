import os
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient
from pymongo.errors import PyMongoError

_indexes_ready = False
_client = None


def is_configured():
    return bool(os.getenv("MONGODB_URI"))


def _validate_uri(uri):
    if "<" in uri or ">" in uri:
        return (
            "MONGODB_URI still contains < or > characters. Atlas shows "
            "<password> as a placeholder — replace it with your real "
            "password only, without angle brackets."
        )
    return None


def _cache_ttl_hours():
    return int(os.getenv("CACHE_TTL_HOURS", "6"))


def _db_name():
    return os.getenv("MONGODB_DB_NAME", "developer_growth_tracker")


def _normalize_username(username):
    return username.strip().lower()


def _friendly_mongo_error(exc):
    message = str(exc).lower()

    if "bad auth" in message or "authentication failed" in message:
        return (
            "MongoDB authentication failed. In Atlas, use the Database User "
            "password (not your Atlas login). URL-encode special characters "
            "in the password, or reset it to letters and numbers only."
        )

    if "server selection" in message or "timed out" in message:
        return (
            "Could not reach MongoDB Atlas. In Atlas → Network Access, "
            "allow your current IP address."
        )

    if "tls" in message or "ssl" in message:
        return (
            "MongoDB TLS connection failed. Copy a fresh mongodb+srv:// "
            "connection string from Atlas → Connect → Drivers → Python."
        )

    return f"MongoDB error: {exc}"


def _get_client():
    global _client
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return None

    if _client is None:
        kwargs = {
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 10000,
        }
        auth_source = os.getenv("MONGODB_AUTH_SOURCE")
        if auth_source:
            kwargs["authSource"] = auth_source

        _client = MongoClient(uri, **kwargs)

    return _client


def _get_collection():
    client = _get_client()
    if client is None:
        return None

    return client[_db_name()]["profile_cache"]


def _ensure_indexes(collection):
    global _indexes_ready
    if _indexes_ready:
        return

    collection.create_index("username", unique=True)
    collection.create_index("expires_at", expireAfterSeconds=0)
    _indexes_ready = True


def get_cached_profile(username):
    uri_error = _validate_uri(os.getenv("MONGODB_URI", ""))
    if uri_error:
        return None

    collection = _get_collection()
    if collection is None:
        return None

    try:
        _ensure_indexes(collection)
        document = collection.find_one({"username": _normalize_username(username)})
        if not document:
            return None

        return {
            "user": document["user"],
            "analytics": document.get("analytics"),
            "analytics_error": document.get("analytics_error"),
            "contributions": document.get("contributions"),
            "contributions_error": document.get("contributions_error"),
            "warnings": document.get("warnings", []),
            "cached_at": document["cached_at"],
        }
    except PyMongoError:
        return None


def save_profile_cache(username, profile_data):
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return False, "MONGODB_URI is not set in .env."

    uri_error = _validate_uri(uri)
    if uri_error:
        return False, uri_error

    collection = _get_collection()
    if collection is None:
        return False, "MONGODB_URI is not set in .env."

    normalized = _normalize_username(username)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=_cache_ttl_hours())

    document = {
        "username": normalized,
        "user": profile_data["user"],
        "analytics": profile_data.get("analytics"),
        "analytics_error": profile_data.get("analytics_error"),
        "contributions": profile_data.get("contributions"),
        "contributions_error": profile_data.get("contributions_error"),
        "warnings": profile_data.get("warnings", []),
        "cached_at": now,
        "expires_at": expires_at,
    }

    try:
        collection.database.client.admin.command("ping")
        _ensure_indexes(collection)
        result = collection.update_one(
            {"username": normalized},
            {"$set": document},
            upsert=True,
        )

        if result.upserted_id is None and result.modified_count == 0 and result.matched_count == 0:
            return False, "MongoDB write did not create or update a document."

        saved = collection.find_one({"username": normalized}, {"username": 1})
        if not saved:
            return False, (
                "MongoDB write appeared to succeed but the document could not "
                "be read back. Check that MONGODB_DB_NAME matches your Atlas "
                f"database (currently '{_db_name()}')."
            )

        return True, None
    except PyMongoError as exc:
        return False, _friendly_mongo_error(exc)


def test_connection():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        return False, "MONGODB_URI is not set in .env."

    uri_error = _validate_uri(uri)
    if uri_error:
        return False, uri_error

    collection = _get_collection()
    if collection is None:
        return False, "MONGODB_URI is not set in .env."

    try:
        collection.database.client.admin.command("ping")
        _ensure_indexes(collection)
        count = collection.count_documents({})
        return True, f"Connected to '{_db_name()}.profile_cache' ({count} document(s))."
    except PyMongoError as exc:
        return False, _friendly_mongo_error(exc)


def format_cached_at(cached_at):
    if cached_at is None:
        return ""

    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=timezone.utc)

    return cached_at.astimezone(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
