import os
import queue
import sys
import threading
import time

import matplotlib

_NON_INTERACTIVE_BACKENDS = {"agg", "pdf", "ps", "svg", "cairo", "template", "pgf"}


def _ensure_interactive_backend():
    """matplotlib silently falls back to the non-interactive Agg backend if
    it can't find a GUI toolkit (e.g. no python3-tk installed). That failure
    is easy to miss -- plt.show() just does nothing. If the backend that's
    already active/configured is interactive, leave it alone; otherwise try
    the common interactive backends explicitly and fail with a clear message
    instead of silently rendering nothing.

    Set SCHEDVIZ_ALLOW_HEADLESS=1 to skip this check entirely (useful for
    automated tests / saving animations to file without a display)."""
    if os.environ.get("SCHEDVIZ_ALLOW_HEADLESS") == "1":
        return matplotlib.get_backend()

    current = matplotlib.get_backend().lower()
    if current not in _NON_INTERACTIVE_BACKENDS:
        return current  # already interactive (or user explicitly configured it)

    if sys.platform == 'darwin':
        candidates = ["MacOSX", "QtAgg", "TkAgg"]
    else:
        candidates = ["TkAgg", "QtAgg", "GTK4Agg", "GTK3Agg"]

    for name in candidates:
        try:
            matplotlib.use(name, force=True)
            import matplotlib.pyplot as plt
            fig = plt.figure()
            plt.close(fig)
            return name
        except Exception:
            continue

    raise RuntimeError(
        "No interactive matplotlib backend is available (tried "
        f"{', '.join(candidates)}), so a plot window can't be opened.\n"
        "This almost always means a GUI toolkit is missing, not a bug in "
        "this script. Fix depends on your OS:\n"
        "  Debian/Ubuntu:  sudo apt install python3-tk\n"
        "  Fedora:         sudo dnf install python3-tkinter\n"
        "  Arch:           sudo pacman -S tk\n"
        "  macOS (brew):   brew install python-tk\n"
        "  or:             pip install PyQt6\n"
        "Then rerun (no need to recreate your venv unless you used "
        "--system-site-packages=False and it still can't see it)."
    )


_ensure_interactive_backend()

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation

FRAME_INTERVAL_MS = 33  # ~30 fps
WAITING_COLOR = "white"
FINISHED_EDGE = "black"

# layout mosaics for 1..4 simultaneous algorithms
_MOSAICS = {
    1: "A",
    2: "A\nB",
    3: "AB\nCC",
    4: "AB\nCD",
}


def _task_colors(processes):
    #Assign a stable color per task id using tab10/tab20.
    ids = sorted({p['task'] for p in processes})
    cmap = plt.get_cmap('tab20' if len(ids) > 10 else 'tab10')
    return {tid: cmap(i % cmap.N) for i, tid in enumerate(ids)}


