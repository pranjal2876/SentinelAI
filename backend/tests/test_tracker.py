"""Unit tests for the multi-object tracker — ID persistence across frames."""
from app.vision.tracking.tracker import MultiObjectTracker, _iou
from app.vision.types import Detection


def _det(x1, y1, x2, y2, conf=0.9, cls=0, name="person") -> Detection:
    return Detection(bbox=(x1, y1, x2, y2), confidence=conf,
                     class_id=cls, class_name=name)


def test_iou_identical_boxes():
    assert abs(_iou((0, 0, 10, 10), (0, 0, 10, 10)) - 1.0) < 1e-6


def test_iou_disjoint_boxes():
    assert _iou((0, 0, 10, 10), (100, 100, 110, 110)) == 0.0


def test_track_id_persists_across_frames():
    tracker = MultiObjectTracker(min_hits=1)
    tid = None
    # Object moving slowly to the right; ID must stay stable.
    for i in range(6):
        dets = [_det(10 + i * 5, 10, 40 + i * 5, 80)]
        tracks = tracker.update(dets, fps=25)
        assert len(tracks) == 1
        if tid is None:
            tid = tracks[0].track_id
        assert tracks[0].track_id == tid


def test_new_object_gets_new_id():
    tracker = MultiObjectTracker(min_hits=1)
    t1 = tracker.update([_det(10, 10, 40, 80)], fps=25)
    t2 = tracker.update([_det(10, 10, 40, 80), _det(500, 500, 540, 580)], fps=25)
    ids = {t.track_id for t in t2}
    assert t1[0].track_id in ids
    assert len(ids) == 2
