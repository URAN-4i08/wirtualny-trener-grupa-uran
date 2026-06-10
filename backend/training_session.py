"""Sesja treningowa: ustawienie postawy → 3 s prep → 10 s odbić → podsumowanie."""

from __future__ import annotations

import threading
import time

PREP_DURATION_SEC = 3.0
ACTIVE_DURATION_SEC = 10.0
SUMMARY_DURATION_SEC = 8.0
READY_STABLE_SEC = 1.5

_lock = threading.Lock()
_setup_ready_since: float | None = None
_session: dict = {
    "status": "idle",
    "prep_end_at": 0.0,
    "active_end_at": 0.0,
    "summary_end_at": 0.0,
    "bounces": [],
    "aggregate": None,
}


def start_session() -> None:
    global _setup_ready_since
    with _lock:
        _setup_ready_since = None
        _session.update(
            {
                "status": "setup",
                "prep_end_at": 0.0,
                "active_end_at": 0.0,
                "summary_end_at": 0.0,
                "bounces": [],
                "aggregate": None,
            }
        )


def stop_session() -> None:
    global _setup_ready_since
    with _lock:
        _setup_ready_since = None
        _session.update(
            {
                "status": "idle",
                "prep_end_at": 0.0,
                "active_end_at": 0.0,
                "summary_end_at": 0.0,
                "bounces": [],
                "aggregate": None,
            }
        )


def is_recording_bounces() -> bool:
    with _lock:
        return _session["status"] == "active"


def is_timed_session_active() -> bool:
    with _lock:
        return _session["status"] in ("setup", "prep", "active", "summary")


def _is_posture_ready(posture_warnings: str | None) -> bool:
    if not posture_warnings:
        return True
    lowered = posture_warnings.lower()
    if "lokie" in lowered or "łokci" in lowered:
        return False
    return True


def try_advance_from_setup(
    gotowosc: dict | None,
    *,
    has_pose: bool,
    has_legs: bool,
    posture_warnings: str | None = None,
) -> bool:
    """Przechodzi z setup → prep gdy wszystkie segmenty są OK przez READY_STABLE_SEC."""
    global _setup_ready_since

    with _lock:
        if _session["status"] != "setup":
            return False

    ready = (
        has_pose
        and has_legs
        and bool(gotowosc)
        and all(gotowosc.values())
        and _is_posture_ready(posture_warnings)
    )

    if not ready:
        _setup_ready_since = None
        return False

    now = time.time()
    if _setup_ready_since is None:
        _setup_ready_since = now
        return False

    if now - _setup_ready_since < READY_STABLE_SEC:
        return False

    with _lock:
        if _session["status"] != "setup":
            return False
        _session["status"] = "prep"
        _session["prep_end_at"] = now + PREP_DURATION_SEC
        _session["active_end_at"] = now + PREP_DURATION_SEC + ACTIVE_DURATION_SEC

    _setup_ready_since = None
    return True


def record_bounce(bounce: dict) -> None:
    if not is_recording_bounces():
        return
    with _lock:
        _session["bounces"].append(bounce)


def _compute_aggregate(bounces: list[dict]) -> dict:
    if not bounces:
        return {
            "count": 0,
            "avgScore": 0,
            "bestScore": 0,
            "feedback": "Nie wykryto odbić w czasie sesji — spróbuj ponownie",
            "gotowosc": None,
        }

    count = len(bounces)
    scores = [int(b.get("score", 0)) for b in bounces]
    avg_score = sum(scores) // count
    best_score = max(scores)
    good_count = sum(1 for s in scores if s >= 70)

    if count == 1:
        feedback = bounces[0].get("feedback", f"1 odbicie — wynik {avg_score}/100")
    elif good_count == count:
        feedback = f"{count} odbić — średnia {avg_score}/100. Świetna seria! ✓"
    elif good_count >= count // 2:
        feedback = f"{count} odbić — średnia {avg_score}/100. {good_count} poprawnych."
    else:
        feedback = f"{count} odbić — średnia {avg_score}/100. Skup się na kolanach i dłoniach."

    gotowosc_keys = ("stopa_ok", "kolana_ok", "platforma_ok", "lokcie_ok", "ruch_ok")
    gotowosc = {}
    for key in gotowosc_keys:
        ok_count = sum(1 for b in bounces if b.get("gotowosc", {}).get(key))
        gotowosc[key] = ok_count >= count / 2

    return {
        "count": count,
        "avgScore": avg_score,
        "bestScore": best_score,
        "feedback": feedback,
        "gotowosc": gotowosc,
    }


def _tick_session(now: float) -> None:
    with _lock:
        status = _session["status"]
        if status == "prep" and now >= _session["prep_end_at"]:
            _session["status"] = "active"
            status = "active"
        if status == "active" and now >= _session["active_end_at"]:
            _session["status"] = "summary"
            _session["aggregate"] = _compute_aggregate(list(_session["bounces"]))
            _session["summary_end_at"] = now + SUMMARY_DURATION_SEC
            status = "summary"
        if status == "summary" and _session["summary_end_at"] and now >= _session["summary_end_at"]:
            _session["status"] = "idle"
            _session["aggregate"] = None


def get_session_snapshot() -> dict:
    now = time.time()
    _tick_session(now)

    with _lock:
        status = _session["status"]
        seconds_remaining = 0
        if status == "prep":
            seconds_remaining = max(0, int(_session["prep_end_at"] - now + 0.999))
        elif status == "active":
            seconds_remaining = max(0, int(_session["active_end_at"] - now + 0.999))

        return {
            "sessionStatus": status,
            "sessionSecondsRemaining": seconds_remaining,
            "sessionContactCount": len(_session["bounces"]),
            "sessionSummary": _session["aggregate"],
        }


def session_metrics_overlay() -> dict:
    """Pola do merge w update_metrics()."""
    snap = get_session_snapshot()
    overlay = dict(snap)
    if snap["sessionStatus"] == "setup":
        overlay["fazaRuchu"] = "OCZEKIWANIE"
        overlay["totalContacts"] = 0
        overlay["feedbackFazy"] = "Ustaw postawę — zaznacz wszystkie segmenty na zielono"
    elif snap["sessionStatus"] == "active":
        overlay["totalContacts"] = snap["sessionContactCount"]
        overlay["fazaRuchu"] = "KONTAKT"
        with _lock:
            bounces = list(_session["bounces"])
        if bounces:
            last_score = int(bounces[-1].get("score", 0))
            overlay["score"] = last_score
            overlay["contactScore"] = last_score
            overlay["feedbackFazy"] = bounces[-1].get("feedback")
        else:
            overlay["score"] = 0
            overlay["contactScore"] = 0
    elif snap["sessionStatus"] == "prep":
        overlay["fazaRuchu"] = "PRZYGOTOWANIE"
        overlay["totalContacts"] = 0
    elif snap["sessionStatus"] == "summary" and snap["sessionSummary"]:
        summary = snap["sessionSummary"]
        overlay["fazaRuchu"] = "FOLLOW_THROUGH"
        overlay["totalContacts"] = summary.get("count", 0)
        overlay["score"] = summary.get("avgScore", 0)
        overlay["feedbackFazy"] = summary.get("feedback")
        overlay["gotowoscPrzedOdbiciem"] = summary.get("gotowosc")
        overlay["contactScore"] = summary.get("avgScore", 0)
    return overlay
