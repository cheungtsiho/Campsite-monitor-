"""Load config, poll every search, diff against saved state, notify."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .catalog import CATALOG
from .matcher import StayRule, find_openings
from .models import Opening
from .notify import Notifier
from .providers import RecreationGov, ReserveCalifornia

RULE_KEYS = {"start", "end", "nights", "check_in_days", "include_sites", "exclude_sites", "site_types"}


@dataclass
class Target:
    """One concrete campground/facility to query."""

    label: str
    provider: str
    campground_id: str
    place_id: str | None = None


def load_config(path: str | Path) -> dict:
    with open(path, "rb") as fh:
        cfg = tomllib.load(fh)
    if not cfg.get("search"):
        raise ValueError(f"{path}: add at least one [[search]] table")
    return cfg


def _merged_search(raw: dict, defaults: dict) -> dict:
    merged = {**defaults, **raw}
    key = merged.get("campground")
    if key:
        if key not in CATALOG:
            raise ValueError(f"unknown campground {key!r}; run `list` to see the catalog")
        merged = {**CATALOG[key], **merged}
    if "provider" not in merged:
        raise ValueError(f"search {raw} needs `campground` (catalog key) or `provider`")
    return merged


class Monitor:
    def __init__(self, config: dict, state_path: str | Path | None = None, rec=None, rca=None):
        self.config = config
        self.state_path = Path(state_path or config.get("state_file", ".campsite_state.json"))
        self.rec = rec or RecreationGov()
        self.rca = rca or ReserveCalifornia()
        self.notifier = Notifier(config.get("notify"))
        defaults = config.get("defaults", {})
        self.searches = [_merged_search(s, defaults) for s in config["search"]]

    # -- target resolution ----------------------------------------------------
    def targets(self, search: dict) -> list[Target]:
        provider = search["provider"]
        if provider == "recreation.gov":
            return [
                Target(
                    search.get("name", search["campground_id"]),
                    provider,
                    str(search["campground_id"]),
                )
            ]
        if provider == "reservecalifornia":
            if search.get("facility_id"):
                return [
                    Target(
                        search.get("name", f"facility {search['facility_id']}"),
                        provider,
                        str(search["facility_id"]),
                        str(search.get("place_id") or "") or None,
                    )
                ]
            matches = self.rca.search(search["park"], search.get("facility"))
            if not search.get("include_group", False):
                matches = [m for m in matches if "group" not in m["facility"].lower()]
            if not matches:
                raise ValueError(f"no ReserveCalifornia facility matches park={search['park']!r}")
            return [
                Target(
                    f"{m['park']} - {m['facility']}",
                    provider,
                    str(m["facility_id"]),
                    str(m["place_id"]),
                )
                for m in matches
            ]
        raise ValueError(f"unknown provider {provider!r}")

    # -- polling --------------------------------------------------------------
    def scan(self, today: date | None = None) -> tuple[list[Opening], list[str]]:
        """Query every search once. Returns (all current openings, errors)."""
        openings: list[Opening] = []
        errors: list[str] = []
        for search in self.searches:
            rule = StayRule.from_config({k: v for k, v in search.items() if k in RULE_KEYS})
            try:
                targets = self.targets(search)
            except Exception as exc:
                errors.append(f"{search.get('name', search)}: {exc}")
                continue
            for t in targets:
                try:
                    if t.provider == "recreation.gov":
                        sites = self.rec.availability(t.campground_id, rule.start, rule.end)
                    else:
                        sites = self.rca.availability(
                            t.campground_id, rule.start, rule.end, place_id=t.place_id
                        )
                except Exception as exc:
                    errors.append(f"{t.label}: {exc}")
                    continue
                openings.extend(find_openings(t.label, sites, rule, today))
        return openings, errors

    def load_state(self) -> set[str]:
        try:
            return set(json.loads(self.state_path.read_text()).get("notified", []))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def save_state(self, keys: set[str]) -> None:
        self.state_path.write_text(json.dumps({"notified": sorted(keys)}, indent=1))

    def check_once(self, notify: bool = True, today: date | None = None) -> list[Opening]:
        """Scan, notify about openings not seen last time, persist state.

        An opening that disappears (someone booked it) is dropped from state, so
        if it is cancelled again later you will be notified again.
        """
        openings, errors = self.scan(today)
        for err in errors:
            print(f"[warn] {err}", flush=True)
        seen = self.load_state()
        current = {o.key for o in openings}
        new = [o for o in openings if o.key not in seen]
        if notify and new:
            for err in self.notifier.send(new):
                print(f"[warn] notify {err}", flush=True)
        self.save_state(current)
        return new
