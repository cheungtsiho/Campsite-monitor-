import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from campsite_monitor.matcher import StayRule, find_openings
from campsite_monitor.monitor import Monitor
from campsite_monitor.providers import RecreationGov, ReserveCalifornia, _month_starts


def recgov_month(month: str, sites: dict[str, dict[str, str]]) -> dict:
    """Build a recreation.gov month payload: {site_name: {day: status}}."""
    return {
        "campsites": {
            str(100 + i): {
                "campsite_id": str(100 + i),
                "site": name,
                "loop": "A",
                "campsite_type": "STANDARD NONELECTRIC",
                "availabilities": {f"{month}-{d}T00:00:00Z": s for d, s in days.items()},
            }
            for i, (name, days) in enumerate(sites.items())
        }
    }


class FakeFetch:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        for needle, payload in self.responses.items():
            if needle in url:
                return payload
        raise AssertionError(f"unexpected url {url}")


class MonthTests(unittest.TestCase):
    def test_month_starts_spans_year(self):
        self.assertEqual(
            _month_starts(date(2026, 11, 20), date(2027, 1, 2)),
            [date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1)],
        )


class RecreationGovTests(unittest.TestCase):
    def test_merges_months_and_filters_status(self):
        fetch = FakeFetch(
            {
                "start_date=2026-11-01": recgov_month(
                    "2026-11", {"001": {"27": "Available", "28": "Available", "29": "Reserved"}}
                ),
                "start_date=2026-12-01": recgov_month("2026-12", {"001": {"01": "Available"}}),
            }
        )
        sites = RecreationGov(fetch, pause=0).availability("232491", date(2026, 11, 27), date(2026, 12, 2))
        self.assertEqual(len(sites), 1)
        self.assertEqual(
            sites[0].free_nights, {date(2026, 11, 27), date(2026, 11, 28), date(2026, 12, 1)}
        )
        self.assertIn("/232491/month", fetch.calls[0][0])
        self.assertEqual(sites[0].site.booking_url, "https://www.recreation.gov/camping/campsites/100")


class ReserveCaliforniaTests(unittest.TestCase):
    def setUp(self):
        self.fetch = FakeFetch(
            {
                "/fd/places": [
                    {"PlaceId": 1, "Name": "Mt. Diablo SP"},
                    {"PlaceId": 2, "Name": "Butano SP"},
                ],
                "/fd/facilities": [
                    {"FacilityId": 10, "PlaceId": 1, "Name": "Juniper Campground"},
                    {"FacilityId": 11, "PlaceId": 1, "Name": "Live Oak Campground"},
                    {"FacilityId": 12, "PlaceId": 1, "Name": "Wildcat Group Camp"},
                    {"FacilityId": 20, "PlaceId": 2, "Name": "Butano Campground"},
                ],
                "/search/grid": {
                    "Facility": {
                        "Name": "Juniper Campground",
                        "Units": {
                            "500": {
                                "UnitId": 500,
                                "ShortName": "J5",
                                "Name": "Campsite #5",
                                "Slices": {
                                    "2026-12-04T00:00:00": {"Date": "2026-12-04", "IsFree": True},
                                    "2026-12-05T00:00:00": {"Date": "2026-12-05", "IsFree": True},
                                    "2026-12-06T00:00:00": {"Date": "2026-12-06", "IsFree": False},
                                },
                            },
                            "501": {
                                "UnitId": 501,
                                "ShortName": "J6",
                                "AllowWebBooking": False,
                                "Slices": {"x": {"Date": "2026-12-04", "IsFree": True}},
                            },
                        },
                    }
                },
            }
        )
        self.rca = ReserveCalifornia(self.fetch, pause=0)

    def test_search_normalizes_names(self):
        res = self.rca.search("mount diablo", "juniper")
        self.assertEqual([m["facility_id"] for m in res], [10])
        self.assertEqual(len(self.rca.search(["mount diablo"])), 3)

    def test_availability(self):
        sites = self.rca.availability(10, date(2026, 12, 4), date(2026, 12, 7), place_id=1)
        self.assertEqual(len(sites), 1)  # non-web-bookable unit skipped
        self.assertEqual(sites[0].site.name, "J5")
        self.assertEqual(sites[0].free_nights, {date(2026, 12, 4), date(2026, 12, 5)})
        self.assertEqual(sites[0].site.booking_url, "https://www.reservecalifornia.com/park/1/10")
        body = [c for c in self.fetch.calls if "/search/grid" in c[0]][0][1]["body"]
        self.assertEqual(body["FacilityId"], "10")
        self.assertEqual(body["EndDate"], "12-07-2026")