class _RunState:
    #Tracks the evolving Gantt data for a single algorithm run.

    def __init__(self, name, processes, show_priority, show_dynamic):
        self.name = name
        self.processes = processes
        self.show_priority = show_priority
        self.show_dynamic = show_dynamic
        self.total_duration = sum(p['duration'] for p in processes)
        self.task_ids = sorted({p['task'] for p in processes})
        self.colors = _task_colors(processes)

        # per task: list of closed (start, end, state) segments
        self.segments = {tid: [] for tid in self.task_ids}
        # per task: the currently-open segment, as [start, state], or None
        self.open_seg = {tid: None for tid in self.task_ids}
        # per task: latest known priority / dynamic priority
        self.priority = {tid: None for tid in self.task_ids}
        self.dynamic_priority = {tid: None for tid in self.task_ids}
        # per task: simulated time at which it finished, or None while still going
        self.finished_at = {tid: None for tid in self.task_ids}

        self.last_tick_time = -1          # simulated seconds, i.e. the `i` from on_tick
        self.last_tick_wallclock = None    # time.time() when that tick arrived
        self.mean_wait_time = None
        self.done = False
        self.q = queue.Queue()

    def push(self, t, curr_proc, waiting_tasks, finished_procs):
        self.q.put((t, curr_proc, waiting_tasks, finished_procs))

    def _apply_tick(self, t, active_id, states, priorities, dyn_priorities):
        """Close out the previous open segment (if its state changed) and
        open a fresh one for time step t -> t+1 for every task present.
        A task that has finished is frozen at the moment it finishes: its
        segment stops growing and further ticks for it are ignored, so the
        bar visually stays put right where the task completed."""
        for tid, state in states.items():
            if self.finished_at.get(tid) is not None:
                continue  # already frozen, don't keep drawing it

            prev = self.open_seg.get(tid)
            if prev is None or prev[1] != state:
                if prev is not None:
                    self.segments[tid].append((prev[0], t, prev[1]))
                self.open_seg[tid] = [t, state]

            if state == 'finished':
                # close this final segment at a fixed width (t -> t+1) and
                # freeze -- no further growth, no further updates.
                start = self.open_seg[tid][0]
                self.segments[tid].append((start, t + 1, 'finished'))
                self.open_seg[tid] = None
                self.finished_at[tid] = t + 1

            if tid in priorities:
                self.priority[tid] = priorities[tid]
            if tid in dyn_priorities:
                self.dynamic_priority[tid] = dyn_priorities[tid]

        self.last_tick_time = t
        self.last_tick_wallclock = time.time()

    def drain(self):
        #Pull every pending tick off the queue and fold it into state.
        drained_any = False
        while True:
            try:
                t, curr_proc, waiting_tasks, finished_procs = self.q.get_nowait()
            except queue.Empty:
                break
            drained_any = True

            states, priorities, dyn = {}, {}, {}

            if curr_proc is not None:
                tid = curr_proc['task']['task']
                states[tid] = 'active'
                priorities[tid] = curr_proc['task'].get('priority')
                dyn[tid] = curr_proc.get('dynamic_priority')

            for w in waiting_tasks:
                tid = w['task']['task']
                states[tid] = 'waiting'
                priorities[tid] = w['task'].get('priority')
                dyn[tid] = w.get('dynamic_priority')

            for f in finished_procs:
                tid = f['task']['task']
                states[tid] = 'finished'
                priorities[tid] = f['task'].get('priority')
                dyn[tid] = f.get('dynamic_priority')

            self._apply_tick(t, curr_proc, states, priorities, dyn)

            if len(finished_procs) == len(self.processes) and finished_procs:
                waits = [f['wait_time'] for f in finished_procs]
                self.mean_wait_time = sum(waits) / len(waits)
                self.done = True

        return drained_any

    def current_open_end(self):
        """How far (in simulated seconds) the open segment should currently
        be drawn, interpolating smoothly toward last_tick_time + 1."""
        if self.last_tick_wallclock is None:
            return 0.0
        elapsed = time.time() - self.last_tick_wallclock
        frac = min(1.0, max(0.0, elapsed))
        return self.last_tick_time + frac


