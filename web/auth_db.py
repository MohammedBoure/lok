#!/usr/bin/env python3
"""
SaaS Multi-Tenant Authentication, Sessions & Quotas Database Module (web/auth_db.py).
Manages commercial merchant accounts, password hashing, session tokens, expiration,
daily/weekly quotas, and video generation audit history in SQLite (outputs/saas_platform.db).

Author: MohammedBoure <datasupabase@gmail.com>
Role: Backend Architecture & Systems Specialist (agy11)
Branch: backend/agy11-session-auth-tts-voice-samples
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("auth_db")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

# Ensure repository root and default DB path
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "outputs" / "saas_platform.db"

# ---------------------------------------------------------------------------
# Password Hashing & Verification (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

DEFAULT_PBKDF2_ITERATIONS = 100_000


def hash_password(password: str, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with a cryptographically secure salt.
    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"


def verify_password(password: str, hashed_password: Optional[str]) -> bool:
    """
    Verify plaintext password against a stored PBKDF2-HMAC-SHA256 hash or plaintext fallback.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not password or not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt = parts[2]
            expected_hash = parts[3]
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            return hmac.compare_digest(derived.hex(), expected_hash)
        # Fallback for plain tokens or direct matching in test/dev
        return hmac.compare_digest(password.strip(), hashed_password.strip())
    except Exception as exc:
        logger.debug("verify_password encountered exception: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Pre-seeded Accounts (Master Admin + Commercial Merchants)
# ---------------------------------------------------------------------------

MASTER_ADMIN_USERNAME = "pluto"
MASTER_ADMIN_PASSWORD = "plutosw4"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_MERCHANT_PASSWORD = "merchant123"

PRESEEDED_ACCOUNTS: List[Dict[str, Any]] = [
    {
        "username": MASTER_ADMIN_USERNAME,
        "business_name": "منصة إدارة النظام (lok Master Admin)",
        "business_category": "tech",
        "role": "admin",
        "is_active": 1,
        "status": "active",
        "valid_from": "2024-01-01",
        "expires_at": "2099-12-31",
        "daily_quota": 9999,
        "weekly_quota": 99999,
        "auth_token": "token_admin_pluto",
        "default_password": MASTER_ADMIN_PASSWORD,
    },
    {
        "username": "admin",
        "business_name": "منصة إدارة النظام (SaaS Master Admin)",
        "business_category": "tech",
        "role": "admin",
        "is_active": 1,
        "status": "active",
        "valid_from": "2024-01-01",
        "expires_at": "2099-12-31",
        "daily_quota": 9999,
        "weekly_quota": 99999,
        "auth_token": "token_admin_master",
        "default_password": DEFAULT_ADMIN_PASSWORD,
    },
    {
        "username": "algiers_luxury_re",
        "business_name": "عقارات الجزائر الفاخرة",
        "business_category": "real_estate",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 10,
        "weekly_quota": 50,
        "auth_token": "token_algiers_luxury_re",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "oran_seafood_bistro",
        "business_name": "مطعم وهران للمأكولات البحرية",
        "business_category": "restaurant",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 8,
        "weekly_quota": 40,
        "auth_token": "token_oran_seafood_bistro",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "annaba_elegance_couture",
        "business_name": "أزياء عنابة الراقية",
        "business_category": "fashion",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 6,
        "weekly_quota": 30,
        "auth_token": "token_annaba_elegance_couture",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "constantine_smart_tech",
        "business_name": "قسنطينة للأجهزة الذكية",
        "business_category": "tech",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 8,
        "weekly_quota": 40,
        "auth_token": "token_constantine_smart_tech",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "batna_auto_showroom",
        "business_name": "معرض باتنة للسيارات",
        "business_category": "automotive",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 5,
        "weekly_quota": 25,
        "auth_token": "token_batna_auto_showroom",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "ghardaia_oasis_carpets",
        "business_name": "زرابي وواحات غرداية التقليدية",
        "business_category": "handcrafts",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 5,
        "weekly_quota": 25,
        "auth_token": "token_ghardaia_oasis_carpets",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "bejaia_coast_tours",
        "business_name": "وكالة بجاية للسياحة البحرية",
        "business_category": "tourism",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 7,
        "weekly_quota": 35,
        "auth_token": "token_bejaia_coast_tours",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "setif_home_decor",
        "business_name": "سطيف للمفروشات والديكور المنزلي",
        "business_category": "ecommerce",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 6,
        "weekly_quota": 30,
        "auth_token": "token_setif_home_decor",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "blida_wellness_clinic",
        "business_name": "عيادة البليدة الطبية والصحية",
        "business_category": "clinic",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 5,
        "weekly_quota": 25,
        "auth_token": "token_blida_wellness_clinic",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
    {
        "username": "algiers_pro_fitness",
        "business_name": "نادي العاصمة للرشاقة واللياقة",
        "business_category": "fitness",
        "role": "merchant",
        "is_active": 1,
        "expires_at": "2027-12-31",
        "daily_quota": 8,
        "weekly_quota": 40,
        "auth_token": "token_algiers_pro_fitness",
        "default_password": DEFAULT_MERCHANT_PASSWORD,
    },
]


# ---------------------------------------------------------------------------
# Database Initialization & Connection Helpers
# ---------------------------------------------------------------------------

def _resolve_db_path(db_path: Optional[Union[str, Path]] = None) -> Path:
    """Resolve and ensure the parent directory of the SQLite database exists."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection with row_factory enabled."""
    resolved_path = _resolve_db_path(db_path)
    conn = sqlite3.connect(str(resolved_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """
    Initialize SQLite database schema and pre-seed admin and 10 diverse commercial
    merchant accounts with hashed passwords if the users table is currently empty.
    Applies non-destructive schema migrations (e.g. password_hash, sessions table).
    """
    resolved_path = _resolve_db_path(db_path)
    conn = sqlite3.connect(str(resolved_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            # 1. Users table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    business_name TEXT NOT NULL,
                    business_category TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'merchant',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'active',
                    valid_from TEXT,
                    expires_at TEXT,
                    daily_quota INTEGER NOT NULL DEFAULT 5,
                    weekly_quota INTEGER NOT NULL DEFAULT 25,
                    auth_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Ensure columns exist if table was created earlier without them
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "password_hash" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")
            if "valid_from" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN valid_from TEXT;")
            if "status" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active';")

            # 2. Sessions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_token TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

            # 3. Video generations table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    job_id TEXT NOT NULL,
                    video_url TEXT,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

            # 4. User activity logs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

            # Create indexes for fast quota, session, token, and activity lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_token ON users(auth_token);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generations_user_date ON video_generations(user_id, created_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_date ON user_activity_logs(user_id, created_at);")

            # Check if seeding or password upgrade is required
            cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
            user_count = cursor.fetchone()["cnt"]

            if user_count == 0:
                logger.info("Pre-seeding SaaS database with master admin pluto and commercial merchant accounts...")
                for acc in PRESEEDED_ACCOUNTS:
                    pwd_hash = hash_password(acc.get("default_password", DEFAULT_MERCHANT_PASSWORD))
                    cursor.execute(
                        """
                        INSERT INTO users (
                            username, password_hash, business_name, business_category, role,
                            is_active, status, valid_from, expires_at, daily_quota, weekly_quota, auth_token
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            acc["username"],
                            pwd_hash,
                            acc["business_name"],
                            acc["business_category"],
                            acc.get("role", "merchant"),
                            acc.get("is_active", 1),
                            acc.get("status", "active"),
                            acc.get("valid_from", "2024-01-01"),
                            acc.get("expires_at"),
                            acc.get("daily_quota", 5),
                            acc.get("weekly_quota", 25),
                            acc["auth_token"],
                        ),
                    )
                logger.info("Successfully seeded %d commercial accounts into %s", len(PRESEEDED_ACCOUNTS), resolved_path)
            else:
                # Update existing preseeded users whose password_hash is empty or NULL
                for acc in PRESEEDED_ACCOUNTS:
                    pwd_hash = hash_password(acc.get("default_password", DEFAULT_MERCHANT_PASSWORD))
                    cursor.execute(
                        """
                        UPDATE users
                        SET password_hash = ?
                        WHERE username = ? AND (password_hash IS NULL OR password_hash = '');
                        """,
                        (pwd_hash, acc["username"]),
                    )

            # Ensure master administrator pluto exists and is updated with plutosw4
            pluto_hash = hash_password(MASTER_ADMIN_PASSWORD)
            cursor.execute("SELECT id, password_hash FROM users WHERE username = 'pluto';")
            pluto_row = cursor.fetchone()
            if not pluto_row:
                cursor.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, business_name, business_category, role,
                        is_active, status, valid_from, expires_at, daily_quota, weekly_quota, auth_token
                    ) VALUES (
                        'pluto', ?, 'منصة إدارة النظام (lok Master Admin)', 'tech', 'admin',
                        1, 'active', '2024-01-01', '2099-12-31', 9999, 99999, 'token_admin_pluto'
                    );
                    """,
                    (pluto_hash,),
                )
                pid = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO user_activity_logs (user_id, event_type, details) VALUES (?, 'system_init', 'Master admin pluto auto-provisioned');",
                    (pid,),
                )
            else:
                # Update pluto to ensure plutosw4 password, admin role, and active status
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = ?, role = 'admin', is_active = 1, status = 'active'
                    WHERE username = 'pluto';
                    """,
                    (pluto_hash,),
                )
    finally:
        conn.close()


# Ensure DB schema and seed on module import
init_db()


# ---------------------------------------------------------------------------
# Serialization & User Mapping Helpers
# ---------------------------------------------------------------------------

def _row_to_user_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """
    Convert SQLite Row to structured user dictionary.
    Excludes sensitive password_hash from general public dictionaries.
    """
    if not row:
        return None

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    keys = row.keys() if hasattr(row, "keys") else []

    valid_from = row["valid_from"] if "valid_from" in keys else None
    expires_at = row["expires_at"] if "expires_at" in keys else None
    raw_status = row["status"] if "status" in keys else "active"
    is_active = bool(row["is_active"])

    # Compute effective status: active, suspended, expired, pending
    if not is_active or raw_status in ("suspended", "inactive"):
        status = "suspended"
    elif expires_at and str(expires_at).strip() and str(expires_at).strip()[:10] < today_str:
        status = "expired"
    elif valid_from and str(valid_from).strip() and str(valid_from).strip()[:10] > today_str:
        status = "pending"
    else:
        status = raw_status or "active"

    return {
        "id": row["id"],
        "username": row["username"],
        "business_name": row["business_name"],
        "business_category": row["business_category"],
        "role": row["role"],
        "is_active": is_active and status == "active",
        "status": status,
        "valid_from": valid_from,
        "expires_at": expires_at,
        "daily_quota": row["daily_quota"],
        "weekly_quota": row["weekly_quota"],
        "auth_token": row["auth_token"],
        "created_at": str(row["created_at"]),
    }


# ---------------------------------------------------------------------------
# Session Management Methods
# ---------------------------------------------------------------------------

DEFAULT_SESSION_DURATION_SECONDS = 7 * 86400  # 7 days


def create_session(
    user_id: int,
    duration_seconds: int = DEFAULT_SESSION_DURATION_SECONDS,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Create a new authenticated session token for a user.
    Returns session details dictionary including session_token and expires_at.
    """
    session_token = f"sess_{uuid.uuid4().hex}_{secrets.token_hex(8)}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=duration_seconds)
    expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (session_token, user_id, expires_at)
                VALUES (?, ?, ?);
                """,
                (session_token, user_id, expires_at_str),
            )
            session_id = cursor.lastrowid
            return {
                "id": session_id,
                "session_token": session_token,
                "user_id": user_id,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at": expires_at_str,
                "duration_seconds": duration_seconds,
            }
    finally:
        conn.close()


def get_session(
    session_token: Optional[str],
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve session record and attached user profile by session token.
    Validates expiration and user active state; if expired, deletes the session and returns None.
    """
    if not session_token or not str(session_token).strip():
        return None

    clean_token = str(session_token).strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                s.id AS session_id,
                s.session_token,
                s.user_id,
                s.created_at AS session_created_at,
                s.expires_at AS session_expires_at,
                u.*
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ?
            LIMIT 1;
            """,
            (clean_token,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Check session expiration against UTC
        exp_str = str(row["session_expires_at"]).strip()
        try:
            exp_dt = datetime.fromisoformat(exp_str)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        except Exception:
            exp_dt = datetime.strptime(exp_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        if exp_dt < now_utc:
            # Session expired; cleanup asynchronously
            with conn:
                conn.execute("DELETE FROM sessions WHERE id = ?;", (row["session_id"],))
            return None

        # Check if user is active
        if not bool(row["is_active"]):
            return None

        user_dict = {
            "id": row["id"],
            "username": row["username"],
            "business_name": row["business_name"],
            "business_category": row["business_category"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "expires_at": row["expires_at"],
            "daily_quota": row["daily_quota"],
            "weekly_quota": row["weekly_quota"],
            "auth_token": row["auth_token"],
            "created_at": str(row["created_at"]),
        }

        return {
            "session_id": row["session_id"],
            "session_token": row["session_token"],
            "user_id": row["user_id"],
            "created_at": str(row["session_created_at"]),
            "expires_at": exp_str,
            "user": user_dict,
        }
    finally:
        conn.close()


def delete_session(
    session_token: Optional[str],
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Delete / invalidate a session token."""
    if not session_token or not str(session_token).strip():
        return False

    clean_token = str(session_token).strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_token = ?;", (clean_token,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def cleanup_expired_sessions(db_path: Optional[Union[str, Path]] = None) -> int:
    """Purge all expired session records from the database."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE datetime(expires_at) < datetime('now');")
            return cursor.rowcount
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Authentication & User Management Methods
# ---------------------------------------------------------------------------

def authenticate_token(token: Optional[str], db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate user via permanent auth token or active session token.
    Strips 'Bearer ' prefix if present.
    """
    if not token or not str(token).strip():
        return None

    clean_token = str(token).strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    # 1. Check if token is an active session token
    sess = get_session(clean_token, db_path)
    if sess and sess.get("user"):
        return sess["user"]

    # 2. Check if token is a permanent merchant auth_token
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE auth_token = ? LIMIT 1;", (clean_token,))
        row = cursor.fetchone()
        return _row_to_user_dict(row)
    finally:
        conn.close()


def authenticate_credentials(
    username: str,
    password_or_token: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate user via username and password/token, or by username alone
    for 1-tap demo/merchant selection.
    When password_or_token is provided, verifies password hash or permanent auth token.
    """
    if not username or not str(username).strip():
        return None

    clean_username = str(username).strip()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? LIMIT 1;", (clean_username,))
        row = cursor.fetchone()
        if not row:
            return None

        # If credentials provided, verify against password_hash or auth_token
        if password_or_token is not None and str(password_or_token).strip() != "":
            candidate = str(password_or_token).strip()
            if candidate.lower().startswith("bearer "):
                candidate = candidate[7:].strip()

            # 1. Verify against password hash
            pwd_hash = row["password_hash"]
            if pwd_hash and verify_password(candidate, pwd_hash):
                return _row_to_user_dict(row)

            # 2. Verify against permanent auth token
            if row["auth_token"] and hmac.compare_digest(candidate, str(row["auth_token"])):
                return _row_to_user_dict(row)

            # Credentials failed verification
            return None

        # Admin accounts require password or token verification
        if row["role"] == "admin" and (password_or_token is None or str(password_or_token).strip() == ""):
            return None

        # If no password/token provided (1-tap merchant selection)
        return _row_to_user_dict(row)
    finally:
        conn.close()


def authenticate_user(
    username: str,
    password_or_token: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate user via username and password/token.
    Guarantees master admin 'pluto' with password 'plutosw4' authenticates with role 'admin'.
    """
    return authenticate_credentials(username=username, password_or_token=password_or_token, db_path=db_path)


def log_user_event(
    user_id: Optional[int],
    event_type: str,
    details: Optional[Union[str, Dict[str, Any]]] = None,
    db_path: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """
    Record an administrative or account lifecycle event into user_activity_logs table.
    details may be a string or JSON-serializable dictionary.
    """
    details_str = ""
    if details is not None:
        if isinstance(details, (dict, list)):
            try:
                details_str = json.dumps(details, ensure_ascii=False)
            except Exception:
                details_str = str(details)
        else:
            details_str = str(details)

    should_close = False
    active_conn = conn
    if active_conn is None:
        active_conn = get_connection(db_path)
        should_close = True

    try:
        cursor = active_conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_activity_logs (user_id, event_type, details)
            VALUES (?, ?, ?);
            """,
            (user_id, event_type, details_str),
        )
        if should_close:
            active_conn.commit()
        return cursor.lastrowid
    finally:
        if should_close:
            active_conn.close()


def get_user_activity_logs(
    user_id: Optional[int] = None,
    limit: int = 50,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent user activity events, optionally filtered by user_id."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute(
                """
                SELECT id, user_id, event_type, details, created_at
                FROM user_activity_logs
                WHERE user_id = ?
                ORDER BY id DESC LIMIT ?;
                """,
                (user_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, user_id, event_type, details, created_at
                FROM user_activity_logs
                ORDER BY id DESC LIMIT ?;
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "event_type": r["event_type"],
                "details": r["details"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_user_by_id(user_id: int, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user record by primary key."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ? LIMIT 1;", (user_id,))
        return _row_to_user_dict(cursor.fetchone())
    finally:
        conn.close()


def get_user_by_username(username: str, db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user record by username."""
    if not username or not str(username).strip():
        return None
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? LIMIT 1;", (username.strip(),))
        return _row_to_user_dict(cursor.fetchone())
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Quota Check & Enforcement
# ---------------------------------------------------------------------------

def check_quota(user_id: int, db_path: Optional[Union[str, Path]] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check if user account is active, subscription has not expired,
    and has remaining daily and weekly video generation quota.

    Returns:
        (allowed: bool, reason: str, details: Dict[str, Any])
    """
    user = get_user_by_id(user_id, db_path)
    if not user:
        return (False, "حساب المستخدم غير موجود", {"allowed": False, "reason": "user_not_found"})

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    is_active = user["is_active"]
    expires_at = user["expires_at"]

    is_expired = False
    if expires_at and str(expires_at).strip():
        clean_exp = str(expires_at).strip()[:10]
        if clean_exp < today_str:
            is_expired = True

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        # Daily generations count
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt FROM video_generations
            WHERE user_id = ? AND date(created_at) = date('now');
            """,
            (user_id,),
        )
        today_used = cursor.fetchone()["cnt"]

        # Weekly generations count (past 7 rolling days)
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt FROM video_generations
            WHERE user_id = ? AND created_at >= datetime('now', '-7 days');
            """,
            (user_id,),
        )
        weekly_used = cursor.fetchone()["cnt"]
    finally:
        conn.close()

    daily_quota = user["daily_quota"]
    weekly_quota = user["weekly_quota"]
    daily_remaining = max(0, daily_quota - today_used)
    weekly_remaining = max(0, weekly_quota - weekly_used)

    details = {
        "user_id": user["id"],
        "username": user["username"],
        "business_name": user["business_name"],
        "business_category": user["business_category"],
        "role": user["role"],
        "is_active": is_active,
        "status": user.get("status", "active"),
        "valid_from": user.get("valid_from"),
        "expires_at": expires_at,
        "is_expired": is_expired,
        "daily_quota": daily_quota,
        "daily_used": today_used,
        "daily_remaining": daily_remaining,
        "weekly_quota": weekly_quota,
        "weekly_used": weekly_used,
        "weekly_remaining": weekly_remaining,
    }

    # Admin accounts bypass quota checks
    if user["role"] == "admin":
        return (True, "حساب مسؤول النظام - استخدام غير محدود", details)

    # 1. Check expiration date
    if is_expired or user.get("status") == "expired":
        return (False, f"انتهت صلاحية اشتراك الحساب بتاريخ {expires_at}. يرجى تجديد الاشتراك.", details)

    # 2. Check valid_from start date
    valid_from = user.get("valid_from")
    if valid_from and str(valid_from).strip():
        clean_valid = str(valid_from).strip()[:10]
        if clean_valid > today_str:
            return (False, f"حساب الاشتراك يبدأ في تاريخ {valid_from}.", details)

    # 3. Check active / suspended status
    if not is_active or user.get("status") in ("suspended", "inactive"):
        return (False, "الحساب معطل حالياً من قِبل إدارة المنصة", details)
    # 4. Check daily quota limit
    if today_used >= daily_quota:
        return (False, f"تم استنفاد الحصة اليومية المسموحة ({today_used}/{daily_quota} فيديو). تتجدد الحصة غداً.", details)

    # 5. Check weekly quota limit
    if weekly_used >= weekly_quota:
        return (False, f"تم استنفاد الحصة الأسبوعية المسموحة ({weekly_used}/{weekly_quota} فيديو).", details)

    return (True, "الحصة متاحة لإنتاج الفيديو", details)


# ---------------------------------------------------------------------------
# Video Generation Logging & User History
# ---------------------------------------------------------------------------

def record_generation(
    user_id: int,
    job_id: str,
    video_url: Optional[str] = None,
    title: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """Record a completed or in-progress video generation to the audit log."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO video_generations (user_id, job_id, video_url, title)
                VALUES (?, ?, ?, ?);
                """,
                (user_id, str(job_id), video_url, title or f"فيديو {job_id[:8]}"),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_user_history(
    user_id: int,
    limit: int = 50,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve video generation history for a specific user."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, job_id, video_url, title, created_at
            FROM video_generations
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?;
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "job_id": r["job_id"],
                "video_url": r["video_url"],
                "title": r["title"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Admin Management Functions
# ---------------------------------------------------------------------------

def create_user(
    username: str,
    business_name: str,
    business_category: str = "ecommerce",
    role: str = "merchant",
    password: Optional[str] = None,
    valid_from: Optional[str] = None,
    expires_at: Optional[str] = None,
    daily_quota: int = 5,
    weekly_quota: int = 25,
    auth_token: Optional[str] = None,
    is_active: int = 1,
    status: str = "active",
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new merchant or admin user account with hashed password and date validity."""
    clean_username = username.strip()
    clean_token = auth_token.strip() if auth_token else f"token_{clean_username}_{uuid.uuid4().hex[:8]}"
    pwd_to_hash = password if password else (DEFAULT_ADMIN_PASSWORD if role == "admin" else DEFAULT_MERCHANT_PASSWORD)
    pwd_hash = hash_password(pwd_to_hash)

    clean_status = str(status).strip().lower() if status else "active"
    effective_is_active = 0 if clean_status in ("suspended", "inactive") or not is_active else 1

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (
                    username, password_hash, business_name, business_category, role,
                    is_active, status, valid_from, expires_at, daily_quota, weekly_quota, auth_token
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    clean_username,
                    pwd_hash,
                    business_name.strip(),
                    business_category.strip(),
                    role.strip(),
                    effective_is_active,
                    clean_status,
                    valid_from.strip() if valid_from else None,
                    expires_at.strip() if expires_at else None,
                    int(daily_quota),
                    int(weekly_quota),
                    clean_token,
                ),
            )
            new_id = cursor.lastrowid
            cursor.execute("SELECT * FROM users WHERE id = ?;", (new_id,))
            created = _row_to_user_dict(cursor.fetchone())
            if created is None:
                raise RuntimeError("Failed to retrieve created user")

            log_user_event(
                user_id=new_id,
                event_type="account_created",
                details={
                    "username": clean_username,
                    "role": role,
                    "status": clean_status,
                    "valid_from": valid_from,
                    "expires_at": expires_at,
                    "daily_quota": daily_quota,
                    "weekly_quota": weekly_quota,
                },
                db_path=db_path,
                conn=conn,
            )
            return created
    finally:
        conn.close()


def update_user(
    user_id: int,
    db_path: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> bool:
    """
    Update fields of an existing user account.
    Accepted fields: business_name, business_category, role, is_active, status,
    valid_from, expires_at, daily_quota, weekly_quota, auth_token, password, password_hash.
    """
    allowed_fields = {
        "business_name",
        "business_category",
        "role",
        "is_active",
        "status",
        "valid_from",
        "expires_at",
        "daily_quota",
        "weekly_quota",
        "auth_token",
        "password",
        "password_hash",
    }
    updates = {}
    for k, v in kwargs.items():
        if k in allowed_fields:
            if k == "password":
                updates["password_hash"] = hash_password(str(v))
            elif k == "status":
                s_val = str(v).strip().lower()
                updates["status"] = s_val
                if "is_active" not in kwargs:
                    updates["is_active"] = 0 if s_val in ("suspended", "inactive") else 1
            elif k == "is_active":
                updates["is_active"] = 1 if v else 0
                if "status" not in kwargs:
                    updates["status"] = "active" if v else "suspended"
            elif k in ("daily_quota", "weekly_quota"):
                updates[k] = int(v)
            elif k in ("valid_from", "expires_at"):
                updates[k] = str(v).strip() if v else None
            else:
                updates[k] = v

    if not updates:
        return False

    set_clause = ", ".join(f"{col} = ?" for col in updates.keys())
    values = list(updates.values()) + [user_id]

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?;", values)
            success = cursor.rowcount > 0
            if success:
                log_details = {k: v for k, v in updates.items() if k != "password_hash"}
                if "password_hash" in updates:
                    log_details["password_changed"] = True
                log_user_event(user_id, "account_updated", log_details, db_path=db_path, conn=conn)
            return success
    finally:
        conn.close()


def list_users(db_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """
    List all user accounts along with calculated usage counts
    (videos_today, videos_this_week, total_videos).
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id ASC;")
        user_rows = cursor.fetchall()

        results = []
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for u in user_rows:
            uid = u["id"]
            cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN date(created_at) = date('now') THEN 1 ELSE 0 END) AS today_cnt,
                    SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) AS week_cnt,
                    COUNT(*) AS total_cnt
                FROM video_generations
                WHERE user_id = ?;
                """,
                (uid,),
            )
            stats = cursor.fetchone()
            today_cnt = stats["today_cnt"] or 0
            week_cnt = stats["week_cnt"] or 0
            total_cnt = stats["total_cnt"] or 0

            exp = u["expires_at"]
            is_expired = False
            if exp and str(exp).strip():
                clean_exp = str(exp).strip()[:10]
                if clean_exp < today_str:
                    is_expired = True

            v_from = u["valid_from"] if "valid_from" in u.keys() else None
            raw_status = u["status"] if "status" in u.keys() and u["status"] else ("active" if u["is_active"] else "suspended")
            if not bool(u["is_active"]) or raw_status in ("suspended", "inactive"):
                eff_status = "suspended"
            elif is_expired:
                eff_status = "expired"
            elif v_from and str(v_from).strip()[:10] > today_str:
                eff_status = "pending"
            else:
                eff_status = raw_status or "active"

            results.append({
                "id": u["id"],
                "username": u["username"],
                "business_name": u["business_name"],
                "business_category": u["business_category"],
                "role": u["role"],
                "is_active": bool(u["is_active"]) and eff_status == "active",
                "status": eff_status,
                "valid_from": v_from,
                "expires_at": u["expires_at"],
                "is_expired": is_expired,
                "daily_quota": u["daily_quota"],
                "weekly_quota": u["weekly_quota"],
                "videos_today": today_cnt,
                "videos_this_week": week_cnt,
                "total_videos": total_cnt,
                "daily_remaining": max(0, u["daily_quota"] - today_cnt),
                "weekly_remaining": max(0, u["weekly_quota"] - week_cnt),
                "auth_token": u["auth_token"],
                "created_at": str(u["created_at"]),
            })
        return results
    finally:
        conn.close()


def get_platform_stats(db_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Retrieve macro-level platform statistics for the Admin Dashboard."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        # Users breakdown
        cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
        total_users = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'merchant' AND is_active = 1;")
        active_merchants = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin';")
        total_admins = cursor.fetchone()["cnt"]

        # Video generations breakdown
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN date(created_at) = date('now') THEN 1 ELSE 0 END) AS today_cnt,
                SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) AS week_cnt,
                COUNT(*) AS total_cnt
            FROM video_generations;
            """
        )
        gen_stats = cursor.fetchone()
        videos_today = gen_stats["today_cnt"] or 0
        videos_this_week = gen_stats["week_cnt"] or 0
        total_videos = gen_stats["total_cnt"] or 0

        # Categories breakdown
        cursor.execute(
            """
            SELECT business_category, COUNT(*) AS count
            FROM users
            WHERE role = 'merchant'
            GROUP BY business_category
            ORDER BY count DESC;
            """
        )
        category_breakdown = {row["business_category"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_users": total_users,
            "active_merchants": active_merchants,
            "total_admins": total_admins,
            "videos_today": videos_today,
            "videos_this_week": videos_this_week,
            "total_videos": total_videos,
            "category_breakdown": category_breakdown,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        conn.close()


def get_demo_accounts() -> List[Dict[str, Any]]:
    """Return pre-seeded accounts for 1-tap fast switching on the front-end."""
    return list(PRESEEDED_ACCOUNTS)
