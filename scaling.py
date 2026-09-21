import time
import heapq
from collections import deque

# NOTE: queues used to be module-level globals shared across calls. That
# meant prioc/priop/priod all shared the same `prioc_queue`, so running two
# of them at once (or the same one twice) would corrupt each other's state.
# Each queue is now local to its function so multiple algorithms can safely
# run concurrently (e.g. in separate threads).

# NOTE: every function below gained one new parameter, `on_tick=None`, and
# one call to it per second of simulated time. If you don't pass on_tick,
# behavior is 100% identical to before (prints + time.sleep(1) each tick).
# `on_tick(time_step, curr_proc, waiting_tasks, finished_procs)` hands off
# the raw state for that tick; visuals.py turns that into plots. Nothing in
# here knows or cares that visuals.py exists.

def FCFS(processes, on_tick=None):
  queue = deque()
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  for i in range(total_duration):
    # put process in the queue if it starts at the i-th time
    for proc in processes:
      if proc['start_time'] == i:
        queue.append({'task': proc, 'wait_time': 0, 'executed_time': 0})
      
    # sets a process to run if there is none
    if curr_proc == None:
      curr_proc = queue.popleft()
      print(f"Starting task {curr_proc['task']['task']}...")
    
    # every process still in the queue increases wait time
    for t in queue:
      t['wait_time'] += 1

    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, list(queue), finished_procs)

    # 1 second delay for visualization
    time.sleep(1)

  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")

def RR(processes, quantum, on_tick=None):
  queue = deque()
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  for i in range(total_duration):
    # put process in the queue if it starts at the i-th time
    for proc in processes:
      if proc['start_time'] == i:
        queue.append({'task': proc, 'wait_time': 0, 'executed_time': 0, 'quantum': quantum})

    # sets a process to run if there is none
    if curr_proc == None:
      curr_proc = queue.popleft()
      print(f"Starting task {curr_proc['task']['task']}...")

    # every process still in the queue increases wait time
    for t in queue: 
      t['wait_time'] += 1   

    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    curr_proc['quantum'] -= 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None
    
    # if the process quantum expired, it goes back to the queue
    if curr_proc != None and curr_proc['quantum'] == 0:
      curr_proc['quantum'] = quantum
      queue.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, list(queue), finished_procs)

    # 1 second delay for visualization
    time.sleep(1)

  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")

def SJF(processes, on_tick=None):
  SJF_queue = []
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  for i in range(total_duration):
    for proc in processes:
      if proc['start_time'] == i:
        # proc['task'] (the task id) is included purely as a heap tiebreaker
        # for equal durations, so ties never fall through to comparing dicts
        heapq.heappush(SJF_queue, (proc['duration'], proc['task'], {'task': proc, 'wait_time': 0, 'executed_time': 0}))

    # sets a process to run if there is none
    if curr_proc == None:
      # _, _ are the duration and tiebreak id, but that isn't needed
      _, _, curr_proc = heapq.heappop(SJF_queue)
      print(f"Starting task {curr_proc['task']['task']}...")    

    # every process still in the queue increases wait time
    for t in SJF_queue: 
      t[2]['wait_time'] += 1   

    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, [item[2] for item in SJF_queue], finished_procs)

    # 1 second delay for visualization
    time.sleep(1)
  
  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")

def SRTF(processes, on_tick=None):
  SRTF_queue = []
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  for i in range(total_duration):
    for proc in processes:
      if proc['start_time'] == i:
        task_info = {'task': proc, 'wait_time': 0, 'executed_time': 0}
        # proc['task'] (the task id) is included purely as a heap tiebreaker
        # for equal remaining times, so ties never fall through to comparing dicts
        heapq.heappush(SRTF_queue, (proc['duration'] - task_info['executed_time'], proc['task'], task_info))

    # sets a process to run if there is none
    if curr_proc == None:
      # _, _ are the remaining time and tiebreak id, but that isn't needed
      _, _, curr_proc = heapq.heappop(SRTF_queue)
      print(f"Starting task {curr_proc['task']['task']}...")   
    else:
      if SRTF_queue:
        # challenger proc, process than can maybe have the SRT
        _, _, ch_proc = heapq.heappop(SRTF_queue)
        ch_proc_rt = ch_proc['task']['duration'] - ch_proc['executed_time']
        curr_proc_rt = curr_proc['task']['duration'] - curr_proc['executed_time']

        # changes context if the challenger proc has a SRT than the current proc
        if ch_proc_rt < curr_proc_rt:
          heapq.heappush(SRTF_queue, (curr_proc_rt, curr_proc['task']['task'], curr_proc))
          curr_proc = ch_proc
        else:
          heapq.heappush(SRTF_queue, (ch_proc_rt, ch_proc['task']['task'], ch_proc))
    
    # every process still in the queue increases wait time
    for t in SRTF_queue: 
      t[2]['wait_time'] += 1  
    
    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, [item[2] for item in SRTF_queue], finished_procs)

    # 1 second delay for visualization
    time.sleep(1)
  
  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")

