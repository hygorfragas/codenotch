from state_builder import TrackedPerson, build_jev_state


def test_build_jev_state_serializes_persons():
    persons = [
        TrackedPerson(
            tracker_id=7,
            bbox_xyxy=(10.0, 20.0, 30.0, 40.0),
            in_zones=["banheiro"],
            ppe_detected=["helmet"],
            ppe_missing=["vest"],
        )
    ]
    state = build_jev_state(camera_id=1, frame_index=3, persons=persons)
    assert state["camera_id"] == 1
    assert state["frame_index"] == 3
    assert state["persons"][0]["tracker_id"] == 7
    assert state["persons"][0]["ppe_missing"] == ["vest"]
