"""Steps with durations and dependencies -> start/end times, working-hour warnings, staggered samples, ICS."""
import datetime as dt
import json
import re

_DUR = re.compile(r"(\d+(?:\.\d+)?)\s*(days?|d|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)(?![a-z])", re.I)
NAMED = {"overnight": 16 * 3600, "o/n": 16 * 3600}


def parse_duration(text):
    """'1h30m', '45 min', '2 days', 'overnight' -> seconds."""
    t = str(text).strip().lower()
    if t in NAMED:
        return NAMED[t]
    total, pos = 0.0, 0
    for m in _DUR.finditer(t):
        if t[pos:m.start()].strip(" ,and"):
            raise ValueError("bad duration %r" % text)
        unit = m.group(2)[0]
        total += float(m.group(1)) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
        pos = m.end()
    if pos == 0 or t[pos:].strip():
        raise ValueError("bad duration %r" % text)
    return int(total)


def load_protocol(path):
    """JSON: {"name": ..., "steps": [{"name", "duration", "after": [names], "hands_on": bool, "gap": "10 min"}]}."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def schedule(steps, start, work_start=8, work_end=18):
    """Compute start/end for each step. By default a step follows the previous one; 'after' lists explicit
    predecessors (the step starts when all have finished, plus optional 'gap'). Hands-on steps outside
    working hours are flagged."""
    by_name, out = {}, []
    prev = None
    for s in steps:
        dur = dt.timedelta(seconds=parse_duration(s["duration"]))
        after = s.get("after", [prev] if prev else [])
        for a in after:
            if a not in by_name:
                raise ValueError("step %r depends on unknown or later step %r" % (s["name"], a))
        t0 = max([by_name[a]["end"] for a in after], default=start)
        t0 += dt.timedelta(seconds=parse_duration(s["gap"])) if s.get("gap") else dt.timedelta(0)
        row = {"name": s["name"], "start": t0, "end": t0 + dur, "hands_on": s.get("hands_on", True), "warnings": []}
        if row["hands_on"]:
            if t0.hour < work_start or (t0 + dur).hour + (t0 + dur).minute / 60 > work_end or (t0 + dur).date() != t0.date():
                row["warnings"].append("hands-on step outside %02d:00-%02d:00" % (work_start, work_end))
            if t0.weekday() >= 5:
                row["warnings"].append("falls on a weekend")
        by_name[s["name"]] = row
        out.append(row)
        prev = s["name"]
    return out


def stagger(steps, start, samples, interval, **kw):
    """Schedule the same protocol for several samples started `interval` apart; reports hands-on overlaps."""
    gap = dt.timedelta(seconds=parse_duration(interval))
    runs = {smp: schedule(steps, start + i * gap, **kw) for i, smp in enumerate(samples)}
    clashes = []
    flat = [(smp, r) for smp, rows in runs.items() for r in rows if r["hands_on"]]
    for i, (sa, ra) in enumerate(flat):
        for sb, rb in flat[i + 1:]:
            if sa != sb and ra["start"] < rb["end"] and rb["start"] < ra["end"]:
                clashes.append((sa, ra["name"], sb, rb["name"], max(ra["start"], rb["start"])))
    return runs, clashes


def gantt(rows, width=60):
    t0 = min(r["start"] for r in rows)
    t1 = max(r["end"] for r in rows)
    span = (t1 - t0).total_seconds() or 1
    w = max(len(r["name"]) for r in rows)
    lines = []
    for r in rows:
        a = int((r["start"] - t0).total_seconds() / span * width)
        b = max(a + 1, int((r["end"] - t0).total_seconds() / span * width))
        bar = " " * a + ("#" if r["hands_on"] else "=") * (b - a)
        lines.append("%s |%s| %s-%s%s" % (r["name"].ljust(w), bar.ljust(width), r["start"].strftime("%a %H:%M"),
                                         r["end"].strftime("%H:%M"), "  !" + "; ".join(r["warnings"]) if r["warnings"] else ""))
    lines.append("%s  # hands-on   = waiting/incubation" % (" " * w))
    return "\n".join(lines)


def to_ics(rows, title="Experiment", only_hands_on=False, alarm_minutes=10):
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//research-toolkit//experiment-timeline//EN"]
    for i, r in enumerate(rows):
        if only_hands_on and not r["hands_on"]:
            continue
        out += ["BEGIN:VEVENT", "UID:%s-%d-%s@experiment-timeline" % (stamp, i, re.sub(r"\W", "", r["name"])),
                "DTSTAMP:%s" % stamp, "DTSTART:%s" % r["start"].strftime("%Y%m%dT%H%M%S"),
                "DTEND:%s" % r["end"].strftime("%Y%m%dT%H%M%S"),
                "SUMMARY:%s: %s" % (title.replace(",", "\\,"), r["name"].replace(",", "\\,"))]
        if alarm_minutes and r["hands_on"]:
            out += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:%s" % r["name"].replace(",", "\\,"),
                    "TRIGGER:-PT%dM" % alarm_minutes, "END:VALARM"]
        out.append("END:VEVENT")
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"
