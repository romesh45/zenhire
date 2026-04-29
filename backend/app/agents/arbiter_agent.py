"""Arbiter — pure Python, zero LLM calls, zero async. Must return in < 1800 ms."""


def mark_signal_hits(signals: list[dict], answer_text: str) -> list[dict]:
    """Keyword-match signal names against the answer to estimate coverage."""
    lower = answer_text.lower()
    result = []
    for sig in signals:
        # "explains_event_loop" → ["explains", "event", "loop"]
        keywords = sig["name"].replace("_", " ").split()
        hit = any(kw in lower for kw in keywords if len(kw) > 2)
        result.append({**sig, "hit": hit})
    return result


def compute_gap_ratio(signals: list[dict]) -> float:
    missed_weight = 0.0
    total_weight = 0.0
    for sig in signals:
        weight = 1.0 if sig.get("importance") == "critical" else 0.5
        total_weight += weight
        if not sig.get("hit", True):
            missed_weight += weight
    if total_weight == 0.0:
        return 0.0
    return missed_weight / total_weight


def arbiter_decision(
    signals: list[dict],
    answer_text: str,
    difficulty: str,
    followup_count: int = 0,
) -> dict:
    # 1. MAX_DEPTH gate — hard stop at 2 follow-ups per question
    if followup_count >= 2:
        return {
            "decision": "proceed",
            "reason": "Maximum follow-up depth reached",
            "gap_override": False,
        }

    # 2. Any critical signal completely missed
    for sig in signals:
        if sig.get("importance") == "critical" and not sig.get("hit", True):
            return {
                "decision": "follow_up",
                "reason": f"Did not address key concept: {sig['name'].replace('_', ' ')}",
                "gap_override": True,
            }

    # 3. Overall coverage gap
    gap = compute_gap_ratio(signals)
    if gap > 0.5:
        return {
            "decision": "follow_up",
            "reason": f"Coverage gap too high ({gap:.0%} of expected topics missed)",
            "gap_override": False,
        }

    # 4. Suspiciously short answer
    if len(answer_text.split()) < 30:
        return {
            "decision": "follow_up",
            "reason": "Answer is too brief — please elaborate with more detail",
            "gap_override": False,
        }

    # 5. Sufficient answer
    return {"decision": "proceed", "reason": "Sufficient coverage", "gap_override": False}
