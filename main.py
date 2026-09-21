import copy
import csv

import scaling
import visuals

QUANTUM = 2
AGING = 1

# name -> (function, kwargs, show_priority, show_dynamic)
ALGORITHMS = {
    "1": ("FCFS", scaling.FCFS, {}, False, False),
    "2": ("Round Robin", scaling.RR, {"quantum": QUANTUM}, False, False),
    "3": ("SJF", scaling.SJF, {}, False, False),
    "4": ("SRTF", scaling.SRTF, {}, False, False),
    "5": ("Priority (cooperative)", scaling.prioc, {}, True, False),
    "6": ("Priority (preemptive)", scaling.priop, {}, True, False),
    "7": ("Priority w/ aging", scaling.priod, {"aging": AGING}, True, True),
}


def load_processes(path='processes.csv'):
    processes = []
    with open(path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            processes.append({
                'task': int(row[0]),
                'start_time': int(row[1]),
                'duration': int(row[2]),
                'priority': int(row[3])
            })
    return processes


def choose_algorithms():
    print("Choose up to 4 algorithms to run at the same time (comma separated), e.g. 1,3,5")
    for key, (name, *_rest) in ALGORITHMS.items():
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
        if any(k not in ALGORITHMS for k in keys):
            print("Unrecognized option, try again.")
            continue
        return keys


def main():
    processes = load_processes()
    keys = choose_algorithms()

    runs = []
    for key in keys:
        name, func, kwargs, show_priority, show_dynamic = ALGORITHMS[key]
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