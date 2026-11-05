"""Core geodesy on the WGS 84 ellipsoid (P1-T1; NAV-1, INF-3, DAT-14, AD-7, AD-17)."""
import math

import numpy as np
import pytest
from geographiclib.geodesic import Geodesic

from mapcore.geo import geodesy as g

LONDON = (51.507, -0.128)
PARIS = (48.857, 2.352)


# Distance and bearing (INF-3) --------------------------------------------------------

def test_london_to_paris_distance_and_bearing():
    km = g.distance_m(*LONDON, *PARIS) / 1000
    assert km == pytest.approx(344, abs=1)
    assert g.bearing_deg(*LONDON, *PARIS) == pytest.approx(148, abs=1)


def test_inverse_gives_both_bearings():
    metres, start, arrival = g.inverse(*LONDON, *PARIS)
    assert metres == pytest.approx(g.distance_m(*LONDON, *PARIS))
    assert 0 <= start < 360 and 0 <= arrival < 360
    assert arrival > start  # heading turns clockwise on the way to Paris


def test_distance_across_the_180_degree_line_is_short():
    assert g.distance_m(-17.0, 179.9, -17.0, -179.9) / 1000 == pytest.approx(21.3, abs=0.2)


def test_rough_distances_rank_like_exact_ones():
    lats = np.array([48.857, 40.4, 52.52, 55.75])
    lons = np.array([2.352, -3.7, 13.4, 37.6])
    rough = g.rough_distances_m(*LONDON, lats, lons)
    exact = np.array([g.distance_m(*LONDON, la, lo) for la, lo in zip(lats, lons)])
    assert np.argsort(rough).tolist() == np.argsort(exact).tolist()
    assert np.all(np.abs(rough / exact - 1) < 0.006)


# Stepping north and south (NAV-1) ----------------------------------------------------

def test_step_north_along_the_meridian():
    move = g.step_meridian(51.5, -0.1, 10_000)
    assert move.lon == pytest.approx(-0.1)
    assert g.distance_m(51.5, -0.1, move.lat, move.lon) == pytest.approx(10_000, abs=0.01)
    assert move.heading == 0
    assert move.path[0] == (51.5, -0.1) and move.path[-1] == (move.lat, -0.1)


def test_step_south_along_the_meridian():
    move = g.step_meridian(51.5, -0.1, -1_000_000)
    assert move.lat < 51.5 and move.heading == 180
    assert g.distance_m(51.5, -0.1, move.lat, move.lon) == pytest.approx(1_000_000, abs=0.01)


def test_a_step_that_would_pass_the_north_pole_is_refused():
    assert g.step_meridian(89.5, 10.0, 100_000) is None


def test_a_step_that_would_pass_the_south_pole_is_refused():
    assert g.step_meridian(-89.5, 10.0, -100_000) is None


def test_a_step_that_would_reach_a_pole_exactly_is_refused():
    assert g.step_meridian(89.0, 0.0, g.meridian_to_pole_m(89.0, True)) is None
    assert g.step_meridian(89.0, 0.0, g.meridian_to_pole_m(89.0, True) - 1) is not None


# Stepping east and west (NAV-1, AD-17) -----------------------------------------------

def test_step_east_follows_the_line_of_latitude():
    move = g.step_parallel(60.0, 10.0, 50_000)
    assert move.lat == 60.0 and move.heading == 90
    # The change in longitude is the distance over the radius of the line of latitude.
    assert math.radians(move.lon - 10.0) * g.parallel_radius_m(60.0) == pytest.approx(50_000)
    assert all(lat == 60.0 for lat, _ in move.path)


@pytest.mark.parametrize("place, lat", [("Fiji", -17.0), ("the Bering Strait", 65.5)])
def test_a_step_east_from_179_9_east_lands_at_179_9_west(place, lat):
    metres = math.radians(0.2) * g.parallel_radius_m(lat)
    move = g.step_parallel(lat, 179.9, metres)
    assert move.lon == pytest.approx(-179.9, abs=1e-9), place
    assert move.lat == lat
    # The path carries on past 180 so its points are never 360 degrees apart.
    lons = [lon for _, lon in move.path]
    assert lons[-1] == pytest.approx(180.1)
    assert max(abs(b - a) for a, b in zip(lons, lons[1:])) < 1


def test_a_step_west_from_179_9_west_lands_at_179_9_east():
    metres = math.radians(0.2) * g.parallel_radius_m(-17.0)
    move = g.step_parallel(-17.0, -179.9, -metres)
    assert move.lon == pytest.approx(179.9, abs=1e-9) and move.heading == 270


def test_no_east_step_at_a_pole():
    assert g.step_parallel(90.0, 0.0, 1000) is None


@pytest.mark.parametrize("lat", [0.0, 45.0, -80.0])
def test_path_points_are_close_enough_to_follow_the_earth(lat):
    for move in (g.step_meridian(lat, 0.0, 1_000_000 if lat < 0 else -1_000_000), g.step_parallel(lat, 0.0, 1_000_000)):
        gaps = [g.distance_m(a[0], a[1], b[0], b[1]) for a, b in zip(move.path, move.path[1:])]
        assert max(gaps) <= g.PATH_SPACING_M
    assert len(g.step_parallel(0.0, 0.0, 5).path) == 2


