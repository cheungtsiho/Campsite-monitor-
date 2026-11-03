"""Command line interface: ``python -m campsite_monitor <command>``."""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime

from .catalog import CATALOG
from .monitor import Monitor, load_config
from .providers import ReserveCalifornia


def cmd_list(_args) -> int:
    for key, c in CATALOG.items():
        print(f"{key:20} {c['name']}  [{c['provider']}, {c['drive']} from SF]")
        print(f"{'':20} {c['notes']}")
    return 0


def cmd_rc_search(args) -> int:
    matches = ReserveCalifornia().search(args.park, args.facility)
    if not matches:
        print("no matches")
        return 1
    for m in matches:
        print(f"place_id={m['place_id']:<6} facility_id={m['facility_id']:<6} {m['park']} - {m['facility']}")
    return 0


def cmd_check(args) -> int:
    monitor = Monitor(load_config(args.config), state_path=args.state)
    if args.all:
        openings, errors = monitor.scan()
        for err in errors:
            print(f"[warn] {err}")
        for o in openings:
            print(f"{o.describe()}\n    {o.site.booking_url}")
        print(f"{len(openings)} opening(s)")
        return 0
    new = monitor.check_once(notify=not args.dry_run)
    print(f"[{datetime.now():%H:%M:%S}] {len(new)} new opening(s)")
    return 0


def cmd_watch(args) -> int:
    monitor = Monitor(load_config(args.config), state_path=args.state)
    print(f"Watching {len(monitor.searches)} search(es) every ~{args.interval}s. Ctrl-C to stop.")
    while True:
        try:
            new = monitor.check_once()
            print(f"[{datetime.now():%H:%M:%S}] {len(new)} new opening(s)", flush=True)
        except Exception as exc:  # keep watching through transient failures
            print(f"[{datetime.now():%H:%M:%S}] error: {exc}", flush=True)
        # Jitter so we don't hit the sites on a rigid schedule.
        time.sleep(args.interval * random.uniform(0.8, 1.2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="campsite_monitor", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show the curated Bay Area campground catalog").set_defaults(func=cmd_list)

    s = sub.add_parser("rc-search", help="look up ReserveCalifornia park/facility ids")
    s.add_argument("park", help="part of the park name, e.g. 'mount diablo'")
    s.add_argument("--facility", help="part of the facility name, e.g. 'juniper'")
    s.set_defaults(func=cmd_rc_search)

    for name, fn, helptext in (
        ("check", cmd_check, "check once and notify about new openings"),
        ("watch", cmd_watch, "check repeatedly"),
    ):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("-c", "--config", default="config.toml")
        c.add_argument("--state", help="state file (default from config or .campsite_state.json)")
        if name == "check":
            c.add_argument("--all", action="store_true", help="print every current opening; no notify")
            c.add_argument("--dry-run", action="store_true", help="update state but don't notify")
        else:
            c.add_argument("-i", "--interval", type=int, default=300, help="seconds between checks")
        c.set_defaults(func=fn)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
