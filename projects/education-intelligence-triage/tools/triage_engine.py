#!/usr/bin/env python3
"""
Deterministic + Neuro-Pedagogical 5D Student Triage & Coaching Engine.
Evaluates Cognitive/Brain-Wiring, Talents, Bio/Nutrition/Sleep/Adolescence,
Psychological/Screen-Time, and Socio-Cultural/Religious factors.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def evaluate_student_5d(student: Dict[str, Any]) -> Dict[str, Any]:
    cog = student.get("cognitive_arcade_telemetry", {})
    talents = student.get("talent_scores", {})
    bio = student.get("bio_and_nutrition", {})
    psych = student.get("psychological_and_digital", {})
    socio = student.get("socio_cultural_and_family", {})

    risk_factors: List[str] = []
    critical_flags: List[str] = []

    # 1. Biological, Sleep, Nutrition & Adolescent Growth checks
    sleep_hrs = float(bio.get("avg_sleep_hours", 8.0))
    nutrition_score = int(bio.get("morning_protein_and_hydration_score", 80))
    growth_flag = bool(bio.get("adolescent_growth_or_hormonal_fatigue_flag", False))

    if sleep_hrs < 5.2:
        critical_flags.append(f"Severe sleep deprivation ({sleep_hrs}h/night)")
    elif sleep_hrs < 6.8:
        risk_factors.append(f"Adolescent sleep debt ({sleep_hrs}h/night vs 8-9h optimal)")

    if nutrition_score < 40:
        critical_flags.append(f"Critical morning nutritional deficit (score {nutrition_score}/100)")
    elif nutrition_score < 60:
        risk_factors.append(
            f"Suboptimal morning protein/hydration ({nutrition_score}/100) — high glycemic crash risk"
        )

    if growth_flag:
        risk_factors.append(
            f"Active adolescent growth/hormonal shift ({student.get('adolescent_stage', 'Adolescence')}) increasing baseline energy demand"
        )

    # 2. Psychological, Screen Time & Social Media checks
    stress_resilience = int(psych.get("stress_resilience_score", 75))
    late_social_mins = int(psych.get("late_night_social_media_mins", 0))
    screen_hrs = float(psych.get("daily_screen_time_hours", 2.0))
    frustration_rec = int(psych.get("frustration_recovery_rate", 75))

    if stress_resilience < 40 or frustration_rec < 35:
        critical_flags.append(
            f"Acute emotional/stress overload (resilience {stress_resilience}/100, recovery {frustration_rec}/100)"
        )
    elif stress_resilience < 65:
        risk_factors.append(f"Elevated cognitive/emotional strain (resilience {stress_resilience}/100)")

    if late_social_mins >= 120:
        critical_flags.append(
            f"Severe late-night social media circadian disruption ({late_social_mins} mins past bedtime)"
        )
    elif late_social_mins >= 45 or screen_hrs >= 4.5:
        risk_factors.append(
            f"High digital/social media dopamine load ({screen_hrs}h daily, {late_social_mins}m late-night)"
        )

    # 3. Socio-Cultural & Peer Belonging checks
    belonging = int(socio.get("peer_belonging_index", 75))
    if belonging < 45:
        critical_flags.append(f"Social isolation / peer belonging alert ({belonging}/100)")

    # Determine Triage Tier
    if critical_flags:
        triage_tier = "RED"
        triage_label = "TIER 3 (RED) — Urgent Counselor & Family Safeguarding Triage"
    elif len(risk_factors) >= 2:
        triage_tier = "AMBER"
        triage_label = "TIER 2 (AMBER) — Targeted Bio-Psycho-Social Coaching Intervention"
    else:
        triage_tier = "GREEN"
        triage_label = "TIER 1 (GREEN) — Thriving & Autonomous Talent Acceleration"

    # Top 2 Talents
    sorted_talents = sorted(talents.items(), key=lambda kv: kv[1], reverse=True)
    top_talents = [{"domain": k, "score": v} for k, v in sorted_talents[:2]]

    # Tailored Learning Methodology
    stamina = int(cog.get("sustained_attention_stamina_mins", 20))
    optimal_sprint = min(max(stamina + 2, 10), 35)
    dom_mod = cog.get("dominant_modality", "visual_spatial")
    sec_mod = cog.get("secondary_modality", "kinesthetic_experiential")

    modality_playbooks = {
        "visual_spatial": "3D spatial sandboxes, color-coded concept architecture maps, and diagram-first notes",
        "auditory_verbal": "Socratic dialogue quests, rhythmic/narrative synthesis, and peer-teaching voice logs",
        "kinesthetic_experiential": "Hands-on simulation builds, arcade micro-sprints with movement breaks",
        "analytical_systems": "First-principles causal trees, system-debugging puzzles, and rule-discovery labs",
    }

    # Multi-stakeholder Action Plans
    student_quests = [
        f"Arcade Focus Sprint: {optimal_sprint}-min {dom_mod.replace('_', '-')} bursts followed by a 3-min kinetic recharge.",
        f"Talent Channeling Quest: Apply your top talent ({top_talents[0]['domain'].replace('_', ' ').title()} - {top_talents[0]['score']}%) to unlock your next academic boss challenge.",
    ]
    if late_social_mins >= 45:
        student_quests.append(
            "Digital Sunset Shield: Dock devices 45 mins before sleep to boost tomorrow's Working Memory XP by +20%."
        )
    if nutrition_score < 60:
        student_quests.append(
            "Brain-Fuel Combo: Log a high-protein + hydration breakfast to prevent afternoon focus crashes."
        )

    parent_plan = [
        f"Bio-Rhythm & Nutrition: Target 8.5h sleep window (currently {sleep_hrs}h). Pair morning meals with sustained protein & micronutrients.",
        f"Cultural & Family Sync: Align evening wind-down and study routines with family rhythm ({socio.get('religious_and_cultural_context', 'Home schedule')}).",
    ]
    if triage_tier in ("AMBER", "RED"):
        parent_plan.append(
            "Empathy & Screen Co-Pilot: Replace late-night bedroom device access with a calm, non-judgmental check-in; watch for adolescent growth fatigue."
        )

    teacher_card = {
        "privacy_notice": "Scoped to Pedagogical & Classroom Accommodations Only (Medical/Family PII Protected)",
        "optimal_focus_sprint_mins": optimal_sprint,
        "primary_learning_scaffold": modality_playbooks.get(dom_mod, dom_mod),
        "secondary_learning_scaffold": modality_playbooks.get(sec_mod, sec_mod),
        "talent_bridge_strategy": (
            f"Anchor complex lessons using {top_talents[0]['domain'].replace('_', ' ')} "
            f"and {top_talents[1]['domain'].replace('_', ' ')} challenges."
        ),
        "classroom_triage_action": (
            "Schedule warm 1-on-1 counselor check-in & reduce high-stakes timed pressure this week."
            if triage_tier == "RED"
            else (
                "Seat in low-distraction zone, chunk tasks into micro-milestones, and monitor afternoon energy dip."
                if triage_tier == "AMBER"
                else "Assign peer-mentor or stretch Olympiad/incubator challenge."
            )
        ),
    }

    academy_card = {
        "institutional_triage_tier": triage_tier,
        "counselor_safeguarding_queue": (
            "URGENT: Assign School Psychologist & Family Liaison within 24h"
            if triage_tier == "RED"
            else (
                "ACTIVE: 14-Day Bio-Psycho-Social Coaching Check-In"
                if triage_tier == "AMBER"
                else "ROUTINE: Talent Incubator & Olympiad Track"
            )
        ),
        "academy_talent_stream": f"{top_talents[0]['domain'].replace('_', ' ').title()} & {top_talents[1]['domain'].replace('_', ' ').title()} Lab",
        "curriculum_modality_cluster": dom_mod.replace("_", "-").title(),
        "schedule_and_policy_alignment": socio.get(
            "religious_and_cultural_context", "Standard Academy Schedule"
        ),
    }

    return {
        "system_name": "Kalki",
        "student_id": student.get("id"),
        "student_name": student.get("name"),
        "grade": student.get("grade"),
        "triage_tier": triage_tier,
        "triage_label": triage_label,
        "critical_flags": critical_flags,
        "risk_factors": risk_factors,
        "top_talents": top_talents,
        "tailored_learning_methodology": {
            "dominant_modality": dom_mod,
            "secondary_modality": sec_mod,
            "optimal_focus_sprint_mins": optimal_sprint,
            "working_memory_index": cog.get("working_memory_index"),
            "methodology_prescription": modality_playbooks.get(dom_mod, ""),
        },
        "stakeholder_coaching_plans": {
            "student_gamified_quests": student_quests,
            "parent_home_copilot": parent_plan,
            "teacher_classroom_accommodation": teacher_card,
            "academy_governance_card": academy_card,
        },
    }


def main() -> None:
    try:
        import telemetry_store
        students = telemetry_store.list_students()
    except Exception:
        cohort_file = KNOWLEDGE_DIR / "sample_students_cohort.json"
        if not cohort_file.exists():
            print(json.dumps({"error": f"Missing {cohort_file}"}))
            sys.exit(1)
        cohort = json.loads(cohort_file.read_text())
        students = cohort.get("students", [])

    target_id = sys.argv[1].strip() if len(sys.argv) > 1 else None
    results = []
    for s in students:
        if target_id:
            sid = str(s.get("id", "")).lower()
            sname = str(s.get("name", "")).lower()
            q = target_id.lower()
            # Match if student ID or name appears in the query or vice versa
            if sid not in q and sname not in q and q not in sid and q not in sname:
                continue
        results.append(evaluate_student_5d(s))
    if not results:
        results = [evaluate_student_5d(s) for s in students]

    print(json.dumps({"evaluated_count": len(results), "triage_reports": results}, indent=2))


if __name__ == "__main__":
    main()
