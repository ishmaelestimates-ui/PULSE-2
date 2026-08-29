"""
Executive dashboard service.

Everything here is deterministic — computed from PULSE's own tracked
data across modules. No AI calls, no fabricated benchmarks. See
schemas/dashboard.py for the notes surfaced to the user.
"""
from datetime import date


def compute_progress(episode, media_files, reviews, campaign_pack, press_kit, reddit_posts) -> dict:
    """Each stage is 0 or 100 except 'review', which is the % of
    recommendations that have been decided (accepted or rejected)."""
    stages = {}
    stages["upload"] = 100.0 if media_files else 0.0
    stages["transcribe"] = 100.0 if (episode.transcript and episode.transcript.strip()) else 0.0
    stages["analyze"] = 100.0 if episode.analysis else 0.0

    if reviews:
        decided = sum(1 for r in reviews if r.status in ("accepted", "rejected"))
        stages["review"] = round((decided / len(reviews)) * 100, 1)
    else:
        stages["review"] = 0.0

    stages["campaign"] = 100.0 if campaign_pack else 0.0
    stages["press"] = 100.0 if press_kit else 0.0
    stages["distribution"] = 100.0 if reddit_posts else 0.0

    return stages


def compute_health_score(progress: dict, risk_count_by_severity: dict) -> float:
    """Simple weighted formula: average stage progress, minus a penalty
    per open risk (high=-15, medium=-7, low=-2), floored at 0."""
    avg_progress = sum(progress.values()) / len(progress) if progress else 0.0
    penalty = (
        risk_count_by_severity.get("high", 0) * 15
        + risk_count_by_severity.get("medium", 0) * 7
        + risk_count_by_severity.get("low", 0) * 2
    )
    return max(0.0, round(avg_progress - penalty, 1))


def compute_critical_path(progress: dict) -> list[str]:
    """Ordered list of next recommended actions — first incomplete stage
    in the natural production sequence, plus any pending reviews."""
    path = []
    order = [
        ("upload", "Upload media"),
        ("transcribe", "Transcribe the episode"),
        ("analyze", "Run editorial analysis"),
        ("review", "Finish reviewing recommendations"),
        ("campaign", "Generate the marketing campaign"),
        ("press", "Generate the press kit"),
        ("distribution", "Schedule or post distribution content"),
    ]
    for key, label in order:
        if progress.get(key, 0) < 100:
            path.append(label)
    return path


def compute_risks(
    episode,
    reviews,
    festival_matches,
    milestones,
    budget_items,
    sync_flags: list,
) -> list[dict]:
    risks = []

    # Legal — from sync licensing flags (if a scan has been run/cached by caller)
    for flag in sync_flags or []:
        risks.append(
            {
                "category": "Legal",
                "severity": "medium",
                "description": f"Possible rights concern: {flag.get('excerpt', '')[:120]}",
                "recommended_action": flag.get("recommended_action", "Have a human review this section."),
            }
        )

    # Schedule — overdue milestones, unverified festival deadlines coming up
    today = date.today()
    for m in milestones or []:
        if m.due_date and m.status != "done" and m.due_date < today:
            risks.append(
                {
                    "category": "Schedule",
                    "severity": "high",
                    "description": f"Milestone '{m.title}' is overdue (was due {m.due_date}).",
                    "recommended_action": "Update the due date or mark it complete.",
                }
            )
    for f in festival_matches or []:
        if f.deadline and not f.verified and f.deadline >= today:
            days_out = (f.deadline - today).days
            if days_out <= 30:
                risks.append(
                    {
                        "category": "Schedule",
                        "severity": "medium",
                        "description": (
                            f"'{f.festival_name}' deadline is AI-estimated at {f.deadline} "
                            f"({days_out} days) and not yet verified."
                        ),
                        "recommended_action": "Confirm the real deadline on the festival's site before relying on it.",
                    }
                )

    # Financial — over-budget categories
    for b in budget_items or []:
        if b.spent > b.amount:
            risks.append(
                {
                    "category": "Financial",
                    "severity": "high" if b.spent > b.amount * 1.2 else "medium",
                    "description": f"'{b.category}' is over budget (${b.spent:.0f} spent of ${b.amount:.0f}).",
                    "recommended_action": "Reallocate from an underspent category or adjust the budget.",
                }
            )

    # Creative — undecided weak sections (things flagged as dragging that haven't been dealt with)
    pending_weak = [r for r in (reviews or []) if r.decision_type == "weak_section" and r.status == "recommended"]
    if pending_weak:
        risks.append(
            {
                "category": "Creative",
                "severity": "low" if len(pending_weak) < 3 else "medium",
                "description": f"{len(pending_weak)} weak section(s) flagged by analysis haven't been reviewed yet.",
                "recommended_action": "Accept or reject them in the Review tab.",
            }
        )

    return risks


def compute_finances(budget_items) -> dict:
    total_budget = sum(b.amount for b in budget_items) if budget_items else 0.0
    total_spent = sum(b.spent for b in budget_items) if budget_items else 0.0

    suggestions = []
    over = [b for b in budget_items if b.spent > b.amount] if budget_items else []
    under = [b for b in budget_items if b.spent < b.amount * 0.5] if budget_items else []
    for b in over:
        if under:
            pct = under[0].spent / under[0].amount * 100 if under[0].amount else 0
            suggestions.append(
                f"'{b.category}' is over by ${b.spent - b.amount:.0f} — consider moving funds from "
                f"'{under[0].category}' (only {pct:.0f}% spent)."
            )
        else:
            suggestions.append(f"'{b.category}' is over by ${b.spent - b.amount:.0f} — no underspent category to pull from.")

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": total_budget - total_spent,
        "reallocation_suggestions": suggestions,
    }
