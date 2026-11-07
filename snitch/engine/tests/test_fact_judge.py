import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fact_judge import judge_facts  # noqa: E402


def _person(**extra):
    base = {
        "tracker_id": 1,
        "head_height_px": 140,
        "head_occluded": False,
        "items": {},
        "phone": {"votes_present": 0, "votes_window": 5},
    }
    base.update(extra)
    return base


def _item(**extra):
    base = {
        "conf": 0.0,
        "on_part": False,
        "part_visible": True,
        "votes_present": 0,
        "votes_window": 5,
        "zoom": "not_run",
        "detector": True,
    }
    base.update(extra)
    return base


def test_same_facts_always_give_the_same_sentence():
    facts = {"persons": [_person(items={"helmet": _item(votes_present=4, on_part=True, conf=0.6)})]}
    assert judge_facts(facts) == judge_facts(facts)


def test_a_visible_head_without_votes_is_missing_and_a_far_head_is_not():
    near = judge_facts({"persons": [_person(items={"helmet": _item()})]})
    far = judge_facts({"persons": [_person(head_height_px=40, items={"helmet": _item()})]})
    assert near["persons"][0]["ppe"]["helmet"]["status"] == "sem"
    assert far["persons"][0]["ppe"]["helmet"]["status"] == "indeterminado"


def test_an_earplug_without_a_detector_is_never_an_infraction():
    verdict = judge_facts({"persons": [_person(items={"earplug": _item(detector=False)})]})
    assert verdict["persons"][0]["ppe"]["earplug"]["status"] == "indeterminado"


def test_phone_at_the_ear_is_use_and_a_still_hand_is_not():
    ear = judge_facts({"persons": [_person(phone={
        "votes_present": 4, "votes_window": 5, "dist_ear_px": 40,
        "dist_face_px": 200, "dist_wrist_px": 180, "face_toward_phone": False, "motion_px": 0,
    })]})
    still = judge_facts({"persons": [_person(phone={
        "votes_present": 4, "votes_window": 5, "dist_ear_px": 200,
        "dist_face_px": 200, "dist_wrist_px": 40, "face_toward_phone": False, "motion_px": 2,
    })]})
    assert ear["persons"][0]["phone"]["mode"] == "orelha"
    assert still["persons"][0]["phone"]["status"] == "nao_uso"
