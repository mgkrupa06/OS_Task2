"""
Readers-Writers problem - MONITOR based.

Python has no 'monitor' keyword, so the monitor abstraction is built as a class whose state is only
touched while holding one lock, with condition variables for waiting (Mesa semantics -> use wait_for/loops).
Monitor state : active_readers, writing, waiting_writers
Conditions    : ok_to_read, ok_to_write
Policy        : writer preference (readers wait while any writer is waiting). Writers cannot starve,
                but a steady stream of writers could starve readers - discuss this in the report.
Run:  python rw_monitor.py --readers 4 --writers 2 --rounds 3
"""
import argparse, os, random, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
from sync_trace import Tracer, write_html, validate_readers_writers


class SharedDatabase:
    def __init__(self):
        self.value = 0

    def read(self):
        return self.value

    def write(self, pause):
        temp = self.value
        time.sleep(pause)
        self.value = temp + 1
        return self.value


class ReadersWritersMonitor:
    """All entry/exit procedures run mutually exclusively because each takes self._lock."""
    def __init__(self, trace):
        self._lock = threading.Lock()
        self.ok_to_read = threading.Condition(self._lock)
        self.ok_to_write = threading.Condition(self._lock)
        self.active_readers = 0
        self.writing = False
        self.waiting_writers = 0
        self.trace = trace

    def start_read(self, name, db):
        with self._lock:
            self.trace.log(name, "waiting", "requests read access")
            self.ok_to_read.wait_for(lambda: not self.writing and self.waiting_writers == 0)
            self.active_readers += 1
            self.trace.log(name, "reading", f"entered CS, readers inside = {self.active_readers}", value=db.read())

    def end_read(self, name):
        with self._lock:
            self.active_readers -= 1
            self.trace.log(name, "idle", f"left CS, readers inside = {self.active_readers}")
            if self.active_readers == 0:
                self.ok_to_write.notify()          # wake one writer

    def start_write(self, name, db):
        with self._lock:
            self.waiting_writers += 1
            self.trace.log(name, "waiting", "requests write access")
            self.ok_to_write.wait_for(lambda: not self.writing and self.active_readers == 0)
            self.waiting_writers -= 1
            self.writing = True
            self.trace.log(name, "writing", "entered CS (exclusive)", value=db.value)

    def end_write(self, name, new_value):
        with self._lock:
            self.writing = False
            self.trace.log(name, "idle", f"left CS, wrote value {new_value}", value=new_value)
            if self.waiting_writers > 0:
                self.ok_to_write.notify()
            else:
                self.ok_to_read.notify_all()


def reader(rid, rounds, scale, mon, db):
    name = f"R{rid}"
    for _ in range(rounds):
        time.sleep(random.uniform(0.1, 0.6) * scale)
        mon.start_read(name, db)
        time.sleep(random.uniform(0.2, 0.5) * scale)      # reading happens OUTSIDE the monitor lock
        mon.end_read(name)


def writer(wid, rounds, scale, mon, db):
    name = f"W{wid}"
    for _ in range(rounds):
        time.sleep(random.uniform(0.3, 0.9) * scale)
        mon.start_write(name, db)
        new_value = db.write(0.3 * scale)
        mon.end_write(name, new_value)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--readers", type=int, default=4)
    p.add_argument("--writers", type=int, default=2)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=os.path.join(HERE, "..", "..", "generated_html", "readers_writers_monitor.html"))
    a = p.parse_args()
    if a.seed is not None:
        random.seed(a.seed)

    actors = [{"id": f"R{i}", "role": "reader"} for i in range(1, a.readers + 1)] + \
             [{"id": f"W{i}", "role": "writer"} for i in range(1, a.writers + 1)]
    trace = Tracer("Readers-Writers (Monitor)", "rw", actors,
                   description="Same problem solved with a monitor: one lock plus condition variables, writer preference.")
    db, mon = SharedDatabase(), ReadersWritersMonitor(trace)
    threads = [threading.Thread(target=reader, args=(i, a.rounds, a.delay, mon, db)) for i in range(1, a.readers + 1)] + \
              [threading.Thread(target=writer, args=(i, a.rounds, a.delay, mon, db)) for i in range(1, a.writers + 1)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert db.value == a.writers * a.rounds, "lost update detected"
    print(f"final value = {db.value} (expected {a.writers * a.rounds})")
    validate_readers_writers(trace.events)
    write_html(trace, a.out)


if __name__ == "__main__":
    main()