def test_free_step_follows_the_geodesic_and_gives_the_arrival_heading():
    move = g.step_geodesic(*LONDON, 148.0, 344_000)
    direct = Geodesic.WGS84.Direct(*LONDON, 148.0, 344_000)
    assert move.lat == pytest.approx(direct["lat2"]) and move.lon == pytest.approx(direct["lon2"])
    assert move.heading == pytest.approx(direct["azi2"] % 360, abs=0.01)


def test_free_step_across_the_180_degree_line_wraps():
    move = g.step_geodesic(-17.0, 179.9, 90.0, 30_000)
    assert -180 < move.lon < -179.5
    assert move.path[-1][1] > 180  # the path's longitudes carry on


# Longitudes, boxes and centres (AD-17, DAT-14) ---------------------------------------

@pytest.mark.parametrize("lon, wrapped", [(190, -170), (-180, 180), (180, 180), (-190, 170), (540, 180), (0, 0)])
def test_wrap_lon(lon, wrapped):
    assert g.wrap_lon(lon) == wrapped


def test_a_box_across_the_line_is_a_few_degrees_wide_and_its_centre_is_in_it():
    # Shaped like Fiji: parts on both sides of the 180 degree line.
    box = g.wrap_box([(177.0, 180.0), (-180.0, -178.0)], -19.0, -16.0)
    assert box.crosses
    assert box.width < 8, box  # not nearly 360
    lat, lon = g.box_centre(box)
    assert -19 < lat < -16 and (lon > 177 or lon < -178)


def test_a_wide_box_across_the_line():
    # Shaped like Russia.
    box = g.wrap_box([(27.0, 180.0), (-180.0, -169.0)], 41.0, 82.0)
    assert box.crosses and 150 < box.width < 200
    assert box.contains_lon(180) and box.contains_lon(-175) and not box.contains_lon(-30)


def test_a_box_all_the_way_round_has_the_south_pole_as_its_centre():
    # Shaped like Antarctica.
    box = g.wrap_box([(-180.0, 180.0)], -90.0, -60.0)
    assert box.round_the_world
    assert g.box_centre(box) == (-90.0, 0.0)


def test_a_box_not_crossing_the_line():
    box = g.wrap_box([(-8.0, 2.0), (-1.0, 1.8)], 49.9, 60.9)
    assert not box.crosses and box.width == pytest.approx(10.0)
    assert g.box_centre(box) == pytest.approx((55.4, -3.0))


# Areas on the ellipsoid (DAT-14) -----------------------------------------------------

def _polygon_area_geographiclib(lons, lats):
    poly = Geodesic.WGS84.Polygon()
    for lo, la in zip(lons, lats):
        poly.AddPoint(la, lo)
    return abs(poly.Compute()[2])


def test_ring_area_matches_geographiclib():
    # A 1 by 1 degree square near London, closed.
    lons = [0.0, 1.0, 1.0, 0.0, 0.0]
    lats = [51.0, 51.0, 52.0, 52.0, 51.0]
    ours = g.ring_area_m2(lons, lats)
    # GeographicLib joins the corners with shortest lines, not lines of latitude,
    # so give it the same densified edges.
    dl, dt = g.densify(lons, lats, 0.01)
    assert ours == pytest.approx(_polygon_area_geographiclib(dl[:-1], dt[:-1]), rel=1e-4)


def test_area_of_a_band_from_the_equator_to_one_degree_north():
    # Exact area of the band from 0 to 1 degree north, on the ellipsoid, all the way round.
    band = 2 * math.pi * g.R_AUTHALIC_M ** 2 * math.sin(math.radians(float(g.authalic_lat(np.float64(1.0)))))
    lons = [0.0, 10.0, 10.0, 0.0, 0.0]
    lats = [0.0, 0.0, 1.0, 1.0, 0.0]
    assert g.ring_area_m2(lons, lats) == pytest.approx(band / 36, rel=1e-4)


def test_densify_keeps_the_ends_and_uses_numpy_index_type():
    lon, lat = g.densify([0.0, 1.0], [0.0, 0.0], 0.25)
    assert lon.tolist() == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert lat.tolist() == [0.0] * 5


# The local projection ----------------------------------------------------------------

def test_local_projection_is_close_to_exact_distances_nearby():
    proj = g.LocalProjection(*LONDON)
    lat, lon = 51.6, 0.0
    x, y = proj.forward(lat, lon)
    assert math.hypot(x, y) == pytest.approx(g.distance_m(*LONDON, lat, lon), rel=2e-3)
    back = proj.inverse(x, y)
    assert float(back[0]) == pytest.approx(lat) and float(back[1]) == pytest.approx(lon)


def test_local_projection_across_the_180_degree_line():
    proj = g.LocalProjection(-17.0, 179.95)
    x, _y = proj.forward(-17.0, -179.95)
    assert x == pytest.approx(g.distance_m(-17.0, 179.95, -17.0, -179.95), rel=1e-3)
    assert x > 0  # east, the short way round


def test_local_projection_on_arrays():
    proj = g.LocalProjection(0.0, 0.0)
    x, y = proj.forward(np.array([0.0, 0.1]), np.array([0.1, 0.0]))
    assert x.shape == (2,) and x[0] > 10_000 and y[1] > 10_000