def prioc(processes, on_tick=None):
  prioc_queue = []
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  for i in range(total_duration):
    for proc in processes:
      if proc['start_time'] == i:
        # proc['task'] (the task id) is included purely as a heap tiebreaker
        # for equal priorities, so ties never fall through to comparing dicts
        heapq.heappush(prioc_queue, (-1 * proc['priority'], proc['task'], {'task': proc, 'wait_time': 0, 'executed_time': 0}))

    # sets a process to run if there is none
    if curr_proc == None:
      # _, _ are the priority and tiebreak id, but that isn't needed
      _, _, curr_proc = heapq.heappop(prioc_queue)
      print(f"Starting task {curr_proc['task']['task']}...")    

    # every process still in the queue increases wait time
    for t in prioc_queue: 
      t[2]['wait_time'] += 1   

    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, [item[2] for item in prioc_queue], finished_procs)

    # 1 second delay for visualization
    time.sleep(1)
  
  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")

def priop(processes, on_tick=None):
  prioc_queue = []
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  # highest priority new process
  hpnp = {'task': {'priority': -1}}
  new_process = False
  for i in range(total_duration):
    for proc in processes:
      if proc['start_time'] == i:
        new_process = True
        if proc['priority'] > hpnp['task']['priority']:
          hpnp = {'task': proc, 'wait_time': 0, 'executed_time': 0}
        # proc['task'] (the task id) is included purely as a heap tiebreaker
        # for equal priorities, so ties never fall through to comparing dicts
        heapq.heappush(prioc_queue, (-1 * proc['priority'], proc['task'], {'task': proc, 'wait_time': 0, 'executed_time': 0}))
      
    # check if the hpnp has a priority higher than the current process
    if new_process and curr_proc != None:
      if hpnp['task']['priority'] > curr_proc['task']['priority']:
        heapq.heappush(prioc_queue, (-1 * curr_proc['task']['priority'], curr_proc['task']['task'], curr_proc))
        _, _, curr_proc = heapq.heappop(prioc_queue)
      new_process = False
      hpnp = {'task': {'priority': -1}}
    
    # sets a process to run if there is none
    if curr_proc == None:
      # _, _ are the priority and tiebreak id, but that isn't needed
      _, _, curr_proc = heapq.heappop(prioc_queue)
      print(f"Starting task {curr_proc['task']['task']}...")    

    # every process still in the queue increases wait time
    for t in prioc_queue: 
      t[2]['wait_time'] += 1   

    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, [item[2] for item in prioc_queue], finished_procs)

    # 1 second delay for visualization
    time.sleep(1)
  
  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")

def priod(processes, aging, on_tick=None):
  prioc_queue = []
  total_duration = sum(p['duration'] for p in processes)
  curr_proc = None
  finished_procs = []
  # highest priority new process
  hpnp = {'task': {'priority': -1}}
  new_process = False
  for i in range(total_duration):
    for proc in processes:
      if proc['start_time'] == i:
        new_process = True
        if proc['priority'] > hpnp['task']['priority']:
          hpnp = {'task': proc, 'wait_time': 0, 'executed_time': 0}
        heapq.heappush(prioc_queue, (-proc['priority'], -proc['priority'], proc['task'], {'task': proc, 'wait_time': 0, 'executed_time': 0, 'dynamic_priority': proc['priority']}))
  
    # check if the hpnp has a dynamic priority higher than the current process
    if new_process and curr_proc != None:
      if hpnp['task']['priority'] > curr_proc['task']['priority']:
        heapq.heappush(prioc_queue, (-curr_proc['task']['priority'], -curr_proc['task']['priority'], curr_proc['task']['task'], curr_proc))
        _, _, _, curr_proc = heapq.heappop(prioc_queue)
      new_process = False
      hpnp = {'task': {'priority': -1}}
    
    # sets a process to run if there is none
    if curr_proc == None:
      # _ is the duration, but that isn't needed
      _, _, _, curr_proc = heapq.heappop(prioc_queue)
      print(f"Starting task {curr_proc['task']['task']}...")
    
    aux_queue = []
    # every process still in the queue increases wait time and dynamic priority
    while prioc_queue:
      # since the tuple is immutable, we recreate it and then replace it
      old_dp, ep, id, task_inq = heapq.heappop(prioc_queue)
      task_inq['wait_time'] += 1
      new_dp = old_dp - aging
      task_inq['dynamic_priority'] = -new_dp
      heapq.heappush(aux_queue, (new_dp, ep, id, task_inq))
    for t in aux_queue:
      heapq.heappush(prioc_queue, t)
    

    # run 1 second of the current process
    curr_proc['executed_time'] += 1
    print(f"Task {curr_proc['task']['task']}")
    print('#' * curr_proc['executed_time'], end='')
    print('-' * (curr_proc['task']['duration'] - curr_proc['executed_time']), end='')
    print('\n')

    # finishing process
    if curr_proc['executed_time'] == curr_proc['task']['duration']:
      print(f"Finished process {curr_proc['task']['task']}")
      finished_procs.append(curr_proc)
      curr_proc = None

    if on_tick:
      on_tick(i, curr_proc, [item[3] for item in prioc_queue], finished_procs)

    # 1 second delay for visualization
    time.sleep(1)
  
  mean_wait_time = sum(item['wait_time'] for item in finished_procs) / len(finished_procs)
  for proc in finished_procs:
    print(proc)
    print("\n")
  
  print(f"Mean wait time: {mean_wait_time}\n")