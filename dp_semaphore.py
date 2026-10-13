"""
Dining Philosophers (exactly 4) - SEMAPHORE based.

Resources : 4 forks, each a binary semaphore (init 1). Philosopher i uses fork i (left) and (i+1)%4 (right).
Deadlock  : prevented by a 'room' counting semaphore initialised to N-1 = 3. At most 3 philosophers
            compete for forks, so at least one can always get both -> circular wait is impossible.
Starvation: Python semaphores are not strictly FIFO, so starvation is improbable but not formally excluded;
            a FIFO semaphore would make the room entry fair. Discuss in the report.
Run:  python dp_semaphore.py --meals 3 --delay 1.0
"""
import argparse, os, random, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
from sync_trace import Tracer, write_html, validate_philosophers

N = 4
forks = [threading.Semaphore(1) for _ in range(N)]
room = threading.Semaphore(N - 1)


def philosopher(i, meals, scale, trace):
    name, left, right = f"P{i}", i, (i + 1) % N
    for _ in range(meals):
        trace.log(name, "thinking")
        time.sleep(random.uniform(0.1, 0.5) * scale)
        trace.log(name, "hungry", "wants to eat")

        room.acquire()                                              # wait(room)
        trace.log(name, "acquiring", "entered the room (max 3 seated)")
        forks[left].acquire()                                       # wait(left fork)
        trace.log(name, "acquiring", f"picked up fork {left}", fork=left, owner=i)
        time.sleep(random.uniform(0.05, 0.2) * scale)               # widen the interleaving window
        forks[right].acquire()                                      # wait(right fork)
        trace.log(name, "acquiring", f"picked up fork {right}", fork=right, owner=i)

        trace.log(name, "eating", "has both forks")                 # ---- critical section ----
        time.sleep(random.uniform(0.2, 0.5) * scale)

        trace.log(name, "releasing", f"put down fork {left}", fork=left, owner=None)
        forks[left].release()                                       # signal(left fork)
        trace.log(name, "releasing", f"put down fork {right}", fork=right, owner=None)
        forks[right].release()                                      # signal(right fork)
        room.release()                                              # signal(room)
    trace.log(name, "thinking", "finished all meals")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--meals", type=int, default=3)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=os.path.join(HERE, "..", "..", "generated_html", "dining_philosophers_semaphore.html"))
    a = p.parse_args()
    if a.seed is not None:
        random.seed(a.seed)

    actors = [{"id": f"P{i}", "role": "philosopher"} for i in range(N)]
    trace = Tracer("Dining Philosophers - 4 philosophers (Semaphores)", "dp", actors, forks=list(range(N)),
                   description="Fork semaphores plus a room semaphore (N-1) prevent deadlock.")
    threads = [threading.Thread(target=philosopher, args=(i, a.meals, a.delay, trace)) for i in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()

    validate_philosophers(trace.events, N)
    write_html(trace, a.out)


if __name__ == "__main__":
    main()
