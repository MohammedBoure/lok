#!/usr/bin/env python3
"""
SaaS Multi-Tenant Authentication & Quotas Database Module (web/auth_db.py).
Manages commercial merchant accounts, roles, expiration, daily/weekly quotas,
and video generation audit history in SQLite (outputs/saas_platform.db).

Author: MohammedBoure
Role: Backend Architecture & SaaS Systems Engineer (agy11)
Branch: backend/agy11-saas-auth-quotas-and-dashboard
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("auth_db")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

# Ensure repository root and default DB path
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "outputs" / "saas_platform.db"

# ---------------------------------------------------------------------------
# Pre-seeded Accounts (1 Master Admin + 10 Commercial Merchants)
# ---------------------------------------------------------------------------

PRESEEDED_ACCOUNTS: List[Dict[str, Any]] = [
    {
        "username": "admin",
        "business_name": "منصة إدارة النظام (SaaS Master Admin)",
        "business_category": "tech",
        "role": "admin",
        "is_active": 1,
        "expires_at": "2099-12-31",
        "daily_quota": 9999,
        "weekly_quota": 99999,
        "auth_token": "token_admin_master",
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
    merchant accounts if the users table is currently empty.
    """
    resolved_path = _resolve_db_path(db_path)
    conn = sqlite3.connect(str(resolved_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    business_name TEXT NOT NULL,
                    business_category TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'merchant',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    expires_at TEXT,
                    daily_quota INTEGER NOT NULL DEFAULT 5,
                    weekly_quota INTEGER NOT NULL DEFAULT 25,
                    auth_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
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
            # Create indexes for fast quota and token lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_token ON users(auth_token);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generations_user_date ON video_generations(user_id, created_at);")

            # Check if seeding is required
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
            row = cursor.fetchone()
            user_count = row["cnt"] if row else 0

            if user_count == 0:
                logger.info("Pre-seeding SaaS database with 1 admin and 10 diverse merchant accounts...")
                for acc in PRESEEDED_ACCOUNTS:
                    cursor.execute(
                        """
                        INSERT INTO users (
                            username, business_name, business_category, role,
                            is_active, expires_at, daily_quota, weekly_quota, auth_token
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            acc["username"],
                            acc["business_name"],
                            acc["business_category"],
                            acc.get("role", "merchant"),
                            acc.get("is_active", 1),
                            acc.get("expires_at"),
                            acc.get("daily_quota", 5),
                            acc.get("weekly_quota", 25),
                            acc["auth_token"],
                        ),
                    )
                logger.info("Successfully seeded %d commercial accounts into %s", len(PRESEEDED_ACCOUNTS), resolved_path)
    finally:
        conn.close()


# Ensure DB schema and seed on module import
init_db()


# ---------------------------------------------------------------------------
# Authentication & User Management Methods
# ---------------------------------------------------------------------------

def _row_to_user_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Convert SQLite Row to structured user dictionary."""
    if not row:
        return None
    return {
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


def authenticate_token(token: Optional[str], db_path: Optional[Union[str, Path]] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate user via auth token.
    Strips 'Bearer ' prefix if present.
    """
    if not token or not str(token).strip():
        return None

    clean_token = str(token).strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

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
    Authenticate user via username alone, or username + token / password.
    For lightweight commercial merchant flow, username matching succeeds directly.
    """
    if not username or not str(username).strip():
        return None

    clean_username = str(username).strip()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if password_or_token and str(password_or_token).strip():
            clean_token = str(password_or_token).strip()
            if clean_token.lower().startswith("bearer "):
                clean_token = clean_token[7:].strip()
            cursor.execute(
                "SELECT * FROM users WHERE username = ? AND auth_token = ? LIMIT 1;",
                (clean_username, clean_token),
            )
        else:
            cursor.execute("SELECT * FROM users WHERE username = ? LIMIT 1;", (clean_username,))
        row = cursor.fetchone()
        return _row_to_user_dict(row)
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
        # Compare ISO date strings YYYY-MM-DD
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

    # 1. Check active status
    if not is_active:
        return (False, "الحساب معطل حالياً من قِبل إدارة المنصة", details)

    # 2. Check expiration date
    if is_expired:
        return (False, f"انتهت صلاحية اشتراك الحساب بتاريخ {expires_at}. يرجى تجديد الاشتراك.", details)

    # 3. Check daily quota limit
    if today_used >= daily_quota:
        return (False, f"تم استنفاد الحصة اليومية المسموحة ({today_used}/{daily_quota} فيديو). تتجدد الحصة غداً.", details)

    # 4. Check weekly quota limit
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
    expires_at: Optional[str] = None,
    daily_quota: int = 5,
    weekly_quota: int = 25,
    auth_token: Optional[str] = None,
    is_active: int = 1,
    db_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Create a new merchant or admin user account."""
    clean_username = username.strip()
    clean_token = auth_token.strip() if auth_token else f"token_{clean_username}_{uuid.uuid4().hex[:8]}"

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (
                    username, business_name, business_category, role,
                    is_active, expires_at, daily_quota, weekly_quota, auth_token
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    clean_username,
                    business_name.strip(),
                    business_category.strip(),
                    role.strip(),
                    int(is_active),
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
    Accepted fields: business_name, business_category, role, is_active,
    expires_at, daily_quota, weekly_quota, auth_token.
    """
    allowed_fields = {
        "business_name",
        "business_category",
        "role",
        "is_active",
        "expires_at",
        "daily_quota",
        "weekly_quota",
        "auth_token",
    }
    updates = {}
    for k, v in kwargs.items():
        if k in allowed_fields:
            if k == "is_active":
                updates[k] = 1 if v else 0
            elif k in ("daily_quota", "weekly_quota"):
                updates[k] = int(v)
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
            return cursor.rowcount > 0
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

            results.append({
                "id": u["id"],
                "username": u["username"],
                "business_name": u["business_name"],
                "business_category": u["business_category"],
                "role": u["role"],
                "is_active": bool(u["is_active"]),
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
