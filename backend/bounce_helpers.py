"""Wspólna logika budowania rekordu odbicia dla sesji treningowej."""

from __future__ import annotations

import time


def build_bounce_record(
    typ: str,
    *,
    knee: int | float | None = None,
    bio_front: dict | None = None,
    bio_bok: dict | None = None,
    fusion_score: int | None = None,
) -> dict:
    bio_front = bio_front or {}
    bio_bok = bio_bok or {}
    dane_stopy = bio_front.get("dane_stopy") or {}

    problemy = []
    kat_k = bio_bok.get("kat_kolana")

    if dane_stopy.get("nogi_widoczne") and not dane_stopy.get("rozstawienie_ok", False):
        problemy.append("popraw stopy")
    if kat_k is not None and (kat_k < 105 or kat_k > 155):
        problemy.append("ugnij kolana")
    elif kat_k is not None and kat_k > 160:
        problemy.append("ugnij kolana")
    elif knee is not None and (knee < 105 or knee > 155):
        problemy.append("ugnij kolana")
    elif knee is not None and knee > 160:
        problemy.append("ugnij kolana")
    if bio_bok.get("kolana_proste", False):
        problemy.append("ugnij kolana")
    if not bio_front.get("nadgarstki_zlaczone", False):
        problemy.append("złącz dłonie")
    kat_l = bio_front.get("kat_lokcia_l")
    kat_p = bio_front.get("kat_lokcia_p")
    if kat_l is not None and kat_p is not None and (
        kat_l < 55 or kat_l > 158 or kat_p < 55 or kat_p > 158
    ):
        problemy.append("popraw łokcie")
    if bio_bok and not bio_bok.get("zamach_wykryty", False):
        problemy.append("praca nóg")

    if not problemy:
        score = 72
        fb = f"Poprawne odbicie {typ}! ✓"
    elif len(problemy) == 1:
        score = 52
        fb = f"Odbicie {typ} — popraw: {problemy[0]}"
    elif len(problemy) == 2:
        score = 38
        fb = f"Odbicie {typ} — popraw: {', '.join(problemy)}"
    else:
        score = 25
        fb = f"Odbicie {typ} — popraw: {', '.join(problemy[:2])}…"

    # fusion_score bywa zawyżony (Dual-Cam) — tylko lekka korekta w dół
    if fusion_score is not None and fusion_score < score:
        score = max(25, fusion_score)

    kolana_ok = (
        not bio_bok.get("kolana_proste", False)
        and (kat_k is None or kat_k <= 160)
        and (knee is None or knee <= 160)
    )
    gotowosc = {
        "stopa_ok": bool(dane_stopy.get("rozstawienie_ok")) if dane_stopy.get("nogi_widoczne") else False,
        "kolana_ok": kolana_ok,
        "platforma_ok": bool(bio_front.get("nadgarstki_zlaczone", False)),
        "lokcie_ok": kat_l is not None and kat_p is not None and 55 <= kat_l <= 158 and 55 <= kat_p <= 158,
        "ruch_ok": bool(bio_bok.get("zamach_wykryty", False)),
    }

    return {
        "typ": typ,
        "score": int(score),
        "feedback": fb,
        "gotowosc": gotowosc,
        "timestamp": time.time(),
    }
