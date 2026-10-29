import datetime as dt
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from experiment_timeline.cli import main
from experiment_timeline.core import gantt, load_protocol, parse_duration, schedule, stagger, to_ics

EX = os.path.join(os.path.dirname(__file__), "..", "examples", "western_blot.json")
START = dt.datetime(2026, 3, 2, 9, 0)     # a Monday


class DurationTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_duration("1h30m"), 5400)
        self.assertEqual(parse_duration("45 min"), 2700)
        self.assertEqual(parse_duration("2 days"), 172800)
        self.assertEqual(parse_duration("1 h and 15 min"), 4500)
        self.assertEqual(parse_duration("overnight"), 57600)
        for bad in ("soon", "5 parsecs", ""):
            with self.assertRaises(ValueError):
                parse_duration(bad)


class ScheduleTests(unittest.TestCase):
    def test_sequential_with_gap_and_overnight(self):
        rows = schedule(load_protocol(EX)["steps"], START)
        by = {r["name"]: r for r in rows}
        self.assertEqual(by["Transfer"]["start"], dt.datetime(2026, 3, 2, 10, 30))
        self.assertEqual(by["Block"]["start"], dt.datetime(2026, 3, 2, 11, 40))
        self.assertEqual(by["Wash 3x"]["start"], dt.datetime(2026, 3, 3, 4, 40))
        self.assertIn("outside", by["Wash 3x"]["warnings"][0])
        self.assertEqual(by["Primary antibody"]["warnings"], [])

    def test_explicit_dependencies(self):
        steps = [{"name": "A", "duration": "1h"}, {"name": "B", "duration": "2h", "after": []},
                 {"name": "C", "duration": "30m", "after": ["A", "B"]}]
        rows = {r["name"]: r for r in schedule(steps, START)}
        self.assertEqual(rows["B"]["start"], START)
        self.assertEqual(rows["C"]["start"], START + dt.timedelta(hours=2))
        with self.assertRaises(ValueError):
            schedule([{"name": "X", "duration": "1h", "after": ["Y"]}], START)

    def test_weekend_and_stagger_clashes(self):
        sat = dt.datetime(2026, 3, 7, 10, 0)
        self.assertIn("falls on a weekend", schedule([{"name": "x", "duration": "1h"}], sat)[0]["warnings"])
        steps = [{"name": "prep", "duration": "20 min"}, {"name": "incubate", "duration": "1h", "hands_on": False}]
        runs, clashes = stagger(steps, START, ["s1", "s2"], "10 min")
        self.assertEqual(len(clashes), 1)
        runs, clashes = stagger(steps, START, ["s1", "s2"], "20 min")
        self.assertEqual(clashes, [])

    def test_outputs(self):
        rows = schedule(load_protocol(EX)["steps"], START)
        self.assertIn("# hands-on", gantt(rows))
        ics = to_ics(rows, "WB", only_hands_on=True)
        self.assertEqual(ics.count("BEGIN:VEVENT"), 3)
        self.assertIn("TRIGGER:-PT10M", ics)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            ics = os.path.join(d, "wb.ics")
            with redirect_stdout(io.StringIO()) as buf:
                code = main([EX, "2026-03-02 09:00", "--ics", ics])
            self.assertEqual(code, 1)          # the wash step lands at night
            self.assertIn("finishes Tue 2026-03-03", buf.getvalue())
            self.assertTrue(os.path.exists(ics))


if __name__ == "__main__":
    unittest.main()
