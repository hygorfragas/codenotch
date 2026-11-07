#!/usr/bin/env python3
"""Laboratório A/B/C/D do JEV com imagem.

O cache e o JSONL ficam em ~/.config/snitch, fora do git. Retomar o script
não reenvia um JPEG já cobrado. A chave não é impressa.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyze_stream import person_intersects_zone  # noqa: E402
from fact_judge import judge_item, judge_phone  # noqa: E402
from jev_image import (  # noqa: E402
    JevImageClient,
    crop_box,
    encode_jpeg,
    noul_is_true,
)

LAB_DIR = Path.home() / ".config" / "snitch" / "jev-lab"
DETECTIONS_PATH = LAB_DIR / "detections.json"
CALLS_PATH = LAB_DIR / "calls.jsonl"
SUMMARY_PATH = LAB_DIR / "summary.json"
HB_ROOT = Path("/tmp/ppe-hb")
PHONE_ROOT = Path("/tmp/laya-crops/full")
WEIGHTS = Path("/Users/hygorfragas/codenotch/snitch/storage/engine/sh17.mlpackage")
LOW_CONFIDENCE = 0.35
ZONE_PER_BAND = 40
ALIASES = {
    "glasses": "goggles",
    "safety-vest": "vest",
    "ear-mufs": "ear_protection",
    "face-mask": "mask",
    "hands": "hand",
    "shoes": "boots",
}
GT_CLASSES = {
    "helmet": (3, 6),
    "goggles": (2, 5),
    "gloves": (1, 4),
    "vest": (10, 7),
}
HEAD_ITEMS = ("helmet", "goggles")
PERSON_ITEMS = ("gloves", "vest")
QUESTIONS = {
    "helmet": "Is a safety helmet or hard hat being worn on the head in `photo`? True only when the helmet is visibly on the head. False when the head is bare.",
    "goggles": "Are protective goggles or safety glasses being worn over the eyes in `photo`? False when the eyes are uncovered.",
    "gloves": "Are protective work gloves being worn on the hands in `photo`? False for bare hands.",
    "vest": "Is a high-visibility safety vest being worn on the torso in `photo`? False when the torso has no safety vest.",
    "phone": "Is the person using a smartphone, by tapping it, looking at the screen, or holding it against the ear? A phone held still and ignored, or no phone at all, is false.",
    "zone": "Is the person standing inside the bright green polygon drawn on `photo`?",
}


def band_of(head_px: float | None) -> str | None:
    if head_px is None:
        return None
    if head_px >= 110:
        return "perto"
    if head_px >= 55:
        return "media"
    return "longe"


def center_inside(box: np.ndarray, outer: np.ndarray) -> bool:
    cx = (float(box[0]) + float(box[2])) / 2
    cy = (float(box[1]) + float(box[3])) / 2
    return float(outer[0]) <= cx <= float(outer[2]) and float(outer[1]) <= cy <= float(outer[3])


def keep_detection(label: str, confidence: float, box: np.ndarray, anchors: list[np.ndarray]) -> bool:
    if label in {"person", "head", "face"}:
        return confidence >= 0.25
    if label in {"goggles", "ear_protection", "mask", "gloves"}:
        if confidence < 0.10:
            return False
        if confidence >= 0.25:
            return True
        return any(center_inside(box, anchor) for anchor in anchors)
    return confidence >= 0.25


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def phone_labels() -> dict[str, str]:
    tree = ast.parse(Path("/tmp/laya_eval.py").read_text(encoding="utf-8"))
    labels: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "LABELS":
                value = ast.literal_eval(node.value)
                if isinstance(value, dict):
                    labels = {str(key): str(item) for key, item in value.items()}
    none_path = Path("/tmp/laya-crops/none_names.txt")
    if none_path.is_file():
        for name in none_path.read_text(encoding="utf-8").split():
            labels[name] = "sem_celular"
    for index in range(8):
        labels[f"loop-{index:02d}.jpg"] = "sem_celular"
    return labels


def read_yolo_classes(path: Path) -> set[int]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return set()
    return {int(line.split()[0]) for line in text.splitlines() if line.strip()}


def judge_ppe(name: str, detected: bool, confidence: float, on_part: bool, part_visible: bool, head_px: float) -> dict[str, str]:
    present = detected and (on_part or name in {"vest", "harness"})
    return judge_item(
        {
            "name": name,
            "conf": confidence if present else 0.0,
            "on_part": on_part or name in {"vest", "harness"},
            "part_visible": part_visible,
            "votes_present": 1 if present else 0,
            "votes_window": 1,
            "zoom": "not_run",
            "detector": True,
        },
        {"head_height_px": head_px, "head_occluded": False},
    )


def in_doubt(detected: bool, confidence: float, judge_status: str) -> bool:
    if judge_status == "indeterminado":
        return True
    return bool(detected and confidence < LOW_CONFIDENCE)


def arm_d(arm_a: str, doubt: bool, jev_positive: bool | None) -> str | None:
    if not doubt:
        return arm_a
    if jev_positive is None:
        return None
    return "com" if jev_positive else "sem"


def score(rows: list[tuple[bool, str]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "precision": None, "recall": None, "accuracy": None, "indeterminate": None, "sem_precision": None}
    true_positive = false_positive = false_negative = correct = indeterminate = sem_true = sem_false = 0
    for truth, prediction in rows:
        if prediction == "indet":
            indeterminate += 1
        if prediction == "com" and truth:
            true_positive += 1
        elif prediction == "com":
            false_positive += 1
        if prediction == "sem" and not truth:
            sem_true += 1
        elif prediction == "sem" and truth:
            sem_false += 1
        if (truth and prediction == "com") or ((not truth) and prediction == "sem"):
            correct += 1
        if truth and prediction != "com":
            false_negative += 1

    def ratio(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return round(numerator / denominator, 4)

    return {
        "n": len(rows),
        "precision": ratio(true_positive, true_positive + false_positive),
        "recall": ratio(true_positive, true_positive + false_negative),
        "accuracy": ratio(correct, len(rows)),
        "indeterminate": ratio(indeterminate, len(rows)),
        "sem_precision": ratio(sem_true, sem_true + sem_false),
    }


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((percent / 100) * (len(ordered) - 1))
    return round(ordered[index], 1)


def detect(model: Any) -> dict[str, Any]:
    names = model.names
    records = []
    for image_path in sorted((HB_ROOT / "images").glob("*.jpg")):
        label_path = HB_ROOT / "labels" / f"{image_path.stem}.txt"
        classes = read_yolo_classes(label_path) if label_path.is_file() else set()
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        result = model(image, verbose=False, conf=0.10, imgsz=640)[0]
        boxes: list[dict[str, Any]] = []
        if result.boxes is not None:
            for xyxy, class_id, confidence in zip(
                result.boxes.xyxy.cpu().numpy(),
                result.boxes.cls.cpu().numpy(),
                result.boxes.conf.cpu().numpy(),
            ):
                label = ALIASES.get(str(names[int(class_id)]), str(names[int(class_id)]))
                boxes.append({"label": label, "conf": float(confidence), "xyxy": [float(value) for value in xyxy]})
        anchors = [
            np.array(box["xyxy"], dtype=np.float32)
            for box in boxes
            if box["label"] in {"person", "head", "face"} and box["conf"] >= 0.25
        ]
        kept = []
        for box in boxes:
            xyxy = np.array(box["xyxy"], dtype=np.float32)
            if keep_detection(box["label"], box["conf"], xyxy, anchors):
                kept.append({**box, "xyxy": box["xyxy"]})
        persons = [box for box in kept if box["label"] == "person"]
        heads = [box for box in kept if box["label"] == "head"]
        if not persons or not heads:
            continue
        head_px = max(box["xyxy"][3] - box["xyxy"][1] for box in heads)
        person_box = max(persons, key=lambda box: (box["xyxy"][2] - box["xyxy"][0]) * (box["xyxy"][3] - box["xyxy"][1]))
        head_box = max(heads, key=lambda box: box["xyxy"][3] - box["xyxy"][1])
        faces = [box for box in kept if box["label"] == "face"]
        hands = [box for box in kept if box["label"] == "hand"]
        items = {}
        for name, (positive, negative) in GT_CLASSES.items():
            if positive in classes and negative in classes:
                continue
            if positive not in classes and negative not in classes:
                continue
            truth = positive in classes
            matched = []
            for box in kept:
                if box["label"] != name:
                    continue
                xyxy = np.array(box["xyxy"], dtype=np.float32)
                if any(center_inside(xyxy, np.array(person["xyxy"], dtype=np.float32)) for person in persons):
                    matched.append(box)
            detected = bool(matched)
            confidence = max((box["conf"] for box in matched), default=0.0)
            if name == "helmet":
                part_boxes = heads
            elif name == "goggles":
                part_boxes = faces
            elif name == "gloves":
                part_boxes = hands
            else:
                part_boxes = persons
            on_part = False
            for box in matched:
                xyxy = np.array(box["xyxy"], dtype=np.float32)
                if name in {"vest", "harness"}:
                    on_part = True
                elif any(center_inside(xyxy, np.array(part["xyxy"], dtype=np.float32)) for part in part_boxes):
                    on_part = True
            part_visible = True if name in {"vest", "harness"} else bool(part_boxes)
            verdict = judge_ppe(name, detected, confidence, on_part, part_visible, head_px)
            arm_a = "com" if detected else "sem"
            items[name] = {
                "truth": truth,
                "detected": detected,
                "conf": round(confidence, 4),
                "on_part": on_part,
                "part_visible": part_visible,
                "arm_a": arm_a,
                "arm_b": verdict["status"],
                "rule_b": verdict["rule"],
                "doubt": in_doubt(detected, confidence, verdict["status"]),
            }
        records.append({
            "id": image_path.stem,
            "path": str(image_path),
            "head_px": round(head_px, 1),
            "band": band_of(head_px),
            "head_box": head_box["xyxy"],
            "person_box": person_box["xyxy"],
            "items": items,
        })
    phone_rows = []
    labels = phone_labels()
    for name, label in sorted(labels.items()):
        image_path = PHONE_ROOT / name
        if not image_path.is_file():
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        result = model(image, verbose=False, conf=0.10, imgsz=640)[0]
        head_px = None
        person_box = None
        if result.boxes is not None:
            heads = []
            persons = []
            for xyxy, class_id, confidence in zip(
                result.boxes.xyxy.cpu().numpy(),
                result.boxes.cls.cpu().numpy(),
                result.boxes.conf.cpu().numpy(),
            ):
                class_name = ALIASES.get(str(names[int(class_id)]), str(names[int(class_id)]))
                if float(confidence) < 0.25:
                    continue
                if class_name == "head":
                    heads.append(xyxy)
                elif class_name == "person":
                    persons.append(xyxy)
            if heads:
                head_px = max(float(box[3] - box[1]) for box in heads)
            if persons:
                chosen = max(persons, key=lambda box: float((box[2] - box[0]) * (box[3] - box[1])))
                person_box = [float(value) for value in chosen]
        phone_verdict = judge_phone({"head_height_px": head_px or 0, "phone": {"votes_present": 0, "votes_window": 1}})
        phone_rows.append({
            "id": name,
            "path": str(image_path),
            "label": label,
            "truth": label == "uso",
            "head_px": None if head_px is None else round(head_px, 1),
            "band": band_of(head_px),
            "person_box": person_box,
            "arm_a": "sem",
            "arm_b": "sem" if phone_verdict["status"] == "nao_uso" else "com",
            "rule_b": phone_verdict["rule"],
            "doubt": False,
        })
    payload = {"hb": records, "phone": phone_rows, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    atomic_write(DETECTIONS_PATH, json.dumps(payload) + "\n")
    return payload


def draw_polygon(image: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    output = image.copy()
    points = np.round(polygon).astype(np.int32).reshape(-1, 1, 2)
    overlay = output.copy()
    cv2.fillPoly(overlay, [points], (0, 255, 0))
    output = cv2.addWeighted(overlay, 0.35, output, 0.65, 0)
    cv2.polylines(output, [points], True, (0, 255, 0), 4)
    return output


def outside_polygon(image: np.ndarray, person_box: list[float]) -> np.ndarray | None:
    height, width = image.shape[:2]
    side = max(20, int(min(height, width) * 0.12))
    corners = ((0, 0), (width - side, 0), (0, height - side), (width - side, height - side))
    box = np.array(person_box, dtype=np.float32)
    for left, top in corners:
        polygon = np.array([
            [left, top],
            [left + side, top],
            [left + side, top + side],
            [left, top + side],
        ], dtype=np.float32)
        if not person_intersects_zone(box, polygon):
            return polygon
    return None


def zone_jobs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    counts = {"perto": 0, "media": 0, "longe": 0}
    for record in records:
        band = record.get("band")
        if band not in counts or counts[band] >= ZONE_PER_BAND:
            continue
        counts[band] += 1
        chosen.append(record)
    return chosen


def send_job(
    client: JevImageClient,
    job_id: str,
    image: np.ndarray,
    questions: dict[str, str],
    local: dict[str, Any],
    done: set[str],
) -> str:
    if job_id in done:
        return "skip"
    jpeg = encode_jpeg(image)
    result = client.ask_jpeg(jpeg, questions)
    if result.get("status") == 401:
        append_jsonl(CALLS_PATH, {"id": job_id, "status": 401, "local": local})
        return "auth"
    if result.get("status") == "teto":
        append_jsonl(CALLS_PATH, {"id": job_id, "status": "teto", "local": local})
        return "teto"
    answers = {}
    raw_answers = result.get("answers") or {}
    if isinstance(raw_answers, dict):
        for name in questions:
            answers[name] = {
                "positive": noul_is_true(raw_answers.get(name)),
                "raw": raw_answers.get(name),
            }
    append_jsonl(CALLS_PATH, {
        "id": job_id,
        "status": result.get("status"),
        "sha256": result.get("sha256"),
        "cache": result.get("cache"),
        "charged": result.get("charged"),
        "latency_ms": result.get("latency_ms"),
        "answers": answers,
        "local": local,
    })
    done.add(job_id)
    ledger = client.ledger
    print(
        f"{job_id} status={result.get('status')} cache={result.get('cache')} "
        f"usd={ledger['usd']:.4f} sent={ledger['images_sent']}",
        flush=True,
    )
    if result.get("status") != 200:
        return "error"
    return "ok"


def run_calls(client: JevImageClient, detected: dict[str, Any]) -> str:
    done = {row["id"] for row in load_jsonl(CALLS_PATH) if row.get("status") == 200}
    for record in detected["hb"]:
        image = cv2.imread(record["path"])
        if image is None:
            continue
        head_questions = {
            name: QUESTIONS[name]
            for name in HEAD_ITEMS
            if name in record["items"]
        }
        if head_questions:
            crop = crop_box(image, record["head_box"], 0.5)
            state = send_job(client, f"hb:{record['id']}:head", crop, head_questions, {"band": record["band"], "items": record["items"]}, done)
            if state in {"auth", "teto"}:
                return state
        person_questions = {
            name: QUESTIONS[name]
            for name in PERSON_ITEMS
            if name in record["items"]
        }
        if person_questions:
            crop = crop_box(image, record["person_box"], 0.08)
            state = send_job(client, f"hb:{record['id']}:person", crop, person_questions, {"band": record["band"], "items": record["items"]}, done)
            if state in {"auth", "teto"}:
                return state
    for record in zone_jobs(detected["hb"]):
        image = cv2.imread(record["path"])
        if image is None:
            continue
        person = np.array(record["person_box"], dtype=np.float32)
        inside = np.array([
            [person[0], person[1]],
            [person[2], person[1]],
            [person[2], person[3]],
            [person[0], person[3]],
        ], dtype=np.float32)
        if person_intersects_zone(person, inside):
            state = send_job(
                client,
                f"hb:{record['id']}:zone-in",
                draw_polygon(image, inside),
                {"zone": QUESTIONS["zone"]},
                {"band": record["band"], "truth": True, "arm_a": "com", "arm_b": "com", "doubt": False},
                done,
            )
            if state in {"auth", "teto"}:
                return state
        outside = outside_polygon(image, record["person_box"])
        if outside is not None:
            state = send_job(
                client,
                f"hb:{record['id']}:zone-out",
                draw_polygon(image, outside),
                {"zone": QUESTIONS["zone"]},
                {"band": record["band"], "truth": False, "arm_a": "sem", "arm_b": "sem", "doubt": False},
                done,
            )
            if state in {"auth", "teto"}:
                return state
    for record in detected["phone"]:
        image = cv2.imread(record["path"])
        if image is None:
            continue
        crop = crop_box(image, record["person_box"], 0.08) if record.get("person_box") else image
        state = send_job(
            client,
            f"phone:{record['id']}",
            crop,
            {"phone": QUESTIONS["phone"]},
            record,
            done,
        )
        if state in {"auth", "teto"}:
            return state
    return "ok"


def prediction_rows(calls: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, list[tuple[bool, str]]]]]:
    grouped: dict[str, dict[str, dict[str, list[tuple[bool, str]]]]] = {}

    def add(item: str, band: str, arm: str, truth: bool, prediction: str | None) -> None:
        if prediction not in {"com", "sem", "indet"}:
            return
        grouped.setdefault(item, {}).setdefault(band, {}).setdefault(arm, []).append((truth, prediction))

    for call in calls:
        if call.get("status") != 200:
            continue
        local = call.get("local") or {}
        answers = call.get("answers") or {}
        job_id = str(call.get("id") or "")
        if ":zone-" in job_id:
            answer = (answers.get("zone") or {}).get("positive")
            if not isinstance(local.get("truth"), bool) or not isinstance(answer, bool):
                continue
            band = local.get("band") or "sem_faixa"
            truth = bool(local["truth"])
            add("zona", band, "A", truth, local.get("arm_a"))
            add("zona", band, "B", truth, local.get("arm_b"))
            add("zona", band, "C", truth, "com" if answer else "sem")
            add("zona", band, "D", truth, arm_d(str(local.get("arm_a")), bool(local.get("doubt")), answer))
            continue
        if job_id.startswith("phone:"):
            answer = (answers.get("phone") or {}).get("positive")
            if not isinstance(local.get("truth"), bool) or not isinstance(answer, bool):
                continue
            band = local.get("band") or "sem_cabeca"
            truth = bool(local["truth"])
            jev = "com" if answer else "sem"
            add("celular", band, "A", truth, local.get("arm_a"))
            add("celular", band, "B", truth, local.get("arm_b"))
            add("celular", band, "C", truth, jev)
            add("celular", band, "D", truth, arm_d(str(local.get("arm_a")), bool(local.get("doubt")), answer))
            continue
        items = local.get("items") or {}
        role_items = HEAD_ITEMS if job_id.endswith(":head") else PERSON_ITEMS
        for name in role_items:
            item = items.get(name)
            answer = (answers.get(name) or {}).get("positive")
            if not item or not isinstance(answer, bool):
                continue
            band = local.get("band") or "sem_faixa"
            truth = bool(item["truth"])
            jev = "com" if answer else "sem"
            add(name, band, "A", truth, item.get("arm_a"))
            add(name, band, "B", truth, "indet" if item.get("arm_b") == "indeterminado" else item.get("arm_b"))
            add(name, band, "C", truth, jev)
            add(name, band, "D", truth, arm_d(str(item.get("arm_a")), bool(item.get("doubt")), answer))
    return grouped


def summarize(client: JevImageClient) -> dict[str, Any]:
    calls = load_jsonl(CALLS_PATH)
    grouped = prediction_rows(calls)
    table = {}
    for item, bands in grouped.items():
        table[item] = {}
        for band, arms in bands.items():
            table[item][band] = {arm: score(rows) for arm, rows in arms.items()}
    latencies = [
        float(call["latency_ms"])
        for call in calls
        if call.get("charged") and isinstance(call.get("latency_ms"), (int, float))
    ]
    doubts = 0
    decided = 0
    for call in calls:
        local = call.get("local") or {}
        items = local.get("items")
        if isinstance(items, dict):
            for item in items.values():
                decided += 1
                if item.get("doubt"):
                    doubts += 1
        elif "doubt" in local:
            decided += 1
            if local.get("doubt"):
                doubts += 1
    summary = {
        "table": table,
        "latency_ms": {"n": len(latencies), "p50": percentile(latencies, 50), "p95": percentile(latencies, 95)},
        "ledger": client.ledger,
        "calls": len(calls),
        "charged_now": sum(1 for call in calls if call.get("charged")),
        "cache_hits": sum(1 for call in calls if call.get("cache")),
        "doubt_cases": doubts,
        "decided_cases": decided,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    atomic_write(SUMMARY_PATH, json.dumps(summary) + "\n")
    return summary


def probe(client: JevImageClient) -> bool:
    image = np.full((280, 280, 3), 40, dtype=np.uint8)
    result = client.ask_jpeg(encode_jpeg(image), {"solid": "Is `photo` a single flat color, with no person and no object?"})
    print(
        f"probe status={result.get('status')} cache={result.get('cache')} "
        f"charged={result.get('charged')} usd={client.ledger['usd']:.4f}",
        flush=True,
    )
    if result.get("status") == 401 or result.get("error") == "auth":
        return False
    answer = (result.get("answers") or {}).get("solid")
    return result.get("status") == 200 and noul_is_true(answer) is not None


def main() -> int:
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    client = JevImageClient(ceiling_usd=0.50)
    if not probe(client):
        print("PROBE_FAILED", flush=True)
        return 2
    if DETECTIONS_PATH.is_file():
        detected = json.loads(DETECTIONS_PATH.read_text(encoding="utf-8"))
        print(f"detections_reuse hb={len(detected.get('hb') or [])} phone={len(detected.get('phone') or [])}", flush=True)
    else:
        os.environ.setdefault("SNITCH_YOLO_DEVICE", "coreml")
        from ultralytics import YOLO
        model = YOLO(str(WEIGHTS))
        detected = detect(model)
        print(f"detections_saved hb={len(detected['hb'])} phone={len(detected['phone'])}", flush=True)
    state = run_calls(client, detected)
    summary = summarize(client)
    print(f"state={state} usd={summary['ledger']['usd']} calls={summary['calls']}", flush=True)
    if state == "auth":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