class MatcherTests(unittest.TestCase):
    def test_weekend_two_nights(self):
        fetch = FakeFetch(
            {
                "start_date=2026-12-01": recgov_month(
                    "2026-12",
                    {
                        "001": {"04": "Available", "05": "Available"},  # Fri+Sat
                        "002": {"04": "Available", "05": "Reserved"},
                        "003": {"10": "Available", "11": "Available"},  # Thu+Fri
                    },
                )
            }
        )
        sites = RecreationGov(fetch, pause=0).availability("1", date(2026, 12, 1), date(2026, 12, 31))
        rule = StayRule.from_config(
            {"start": "2026-12-01", "end": "2026-12-31", "nights": 2, "check_in_days": ["Friday"]}
        )
        found = find_openings("X", sites, rule, today=date(2026, 11, 1))
        self.assertEqual([(o.site.name, o.check_in) for o in found], [("001", date(2026, 12, 4))])

    def test_site_filters(self):
        rule = StayRule.from_config(
            {"start": "2026-12-01", "end": "2026-12-03", "include_sites": ["0*"], "exclude_sites": ["002"]}
        )
        fetch = FakeFetch(
            {"2026-12": recgov_month("2026-12", {n: {"01": "Available"} for n in ("001", "002", "A1")})}
        )
        sites = RecreationGov(fetch, pause=0).availability("1", date(2026, 12, 1), date(2026, 12, 3))
        found = find_openings("X", sites, rule, today=date(2026, 11, 1))
        self.assertEqual([o.site.name for o in found], ["001"])

    def test_past_dates_skipped(self):
        rule = StayRule.from_config({"start": "2026-12-01", "end": "2026-12-05"})
        self.assertEqual(rule.check_ins(today=date(2026, 12, 3)), [date(2026, 12, 3), date(2026, 12, 4)])


class MonitorStateTests(unittest.TestCase):
    def test_notifies_only_new_and_renotifies_after_rebook(self):
        payload = {"value": recgov_month("2026-12", {"001": {"04": "Available"}})}
        rec = RecreationGov(lambda url, **kw: payload["value"], pause=0)
        cfg = {
            "search": [
                {"campground": "kirby-cove", "start": "2026-12-04", "end": "2026-12-05", "check_in_days": []}
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            m = Monitor(cfg, state_path=state, rec=rec)
            m.notifier.send = lambda openings: []
            today = date(2026, 11, 1)
            self.assertEqual(len(m.check_once(today=today)), 1)
            self.assertEqual(len(m.check_once(today=today)), 0)  # already notified
            payload["value"] = recgov_month("2026-12", {"001": {"04": "Reserved"}})
            self.assertEqual(len(m.check_once(today=today)), 0)
            self.assertEqual(json.loads(state.read_text())["notified"], [])
            payload["value"] = recgov_month("2026-12", {"001": {"04": "Available"}})
            self.assertEqual(len(m.check_once(today=today)), 1)  # cancellation -> notify again

    def test_rc_group_sites_excluded_by_default(self):
        rca = ReserveCaliforniaTests()
        rca.setUp()
        m = Monitor(
            {"search": [{"campground": "mount-diablo", "start": "2026-12-01", "end": "2026-12-03"}]},
            state_path="/dev/null",
            rca=rca.rca,
        )
        labels = [t.label for t in m.targets(m.searches[0])]
        self.assertEqual(labels, ["Mt. Diablo SP - Juniper Campground", "Mt. Diablo SP - Live Oak Campground"])


if __name__ == "__main__":
    unittest.main()
