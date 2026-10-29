"""Command-line interface for experiment-timeline."""
import argparse
import datetime as dt

from .core import gantt, load_protocol, schedule, stagger, to_ics


def main(argv=None):
    ap = argparse.ArgumentParser(prog="experiment-timeline", description="Plan an experiment timeline.")
    ap.add_argument("protocol", help="JSON protocol with steps")
    ap.add_argument("start", help="start time, 'YYYY-MM-DD HH:MM'")
    ap.add_argument("--samples", help="comma-separated samples to stagger")
    ap.add_argument("--interval", default="15 min", help="offset between staggered samples")
    ap.add_argument("--work-hours", default="8-18")
    ap.add_argument("--ics", help="write calendar file")
    ap.add_argument("--hands-on-only", action="store_true", help="calendar: only hands-on steps")
    args = ap.parse_args(argv)
    proto = load_protocol(args.protocol)
    start = dt.datetime.strptime(args.start, "%Y-%m-%d %H:%M")
    ws, we = (int(x) for x in args.work_hours.split("-"))
    if args.samples:
        runs, clashes = stagger(proto["steps"], start, [s.strip() for s in args.samples.split(",")], args.interval,
                                work_start=ws, work_end=we)
        rows = []
        for smp, rs in runs.items():
            print("== %s" % smp)
            print(gantt(rs))
            rows += [dict(r, name="%s %s" % (smp, r["name"])) for r in rs]
        for a, sa, b, sb, t in clashes:
            print("CLASH at %s: %s/%s overlaps %s/%s" % (t.strftime("%H:%M"), a, sa, b, sb))
    else:
        rows = schedule(proto["steps"], start, ws, we)
        clashes = []
        print(gantt(rows))
    print("finishes %s" % max(r["end"] for r in rows).strftime("%a %Y-%m-%d %H:%M"))
    if args.ics:
        with open(args.ics, "w", encoding="utf-8", newline="") as fh:
            fh.write(to_ics(rows, proto.get("name", "Experiment"), args.hands_on_only))
    return 1 if clashes or any(r["warnings"] for r in rows) else 0
