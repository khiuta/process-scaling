import random
import time
from collections import deque

# ---------------------------------------------------------------------------
# Shared tie-break policy (per the assignment):
#   1) prefer the process already holding the CPU, to avoid a context switch
#   2) else prefer the one with the shortest remaining time (SRT)
#   3) else choose randomly among whatever is still tied
#
# `candidates` is a list of task-info dicts (the {'task':..., 'wait_time':...,
# 'executed_time':...} dicts used throughout this module). `metric_func(c)`
# returns the scheduling key for a candidate (lower = more eligible to run
# next -- e.g. duration for SJF, -priority for priority scheduling).
# `running` is the task-info dict currently holding the CPU, or None if the
# CPU is free; passing it lets rule (1) apply. Candidates that never started
# have remaining time == duration, so rule (2) only has teeth for algorithms
# where waiting tasks can have partial execution (the preemptive ones).
# ---------------------------------------------------------------------------

def _remaining(task_info):
    return task_info['task']['duration'] - task_info['executed_time']


def _select_next(candidates, metric_func, running=None):
    best_val = min(metric_func(c) for c in candidates)
    tied = [c for c in candidates if metric_func(c) == best_val]
    if len(tied) == 1:
        return tied[0]

    if running is not None:
        for c in tied:
            if c is running:
                return c

    min_remaining = min(_remaining(c) for c in tied)
    tied = [c for c in tied if _remaining(c) == min_remaining]
    if len(tied) == 1:
        return tied[0]

    return random.choice(tied)


def _remove_by_identity(items, target):
    items[:] = [x for x in items if x is not target]


def _sorted_arrivals(arrivals):
    # sorting if various processes arrive at the same time
    if len(arrivals) <= 1:
        return arrivals
    return sorted(arrivals, key=lambda p: (p['duration'], random.random()))


def _report(name, finished_procs, context_switches):
    n = len(finished_procs)
    mean_wait = sum(f['wait_time'] for f in finished_procs) / n
    mean_turnaround = sum(f['wait_time'] + f['task']['duration'] for f in finished_procs) / n
    for proc in finished_procs:
        print(proc)
        print("\n")
    print(f"[{name}] Mean wait time: {mean_wait}")
    print(f"[{name}] Mean turnaround time: {mean_turnaround}")
    print(f"[{name}] Context switches: {context_switches}\n")


def FCFS(processes, on_tick=None):
    queue = deque()
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        # sorting arrivals before adding to the queue
        # helps with various arrivals at the same time
        arrivals = _sorted_arrivals([p for p in processes if p['start_time'] == i])
        for proc in arrivals:
            queue.append({'task': proc, 'wait_time': 0, 'executed_time': 0})

        # set a process if none is running
        if curr_proc is None:
            curr_proc = queue.popleft()
            print(f"Starting task {curr_proc['task']['task']}...")

        for t in queue:
            t['wait_time'] += 1

        # gets the id of the running task
        ran_id = curr_proc['task']['task']
        # printing
        curr_proc['executed_time'] += 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        # detects context switch by comparing who's running now and who was running before
        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        # checks if the process finished
        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None

        # just calls the visuals helper function
        if on_tick:
            on_tick(i, curr_proc, list(queue), finished_procs)

        # delay for visualization
        time.sleep(1)

    _report("FCFS", finished_procs, context_switches)


def RR(processes, quantum, on_tick=None):
    queue = deque()
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        arrivals = _sorted_arrivals([p for p in processes if p['start_time'] == i])
        for proc in arrivals:
            queue.append({'task': proc, 'wait_time': 0, 'executed_time': 0, 'quantum': quantum})

        if curr_proc is None:
            curr_proc = queue.popleft()
            print(f"Starting task {curr_proc['task']['task']}...")

        for t in queue:
            t['wait_time'] += 1

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        curr_proc['quantum'] -= 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        # checks if the task or the quantum ended to switch context
        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None
        elif curr_proc['quantum'] == 0:
            curr_proc['quantum'] = quantum
            queue.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(queue), finished_procs)

        time.sleep(1)

    _report("Round Robin", finished_procs, context_switches)


def SJF(processes, on_tick=None):
    waiting = []
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        for proc in processes:
            if proc['start_time'] == i:
                waiting.append({'task': proc, 'wait_time': 0, 'executed_time': 0})

        # select next
        if curr_proc is None:
            curr_proc = _select_next(waiting, metric_func=lambda c: c['task']['duration'])
            # remove the selected proc from the waiting queue
            _remove_by_identity(waiting, curr_proc)
            print(f"Starting task {curr_proc['task']['task']}...")

        for t in waiting:
            t['wait_time'] += 1

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(waiting), finished_procs)

        time.sleep(1)

    _report("SJF", finished_procs, context_switches)


def SRTF(processes, on_tick=None):
    waiting = []
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        for proc in processes:
            if proc['start_time'] == i:
                waiting.append({'task': proc, 'wait_time': 0, 'executed_time': 0})

        # pool = whoever is waiting plus whoever is currently running (if anyone) 
        # the shared tie-break helper keeps curr_proc running on any tie
        pool = list(waiting)
        if curr_proc is not None:
            pool.append(curr_proc)
        best = _select_next(pool, metric_func=_remaining, running=curr_proc)

        # context switch
        if best is not curr_proc:
            if curr_proc is not None:
                waiting.append(curr_proc)
            _remove_by_identity(waiting, best)
            curr_proc = best
            print(f"Starting task {curr_proc['task']['task']}...")

        for t in waiting:
            t['wait_time'] += 1

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(waiting), finished_procs)

        time.sleep(1)

    _report("SRTF", finished_procs, context_switches)


