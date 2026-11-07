"""Juiz determinístico. Os mesmos fatos produzem a mesma sentença, sem imagem."""

from __future__ import annotations

from typing import Any

PARTS = {
    "helmet": "head",
    "goggles": "face",
    "glasses": "face",
    "mask": "face",
    "ear_protection": "ear",
    "earplug": "ear",
    "gloves": "hand",
    "boots": "foot",
    "vest": "torso",
    "harness": "torso",
}


def distance_band(head_height_px: float) -> str:
    if head_height_px >= 110:
        return "near"
    if head_height_px >= 55:
        return "mid"
    return "far"


def judge_item(item: dict[str, Any], person: dict[str, Any]) -> dict[str, str]:
    if item.get("detector") is False:
        return {"status": "indeterminado", "rule": "sem_detector"}
    band = distance_band(float(person.get("head_height_px") or 0))
    window = max(1, int(item.get("votes_window") or 1))
    present = int(item.get("votes_present") or 0)
    need = window // 2 + 1
    majority = present >= need
    absent = (window - present) >= need
    conf = float(item.get("conf") or 0)
    on_part = bool(item.get("on_part"))
    part_visible = bool(item.get("part_visible"))
    zoom = str(item.get("zoom") or "not_run")
    if person.get("head_occluded") and PARTS.get(str(item.get("name")), "") in {"head", "face", "ear"}:
        return {"status": "indeterminado", "rule": "cabeca_oculta"}
    if zoom == "found" or (majority and on_part and conf >= 0.2):
        rule = "zoom" if zoom == "found" else "voto_na_parte"
        return {"status": "com", "rule": rule}
    if not part_visible:
        return {"status": "indeterminado", "rule": "parte_oculta"}
    if band == "far":
        return {"status": "indeterminado", "rule": "longe"}
    if band == "mid" and zoom != "missed":
        return {"status": "indeterminado", "rule": "media_sem_zoom"}
    if absent:
        return {"status": "sem", "rule": "parte_visivel_sem_voto"}
    return {"status": "indeterminado", "rule": "votos_insuficientes"}


def judge_phone(person: dict[str, Any]) -> dict[str, str | None]:
    phone = person.get("phone") or {}
    present = int(phone.get("votes_present") or 0)
    window = max(1, int(phone.get("votes_window") or 1))
    need = window // 2 + 1
    if present < need:
        return {"status": "nao_uso", "mode": None, "rule": "sem_persistencia"}
    head = max(float(person.get("head_height_px") or 1), 1.0)
    ear = float(phone.get("dist_ear_px") if phone.get("dist_ear_px") is not None else 1e9) / head
    face = float(phone.get("dist_face_px") if phone.get("dist_face_px") is not None else 1e9) / head
    wrist = float(phone.get("dist_wrist_px") if phone.get("dist_wrist_px") is not None else 1e9) / head
    motion = float(phone.get("motion_px") or 0)
    if ear <= 0.55:
        return {"status": "uso", "mode": "orelha", "rule": "perto_da_orelha"}
    if phone.get("face_toward_phone") and face <= 1.0:
        return {"status": "uso", "mode": "olhando", "rule": "rosto_voltado"}
    if wrist <= 0.75 and motion >= 8:
        return {"status": "uso", "mode": "mexendo", "rule": "pulso_em_movimento"}
    if wrist <= 0.75:
        return {"status": "nao_uso", "mode": None, "rule": "na_mao_parado"}
    return {"status": "nao_uso", "mode": None, "rule": "longe_do_corpo"}


def judge_facts(facts: dict[str, Any]) -> dict[str, Any]:
    persons = []
    for person in facts.get("persons") or []:
        items = {}
        for name, item in (person.get("items") or {}).items():
            payload = dict(item)
            payload["name"] = name
            items[name] = judge_item(payload, person)
        persons.append({
            "tracker_id": person.get("tracker_id"),
            "ppe": items,
            "phone": judge_phone(person),
        })
    return {"persons": persons}
