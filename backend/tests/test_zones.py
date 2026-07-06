"""Unit tests for zone geometry (point-in-polygon, line crossing, side test)."""
from app.vision.threat.zones import (
    Zone,
    ZoneType,
    segments_intersect,
    side_of_line,
)


def _square_zone() -> Zone:
    return Zone(
        id="z1", name="box", type=ZoneType.RESTRICTED,
        points=[(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)],
    )


def test_point_inside_polygon():
    z = _square_zone()
    # Center of a 1000x1000 frame is inside the [0.25..0.75] square.
    assert z.contains((500, 500), 1000, 1000) is True


def test_point_outside_polygon():
    z = _square_zone()
    assert z.contains((100, 100), 1000, 1000) is False


def test_segments_intersect():
    assert segments_intersect((0, 0), (10, 10), (0, 10), (10, 0)) is True
    assert segments_intersect((0, 0), (1, 1), (5, 5), (6, 6)) is False


def test_side_of_line_sign_flips():
    a, b = (0, 0), (10, 0)
    assert side_of_line((5, 5), a, b) > 0     # above
    assert side_of_line((5, -5), a, b) < 0    # below
