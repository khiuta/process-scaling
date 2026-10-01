import argparse
import copy
import csv
import sys

import scaling
import visuals

DEFAULT_QUANTUM = 2
DEFAULT_AGING = 1


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process scheduling simulator with a live visual dashboard."
    )
    parser.add_argument(
        '--config', type=str, default=None,
        help="path to a plain-text config file with 'quantum:<n>' and "
             "'aging:<n>' lines (whitespace around ':' is fine). Falls back "
             f"to quantum={DEFAULT_QUANTUM}, aging={DEFAULT_AGING} for "
             "whichever key is missing or if no file is given."
    )
    parser.add_argument(
        '--csv', type=str, default=None,
        help="path to a processes CSV with columns task,start_time,duration,"
             "priority. If omitted, processes are instead read from stdin, "
             "one per line, as '<creation_time> <duration> <priority>' "
             "(task id is just the 1-based line number, per the assignment)."
    )
    parser.add_argument(
        '--algorithms', type=str, default=None,
        help="comma-separated algorithm keys to run (1-4 of them), e.g. "
             "'1,3,5,7'. Required when processes come from stdin, since "
             "stdin can't also be used for an interactive prompt at that "
             "point. If omitted and stdin is a real terminal (e.g. you used "
             "--csv), you'll be prompted interactively instead."
    )
    return parser.parse_args()


def load_config(path):
    quantum, aging = DEFAULT_QUANTUM, DEFAULT_AGING
    if path is None:
        return quantum, aging

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ':' not in line:
                continue
            key, _, value = line.partition(':')
            key = key.strip().lower()
            value = value.strip()
            if key == 'quantum':
                quantum = int(value)
            elif key == 'aging':
                aging = int(value)
    return quantum, aging


def load_processes_csv(path):
    processes = []
    with open(path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if not row:
                continue
            processes.append({
                'task': int(row[0]),
                'start_time': int(row[1]),
                'duration': int(row[2]),
                'priority': int(row[3]),
            })
    return processes


def load_processes_stdin():
    processes = []
    for idx, raw_line in enumerate(sys.stdin, start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(
                f"stdin line {idx} ('{line}') needs 3 fields: creation_time "
                "duration priority"
            )
        start_time, duration, priority = (int(parts[0]), int(parts[1]), int(parts[2]))
        processes.append({
            'task': idx,
            'start_time': start_time,
            'duration': duration,
            'priority': priority,
        })
    return processes


def build_algorithms(quantum, aging):
    """name -> (function, kwargs, show_priority, show_dynamic)"""
    return {
        "1": ("FCFS", scaling.FCFS, {}, False, False),
        "2": ("Round Robin", scaling.RR, {"quantum": quantum}, False, False),
        "3": ("SJF", scaling.SJF, {}, False, False),
        "4": ("SRTF", scaling.SRTF, {}, False, False),
        "5": ("Priority (cooperative)", scaling.prioc, {}, True, False),
        "6": ("Priority (preemptive)", scaling.priop, {}, True, False),
        "7": ("Priority w/ aging", scaling.priod, {"aging": aging}, True, True),
        "8": ("RR + priority + aging (no preempt)", scaling.RR_prio_aging,
              {"quantum": quantum, "aging": aging}, True, True),
    }


def choose_algorithms(algorithms, preselected):
    if preselected:
        keys = [k.strip() for k in preselected.split(',') if k.strip()]
        if not keys or len(keys) > 4 or any(k not in algorithms for k in keys):
            valid = ", ".join(sorted(algorithms.keys()))
            raise SystemExit(
                f"--algorithms '{preselected}' is invalid: pick 1 to 4 keys "
                f"from {{{valid}}}, comma separated."
            )
        return keys

    if not sys.stdin.isatty():
        raise SystemExit(
            "No --algorithms given, and stdin isn't a terminal (it's being "
            "used for process input), so there's nothing to interactively "
            "prompt on. Pass --algorithms, e.g. --algorithms 1,3,5,7"
        )

    print("Choose up to 4 algorithms to run at the same time (comma separated), e.g. 1,3,5")
    for key, (name, *_rest) in algorithms.items():
        print(f"  {key}. {name}")

    while True:
        raw = input("> ").strip()
        keys = [k.strip() for k in raw.split(',') if k.strip()]
        if not keys:
            print("Pick at least one.")
            continue
        if len(keys) > 4:
            print("Pick at most 4.")
            continue
        if any(k not in algorithms for k in keys):
            print("Unrecognized option, try again.")
            continue
        return keys


def main():
    args = parse_args()
    quantum, aging = load_config(args.config)

    if args.csv:
        processes = load_processes_csv(args.csv)
    else:
        processes = load_processes_stdin()

    algorithms = build_algorithms(quantum, aging)
    keys = choose_algorithms(algorithms, args.algorithms)

    runs = []
    for key in keys:
        name, func, kwargs, show_priority, show_dynamic = algorithms[key]
        runs.append({
            'name': name,
            'func': func,
            'kwargs': kwargs,
            'processes': copy.deepcopy(processes),
            'show_priority': show_priority,
            'show_dynamic': show_dynamic,
        })

    dashboard = visuals.LiveDashboard(runs)
    dashboard.start()


if __name__ == '__main__':
    main()