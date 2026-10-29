# experiment-timeline

**Plan multi-step protocols with incubations (western blots, cell culture, cloning): see when
each step happens, get warnings when hands-on steps fall at night or on weekends, stagger samples
without clashes, and export reminders to your calendar.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

"If I start at 9, when do I have to come back?" Long protocols with overnight incubations and
several samples started minutes apart are planned on scraps of paper, and the plan fails when a wash
step lands at 4 a.m. or two samples need attention at the same moment.

## Features

- Protocol JSON: steps with durations (`1h30m`, `45 min`, `2 days`, `overnight`), optional gaps,
  explicit `after` dependencies (parallel branches) and a `hands_on` flag
- Schedule from a start time; warnings for hands-on steps outside working hours or on weekends
- Stagger the protocol across samples and detect overlapping hands-on steps
- Text Gantt chart; ICS calendar export with a reminder before each hands-on step

## Usage

```bash
pip install .
experiment-timeline examples/western_blot.json "2026-03-02 09:00"
experiment-timeline examples/western_blot.json "2026-03-02 13:00" --work-hours 8-20 --ics wb.ics --hands-on-only
experiment-timeline timecourse.json "2026-03-02 08:30" --samples A,B,C,D --interval "20 min"
```

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
