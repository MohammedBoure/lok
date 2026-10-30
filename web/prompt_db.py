#!/usr/bin/env python3
"""
Prompt Descriptions Database Module (web/prompt_db.py)
SQLite persistence layer for visual and speech prompt descriptions history.

Author: MouhammedBoure
Role: Backend Architecture & Systems Engineer (agy11)
Branch: backend/agy11-sqlite-prompt-descriptions-and-agent
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("prompt_db")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

# Ensure repository root and default DB path
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "outputs" / "prompts.db"

# Pre-seeded Algerian Real Estate Descriptions
DEFAULT_PRESEEDED_PROMPTS: List[Dict[str, Any]] = [
    {
        "title": "فيلا عصرية فاخرة بواجهة بحرية - وهران",
        "visual_description": "فيلا عصرية فاخرة مطلة على البحر الأبيض المتوسط، واجهات زجاجية واسعة، مسبح خاص وحديقة خضراء، ديكورات حديثة وإضاءة نهارية طبيعية مشمسة.",
        "speech_description": "التركيز على الفخامة والسكينة، الإطلالة البحرية الخلابة والمساحة الرحبة للعائلات بلهجة جزائرية راقية ومرحبة.",
        "inferred_script": "شوفو معايا هاد الفيلا الساحرة في عين الترك بوهران، إطلالة مباشرة على البحر، مسبح خاص وتشطيبات ديلوكس تجمع بين الفخامة والراحة العائلية.",
        "metadata": {
            "preset": "oran_seaview_villa",
            "city": "وهران",
            "property_type": "فيلا",
            "tag": "Luxury Seaview Villa",
        },
    },
    {
        "title": "بنتهاوس فاخر بتراس بانورامي - سيدي يحيى، الجزائر",
        "visual_description": "شقة بنتهاوس دوبلكس واسعة بتراس بانورامي مفتوح على خليج الجزائر، صالون رخامي واسع، مطبخ أمريكي مجهز، وأجنحة نوم فسيحة بتشطيبات عالية الجودة.",
        "speech_description": "تسليط الضوء على هيبة الموقع الراقي في سيدي يحيى، الإطلالة البانورامية المفتوحة، والتجهيزات العصرية بأسلوب تسويقي واثق وأنيق.",
        "inferred_script": "رانا هنا في قلب سيدي يحيى، بنتهاوس استثنائي بإطلالة بانورامية ساحرة على العاصمة، صالون ملكي ومطبخ مجهز بأعلى المعايير العصرية.",
        "metadata": {
            "preset": "algiers_f4_luxury",
            "city": "الجزائر العاصمة",
            "property_type": "بنتهاوس",
            "tag": "Downtown Penthouse",
        },
    },
    {
        "title": "محل تجاري واستثماري استراتيجي - قسنطينة",
        "visual_description": "محل تجاري واسع بواجهة زجاجية عريضة على شارع رئيسي نشط، طابقين مع مساحة تخزين وتجهيزات أمنية متكاملة وإضاءة تجارية ممتازة.",
        "speech_description": "إبراز القيمة الاستثمارية العالية، التدفق التجاري النشط يومياً، وملاءمته لكافة النشاطات التجارية والتوكيلات الكبرى بأسلوب حيوي.",
        "inferred_script": "فرصة تجارية ذهبية في موقع استراتيجي حيوي بقسنطينة، واجهة واسعة وتدفق ممتاز يضمن نجاح وتطور مشروعك التجاري.",
        "metadata": {
            "preset": "constantine_commercial",
            "city": "قسنطينة",
            "property_type": "تجاري",
            "tag": "Commercial Hub",
        },
    },
]


def _resolve_db_path(db_path: Optional[Union[str, Path]] = None) -> Path:
    """Resolve and ensure the parent directory of SQLite database exists."""
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
    Initialize SQLite database schema and pre-seed realistic Algerian real estate
    prompts if table is currently empty.
    """
    resolved_path = _resolve_db_path(db_path)
    conn = sqlite3.connect(str(resolved_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    visual_description TEXT,
                    speech_description TEXT,
                    inferred_script TEXT,
                    metadata TEXT
                )
                """
            )
            # Check row count
            cur = conn.execute("SELECT COUNT(*) AS cnt FROM prompt_history")
            count = cur.fetchone()["cnt"]
            if count == 0:
                logger.info("Pre-seeding default Algerian real estate prompt descriptions into %s...", resolved_path)
                for item in DEFAULT_PRESEEDED_PROMPTS:
                    meta_val = item.get("metadata")
                    meta_str = json.dumps(meta_val, ensure_ascii=False) if isinstance(meta_val, (dict, list)) else meta_val
                    conn.execute(
                        """
                        INSERT INTO prompt_history (title, visual_description, speech_description, inferred_script, metadata)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            item.get("title"),
                            item.get("visual_description"),
                            item.get("speech_description"),
                            item.get("inferred_script"),
                            meta_str,
                        ),
                    )
    finally:
        conn.close()


def save_prompt(
    visual_description: Optional[str],
    speech_description: Optional[str],
    inferred_script: Optional[str] = None,
    title: Optional[str] = None,
    metadata: Optional[Union[Dict[str, Any], str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Persist a prompt description record into SQLite prompt_history table.

    Args:
        visual_description: Description of what appears in the video (وصف ما يظهر في الفيديو).
        speech_description: Description of what should be said in voiceover (وصف ما سيقال في التعليق الصوتي).
        inferred_script: Optional full generated script text.
        title: Optional title/label for the property or prompt.
        metadata: Optional dictionary or JSON string with additional metadata.
        db_path: Optional override for database file location.

    Returns:
        int: The auto-generated row ID of the inserted record.
    """
    init_db(db_path)
    meta_str: Optional[str] = None
    if isinstance(metadata, (dict, list)):
        meta_str = json.dumps(metadata, ensure_ascii=False)
    elif isinstance(metadata, str):
        meta_str = metadata

    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO prompt_history (title, visual_description, speech_description, inferred_script, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, visual_description, speech_description, inferred_script, meta_str),
            )
            return int(cur.lastrowid)
    finally:
        conn.close()


def get_recent_prompts(
    limit: int = 50,
    db_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent prompt records ordered descending by ID.

    Args:
        limit: Maximum number of records to return (defaults to 50).
        db_path: Optional override for database file location.

    Returns:
        List of dictionaries representing prompt_history records.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT id, created_at, title, visual_description, speech_description, inferred_script, metadata
            FROM prompt_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, limit),),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_prompt_by_id(
    prompt_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single prompt record by its ID.

    Args:
        prompt_id: The primary key ID to find.
        db_path: Optional override for database file location.

    Returns:
        Dictionary representation of prompt record or None if not found.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT id, created_at, title, visual_description, speech_description, inferred_script, metadata
            FROM prompt_history
            WHERE id = ?
            """,
            (prompt_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_prompt(
    prompt_id: int,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Delete a prompt record by its ID.

    Args:
        prompt_id: The primary key ID to delete.
        db_path: Optional override for database file location.

    Returns:
        bool: True if a record was deleted, False otherwise.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute("DELETE FROM prompt_history WHERE id = ?", (prompt_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


def update_prompt_script(
    prompt_id: int,
    inferred_script: str,
    db_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Update the inferred_script for an existing prompt record.

    Args:
        prompt_id: The ID of the prompt record to update.
        inferred_script: The generated script text.
        db_path: Optional override for database file location.

    Returns:
        bool: True if updated, False otherwise.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE prompt_history SET inferred_script = ? WHERE id = ?",
                (inferred_script, prompt_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()