class LiveDashboard:
    #Runs up to 4 algorithms concurrently and animates them side by side.

    def __init__(self, runs):
        """
        runs: list of dicts, each with:
          name: str (title for the panel)
          func: callable (one of scaling.FCFS/RR/SJF/SRTF/prioc/priop/priod)
          kwargs: dict of extra kwargs (e.g. {'quantum': 2}), processes excluded
          processes: list of process dicts for this run
          show_priority: bool
          show_dynamic: bool
        """
        if not (1 <= len(runs) <= 4):
            raise ValueError("choose between 1 and 4 algorithms")

        self.states = [
            _RunState(r['name'], r['processes'], r.get('show_priority', False),
                      r.get('show_dynamic', False))
            for r in runs
        ]
        self.runs = runs

        mosaic = _MOSAICS[len(runs)]
        self.fig, axd = plt.subplot_mosaic(
            mosaic, figsize=(16, 9), constrained_layout=True
        )
        self.axes = [axd[k] for k in sorted(axd.keys())][:len(runs)]
        self.fig.canvas.manager.set_window_title("Scheduling algorithms - live view")

        try:
            mng = plt.get_current_fig_manager()
            mng.full_screen_toggle()
        except Exception:
            pass  # not all backends support this; not fatal

        self._init_axes()
        self.threads = []

    def _init_axes(self):
        for ax, st in zip(self.axes, self.states):
            ax.set_title(st.name, fontsize=13, fontweight='bold')
            ax.set_xlabel("time (s)")
            ax.set_xlim(0, max(1, st.total_duration))
            ax.set_ylim(0.5, len(st.task_ids) + 0.5)
            ax.set_yticks(range(1, len(st.task_ids) + 1))
            ax.set_yticklabels([f"task {tid}" for tid in st.task_ids])
            ax.grid(axis='x', linestyle=':', alpha=0.4)

    def _row(self, st, tid):
        return st.task_ids.index(tid) + 1

    def _ytick_label(self, st, tid):
        bits = [f"task {tid}"]
        if st.show_priority and st.priority.get(tid) is not None:
            bits.append(f"P:{st.priority[tid]}")
        if st.show_dynamic and st.dynamic_priority.get(tid) is not None:
            bits.append(f"DP:{st.dynamic_priority[tid]}")
        return "  ".join(bits)

    def _redraw(self, st, ax):
        ax.cla()
        ax.set_title(st.name, fontsize=13, fontweight='bold')
        ax.set_xlabel("time (s)")
        xmax = max(st.total_duration, st.current_open_end() + 1)
        ax.set_xlim(0, xmax)
        ax.set_ylim(0.5, len(st.task_ids) + 0.5)
        ax.set_yticks(range(1, len(st.task_ids) + 1))
        ax.set_yticklabels([self._ytick_label(st, tid) for tid in st.task_ids])
        ax.grid(axis='x', linestyle=':', alpha=0.4)

        open_end = st.current_open_end()

        for tid in st.task_ids:
            row = self._row(st, tid)
            color = st.colors[tid]
            segs = list(st.segments[tid])
            if st.open_seg[tid] is not None:
                start, state = st.open_seg[tid]
                end = max(start, open_end)
                segs = segs + [(start, end, state)]

            if not segs:
                continue

            xranges = [(s, max(0.02, e - s)) for s, e, _ in segs]
            facecolors = [
                WAITING_COLOR if state == 'waiting' else color
                for _, _, state in segs
            ]
            edgecolors = [color for _ in segs]
            ax.broken_barh(xranges, (row - 0.35, 0.7),
                            facecolors=facecolors, edgecolors=edgecolors,
                            linewidth=1.4)

        legend_handles = [
            mpatches.Patch(facecolor='gray', edgecolor='gray', label='active / finished'),
            mpatches.Patch(facecolor=WAITING_COLOR, edgecolor='gray', label='waiting'),
        ]
        ax.legend(handles=legend_handles, loc='upper right', fontsize=8, framealpha=0.8)

        if st.mean_wait_time is not None:
            msg = f"Mean wait time: {st.mean_wait_time:.2f}s"
        else:
            msg = "running..."
        ax.text(0.01, 0.98, msg, transform=ax.transAxes, ha='left', va='top',
                fontsize=9, style='italic',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    def _on_frame(self, _frame):
        artists = []
        for st, ax in zip(self.states, self.axes):
            st.drain()
            self._redraw(st, ax)
        return artists

    def start(self):
        for run, st in zip(self.runs, self.states):
            kwargs = dict(run.get('kwargs', {}))
            kwargs['on_tick'] = st.push
            t = threading.Thread(
                target=run['func'],
                kwargs={'processes': run['processes'], **kwargs},
                daemon=True,
            )
            self.threads.append(t)
            t.start()

        self.anim = FuncAnimation(
            self.fig, self._on_frame, interval=FRAME_INTERVAL_MS, cache_frame_data=False
        )
        plt.show()