#!/usr/bin/env python3
"""
SQLite Persistence & Ingestion Store for the 5D Education Intelligence System.
Stores:
- Students & 5D Profiles (seeded from sample_students_cohort.json)
- Arcade Game Telemetry Events (Go/No-Go, Spatial Working Memory, Empathy RPG)
- Daily Bio-Psycho-Social & Cultural Check-ins (Sleep, Nutrition, Screen Time, Hormones/Growth, Mood)
- Historical Triage Audit Logs
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "knowledge" / "education_intelligence.db"
SEED_FILE = PROJECT_DIR / "knowledge" / "sample_students_cohort.json"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                grade TEXT,
                profile_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS arcade_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                game_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                metrics_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bio_psycho_social_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                sleep_hours REAL,
                nutrition_score INTEGER,
                late_night_social_mins INTEGER,
                daily_screen_hours REAL,
                stress_resilience INTEGER,
                growth_fatigue_flag INTEGER,
                cultural_notes TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS triage_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                triage_tier TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        # Seed or sync from sample_students_cohort.json
        if SEED_FILE.exists():
            seed_data = json.loads(SEED_FILE.read_text())
            seed_students = seed_data.get("students", [])
            seed_ids = [s["id"] for s in seed_students]
            cur = conn.execute("SELECT student_id FROM students")
            existing_ids = {r["student_id"] for r in cur.fetchall()}
            # If the cohort IDs changed (e.g. Grade 8 Pilot STU-801..806), sync DB
            if not existing_ids.issuperset(set(seed_ids)):
                conn.execute("DELETE FROM students")
                now = time.time()
                for s in seed_students:
                    conn.execute(
                        """
                        INSERT INTO students (student_id, name, age, grade, profile_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            s["id"],
                            s["name"],
                            s.get("age", 13),
                            s.get("grade", "8th Grade"),
                            json.dumps(s),
                            now,
                        ),
                    )
        conn.commit()


