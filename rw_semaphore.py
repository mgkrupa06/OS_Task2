"""
Readers-Writers problem - SEMAPHORE based (fair / starvation-free variant).

Shared resource : SharedDatabase (one integer).  Critical sections: db.read() and db.write().
Semaphores
  resource_lock  (init 1) : held by ONE writer, or by the whole group of active readers.
  count_mutex    (init 1) : protects the variable active_readers (itself shared data).
  turnstile      (init 1) : FIFO gate; a waiting writer blocks later readers, so writers
                            cannot starve and readers cannot be starved either.
Run:  python rw_semaphore.py --readers 4 --writers 2 --rounds 3 --delay 1.0
"""
import argparse, os, random, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
from sync_trace import Tracer, write_html, validate_readers_writers


class SharedDatabase:
    """The shared resource. write() is deliberately non-atomic so a race would show up as lost updates."""
    def __init__(self):
        self.value = 0

    def read(self):
        return self.value

    def write(self, pause):
        temp = self.value
        time.sleep(pause)            # window in which an unprotected second writer would corrupt data
        self.value = temp + 1
        return self.value


resource_lock = threading.Semaphore(1)
count_mutex = threading.Semaphore(1)
turnstile = threading.Semaphore(1)
active_readers = 0
db = SharedDatabase()


def reader(rid, rounds, scale, trace):
    global active_readers
    name = f"R{rid}"
    for _ in range(rounds):
        time.sleep(random.uniform(0.1, 0.6) * scale)                  # idle
        trace.log(name, "waiting", "requests read access")
        turnstile.acquire()                                           # wait(turnstile)
        count_mutex.acquire()                                         # wait(count_mutex)
        active_readers += 1
        if active_readers == 1:
            resource_lock.acquire()                                   # first reader locks writers out
        trace.log(name, "reading", f"entered CS, readers inside = {active_readers}", value=db.read())
        count_mutex.release()                                         # signal(count_mutex)
        turnstile.release()                                           # signal(turnstile)

        time.sleep(random.uniform(0.2, 0.5) * scale)                  # ---- reading (CS) ----

        count_mutex.acquire()
        active_readers -= 1
        trace.log(name, "idle", f"left CS, readers inside = {active_readers}")
        if active_readers == 0:
            resource_lock.release()                                   # last reader lets writers in
        count_mutex.release()


def writer(wid, rounds, scale, trace):
    name = f"W{wid}"
    for _ in range(rounds):
        time.sleep(random.uniform(0.3, 0.9) * scale)
        trace.log(name, "waiting", "requests write access")
        turnstile.acquire()                                           # queue behind earlier arrivals
        resource_lock.acquire()                                       # exclusive access
        turnstile.release()
        trace.log(name, "writing", "entered CS (exclusive)", value=db.value)
        new_value = db.write(0.3 * scale)                             # ---- writing (CS) ----
        trace.log(name, "idle", f"left CS, wrote value {new_value}", value=new_value)
        resource_lock.release()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--readers", type=int, default=4)
    p.add_argument("--writers", type=int, default=2)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--delay", type=float, default=1.0, help="scale factor for all delays")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=os.path.join(HERE, "..", "..", "generated_html", "readers_writers_semaphore.html"))
    a = p.parse_args()
    if a.seed is not None:
        random.seed(a.seed)

    actors = [{"id": f"R{i}", "role": "reader"} for i in range(1, a.readers + 1)] + \
             [{"id": f"W{i}", "role": "writer"} for i in range(1, a.writers + 1)]
    trace = Tracer("Readers-Writers (Semaphores)", "rw", actors,
                   description="Many readers may share the resource; a writer needs it exclusively. Built from semaphores.")
    threads = [threading.Thread(target=reader, args=(i, a.rounds, a.delay, trace)) for i in range(1, a.readers + 1)] + \
              [threading.Thread(target=writer, args=(i, a.rounds, a.delay, trace)) for i in range(1, a.writers + 1)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert db.value == a.writers * a.rounds, "lost update detected"
    print(f"final value = {db.value} (expected {a.writers * a.rounds})")
    validate_readers_writers(trace.events)
    write_html(trace, a.out)


if __name__ == "__main__":
    main()