def prioc(processes, on_tick=None):
    waiting = []
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        for proc in processes:
            if proc['start_time'] == i:
                waiting.append({'task': proc, 'wait_time': 0, 'executed_time': 0})

        # selects the next by priority
        if curr_proc is None:
            # priority is passed as -priority because _select_next uses min()
            curr_proc = _select_next(waiting, metric_func=lambda c: -c['task']['priority'])
            _remove_by_identity(waiting, curr_proc)
            print(f"Starting task {curr_proc['task']['task']}...")

        for t in waiting:
            t['wait_time'] += 1

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(waiting), finished_procs)

        time.sleep(1)

    _report("Priority (cooperative)", finished_procs, context_switches)


def priop(processes, on_tick=None):
    waiting = []
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        for proc in processes:
            if proc['start_time'] == i:
                waiting.append({'task': proc, 'wait_time': 0, 'executed_time': 0})

        # selects the next based on priority with preemption
        pool = list(waiting)
        if curr_proc is not None:
            pool.append(curr_proc)
        best = _select_next(pool, metric_func=lambda c: -c['task']['priority'], running=curr_proc)

        if best is not curr_proc:
            if curr_proc is not None:
                waiting.append(curr_proc)
            _remove_by_identity(waiting, best)
            curr_proc = best
            print(f"Starting task {curr_proc['task']['task']}...")

        for t in waiting:
            t['wait_time'] += 1

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(waiting), finished_procs)

        time.sleep(1)

    _report("Priority (preemptive)", finished_procs, context_switches)


def priod(processes, aging, on_tick=None):
    waiting = []
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None

    for i in range(total_duration):
        for proc in processes:
            if proc['start_time'] == i:
                waiting.append({'task': proc, 'wait_time': 0, 'executed_time': 0,
                                 'dynamic_priority': proc['priority']})

        # selects next task EVERY second
        # this allows preemption without having new arrivals
        pool = list(waiting)
        if curr_proc is not None:
            pool.append(curr_proc)
        best = _select_next(pool, metric_func=lambda c: -c['dynamic_priority'], running=curr_proc)

        if best is not curr_proc:
            if curr_proc is not None:
                waiting.append(curr_proc)
            _remove_by_identity(waiting, best)
            curr_proc = best
            print(f"Starting task {curr_proc['task']['task']}...")

        # waiting tasks age every second (by every second is the below RR implementation)
        for t in waiting:
            t['wait_time'] += 1
            t['dynamic_priority'] += aging

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(waiting), finished_procs)

        time.sleep(1)

    _report("Priority w/ aging", finished_procs, context_switches)


def RR_prio_aging(processes, quantum, aging, on_tick=None):
    waiting = []
    total_duration = sum(p['duration'] for p in processes)
    curr_proc = None
    finished_procs = []
    context_switches = 0
    prev_running_id = None
    just_preempted = None  # task-info dict preempted last tick by quantum expiry, or None

    for i in range(total_duration):
        for proc in processes:
            if proc['start_time'] == i:
                waiting.append({'task': proc, 'wait_time': 0, 'executed_time': 0,
                                 'dynamic_priority': proc['priority'], 'quantum_left': quantum})

        if curr_proc is None:
            # running reference is the task that was just preempted and didn't finish yet
            running_ref = just_preempted if (just_preempted is not None and
                                              any(w is just_preempted for w in waiting)) else None
            curr_proc = _select_next(waiting, metric_func=lambda c: -c['dynamic_priority'],
                                      running=running_ref)
            _remove_by_identity(waiting, curr_proc)
            curr_proc['quantum_left'] = quantum
            print(f"Starting task {curr_proc['task']['task']}...")

            # increase aging in start of new quantum
            for t in waiting:
                t['dynamic_priority'] += aging

            just_preempted = None

        for t in waiting:
            t['wait_time'] += 1

        ran_id = curr_proc['task']['task']
        curr_proc['executed_time'] += 1
        curr_proc['quantum_left'] -= 1
        print(f"Task {curr_proc['task']['task']}")
        print('#' * curr_proc['executed_time'], end='')
        print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
        print('\n')

        if prev_running_id is not None and ran_id != prev_running_id:
            context_switches += 1
        prev_running_id = ran_id

        if curr_proc['executed_time'] == curr_proc['task']['duration']:
            print(f"Finished process {curr_proc['task']['task']}")
            curr_proc['finish_time'] = i + 1
            finished_procs.append(curr_proc)
            curr_proc = None
        elif curr_proc['quantum_left'] == 0:
            # preempted by quantum expiry
            just_preempted = curr_proc
            waiting.append(curr_proc)
            curr_proc = None

        if on_tick:
            on_tick(i, curr_proc, list(waiting), finished_procs)

        time.sleep(1)

    _report("RR + priority + aging", finished_procs, context_switches)