def list_students() -> List[Dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT profile_json FROM students ORDER BY student_id").fetchall()
        return [json.loads(r["profile_json"]) for r in rows]


def get_student(student_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT profile_json FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        return json.loads(row["profile_json"]) if row else None


def save_student(profile: Dict[str, Any]) -> None:
    init_db()
    sid = profile["id"]
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO students (student_id, name, age, grade, profile_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                grade = excluded.grade,
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (
                sid,
                profile.get("name", sid),
                profile.get("age", 14),
                profile.get("grade", ""),
                json.dumps(profile),
                now,
            ),
        )
        conn.commit()


def record_arcade_event(
    student_id: str, game_type: str, score: int, metrics: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Records a stealth assessment arcade game event and updates the student's 5D profile.
    game_type:
      - 'go_nogo_impulse': updates impulse_control_go_nogo_score & sustained_attention_stamina_mins
      - 'spatial_matrix': updates working_memory_index & systems_and_engineering talent
      - 'narrative_empathy': updates interpersonal_and_leadership, linguistic_and_narrative & peer_belonging_index
    """
    student = get_student(student_id)
    if not student:
        return None

    cog = student.setdefault("cognitive_arcade_telemetry", {})
    talents = student.setdefault("talent_scores", {})
    socio = student.setdefault("socio_cultural_and_family", {})

    if game_type == "go_nogo_impulse":
        cog["impulse_control_go_nogo_score"] = int(score)
        if "stamina_mins" in metrics:
            cog["sustained_attention_stamina_mins"] = int(metrics["stamina_mins"])
    elif game_type == "spatial_matrix":
        cog["working_memory_index"] = int(score)
        talents["systems_and_engineering"] = max(
            int(talents.get("systems_and_engineering", 75)), int(score)
        )
        talents["quantitative_and_pattern_logic"] = int(
            round((talents.get("quantitative_and_pattern_logic", 75) + int(score)) / 2)
        )
        if int(score) >= 85:
            cog["dominant_modality"] = "visual_spatial"
    elif game_type == "narrative_empathy":
        talents["interpersonal_and_leadership"] = int(score)
        talents["linguistic_and_narrative"] = max(
            int(talents.get("linguistic_and_narrative", 70)), int(score) - 4
        )
        if "belonging_boost" in metrics:
            socio["peer_belonging_index"] = min(
                100, int(socio.get("peer_belonging_index", 70)) + int(metrics["belonging_boost"])
            )

    save_student(student)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO arcade_telemetry (student_id, game_type, score, metrics_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, game_type, int(score), json.dumps(metrics), time.time()),
        )
        conn.commit()

    return student


def record_checkin(student_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Records a daily Bio-Psycho-Social & Cultural Check-in (Sleep, Nutrition, Screen Time,
    Adolescent Growth/Hormones, Stress Resilience, Cultural/Family notes) and updates the student profile.
    """
    student = get_student(student_id)
    if not student:
        return None

    bio = student.setdefault("bio_and_nutrition", {})
    psych = student.setdefault("psychological_and_digital", {})
    socio = student.setdefault("socio_cultural_and_family", {})
    cog = student.setdefault("cognitive_arcade_telemetry", {})
    hormonal = student.setdefault("hormonal_and_adolescent_profile", {})

    if "sleep_hours" in payload:
        bio["avg_sleep_hours"] = float(payload["sleep_hours"])
    if "nutrition_score" in payload:
        bio["morning_protein_and_hydration_score"] = int(payload["nutrition_score"])
    if "growth_fatigue_flag" in payload:
        bio["adolescent_growth_or_hormonal_fatigue_flag"] = bool(payload["growth_fatigue_flag"])
    if "late_night_social_mins" in payload:
        psych["late_night_social_media_mins"] = int(payload["late_night_social_mins"])
    if "daily_screen_hours" in payload:
        psych["daily_screen_time_hours"] = float(payload["daily_screen_hours"])
    if "stress_resilience" in payload:
        psych["stress_resilience_score"] = int(payload["stress_resilience"])
    if "stamina_mins" in payload:
        cog["sustained_attention_stamina_mins"] = int(payload["stamina_mins"])
    if "melatonin_shift_mins" in payload:
        hormonal["circadian_melatonin_shift_mins"] = int(payload["melatonin_shift_mins"])
    if "cortisol_reactivity" in payload:
        hormonal["cortisol_awakening_reactivity"] = int(payload["cortisol_reactivity"])
    if "cultural_notes" in payload and payload["cultural_notes"]:
        socio["religious_and_cultural_context"] = str(payload["cultural_notes"])

    save_student(student)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO bio_psycho_social_logs (
                student_id, sleep_hours, nutrition_score, late_night_social_mins,
                daily_screen_hours, stress_resilience, growth_fatigue_flag, cultural_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                bio.get("avg_sleep_hours"),
                bio.get("morning_protein_and_hydration_score"),
                psych.get("late_night_social_media_mins"),
                psych.get("daily_screen_time_hours"),
                psych.get("stress_resilience_score"),
                1 if bio.get("adolescent_growth_or_hormonal_fatigue_flag") else 0,
                socio.get("religious_and_cultural_context", ""),
                time.time(),
            ),
        )
        conn.commit()

    return student


def get_student_history(student_id: str) -> Dict[str, Any]:
    init_db()
    with get_conn() as conn:
        arcade_rows = conn.execute(
            """
            SELECT game_type, score, metrics_json, created_at
            FROM arcade_telemetry
            WHERE student_id = ?
            ORDER BY id DESC LIMIT 15
            """,
            (student_id,),
        ).fetchall()
        bio_rows = conn.execute(
            """
            SELECT sleep_hours, nutrition_score, late_night_social_mins, stress_resilience, created_at
            FROM bio_psycho_social_logs
            WHERE student_id = ?
            ORDER BY id DESC LIMIT 15
            """,
            (student_id,),
        ).fetchall()
        return {
            "arcade_events": [
                {
                    "game_type": r["game_type"],
                    "score": r["score"],
                    "metrics": json.loads(r["metrics_json"]),
                    "timestamp": r["created_at"],
                }
                for r in arcade_rows
            ],
            "bio_logs": [dict(r) for r in bio_rows],
        }


if __name__ == "__main__":
    init_db()
    students = list_students()
    print(json.dumps({"db_path": str(DB_PATH), "seeded_students": len(students)}, indent=2))
