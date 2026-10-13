"""
Dining Philosophers (exactly 4) - MONITOR based.

Monitor state : state[i] in {THINKING, HUNGRY, EATING}; one condition variable per philosopher.
Rule          : philosopher i may eat only if neither neighbour is EATING. The check and the state change
                happen atomically inside the monitor, so a philosopher takes BOTH forks or none:
                no hold-and-wait -> no deadlock.
Starvation    : possible in theory (two neighbours can keep alternating and block the philosopher between
                them). Discuss in the report; a ticket/age counter would fix it.
Run:  python dp_monitor.py --meals 3 --delay 1.0
"""
import argparse, os, random, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
from sync_trace import Tracer, write_html, validate_philosophers

N = 4
THINKING, HUNGRY, EATING = "thinking", "hungry", "eating"


class DiningTable:
    def __init__(self, trace):
        self._lock = threading.Lock()
        self.state = [THINKING] * N
        self.can_eat = [threading.Condition(self._lock) for _ in range(N)]
        self.trace = trace

    def _test(self, i):
        """Caller holds the monitor lock. Let i eat if hungry and both neighbours are not eating."""
        left_nb, right_nb = (i + N - 1) % N, (i + 1) % N
        if self.state[i] == HUNGRY and self.state[left_nb] != EATING and self.state[right_nb] != EATING:
            self.state[i] = EATING
            name = f"P{i}"
            self.trace.log(name, "acquiring", f"took fork {i}", fork=i, owner=i)
            self.trace.log(name, "acquiring", f"took fork {right_nb}", fork=right_nb, owner=i)
            self.trace.log(name, "eating", "has both forks")
            self.can_eat[i].notify()

    def pickup(self, i):
        with self._lock:
            self.state[i] = HUNGRY
            self.trace.log(f"P{i}", "hungry", "wants to eat")
            self._test(i)
            while self.state[i] != EATING:                 # Mesa semantics: re-check after waking
                self.can_eat[i].wait()

    def putdown(self, i):
        with self._lock:
            self.state[i] = THINKING
            name, right = f"P{i}", (i + 1) % N
            self.trace.log(name, "releasing", f"put down fork {i}", fork=i, owner=None)
            self.trace.log(name, "releasing", f"put down fork {right}", fork=right, owner=None)
            self.trace.log(name, "thinking", "back to thinking")
            self._test((i + N - 1) % N)                    # a neighbour may now be able to eat
            self._test((i + 1) % N)


def philosopher(i, meals, scale, table):
    for _ in range(meals):
        time.sleep(random.uniform(0.1, 0.5) * scale)       # thinking
        table.pickup(i)
        time.sleep(random.uniform(0.2, 0.5) * scale)       # eating (outside the lock)
        table.putdown(i)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--meals", type=int, default=3)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=os.path.join(HERE, "..", "..", "generated_html", "dining_philosophers_monitor.html"))
    a = p.parse_args()
    if a.seed is not None:
        random.seed(a.seed)

    actors = [{"id": f"P{i}", "role": "philosopher"} for i in range(N)]
    trace = Tracer("Dining Philosophers - 4 philosophers (Monitor)", "dp", actors, forks=list(range(N)),
                   description="A monitor grants both forks atomically, so hold-and-wait never occurs.")
    table = DiningTable(trace)
    threads = [threading.Thread(target=philosopher, args=(i, a.meals, a.delay, table)) for i in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    validate_philosophers(trace.events, N)
    write_html(trace, a.out)


if __name__ == "__main__":
    main()
