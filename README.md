# OS Synchronization Assignment

Name / USN: <fill in>

Language: Python 3.8+ (standard library only, no installs needed).

## Layout
- `common/sync_trace.py` - records every state change, validates the trace, writes the HTML page
- `readers_writers/semaphore/rw_semaphore.py`, `readers_writers/monitor/rw_monitor.py`
- `dining_philosophers/semaphore/dp_semaphore.py`, `dining_philosophers/monitor/dp_monitor.py`
- `generated_html/` - output of each run

## Run (no compile step)
    python readers_writers/semaphore/rw_semaphore.py --readers 4 --writers 2 --rounds 3
    python readers_writers/monitor/rw_monitor.py --readers 4 --writers 2 --rounds 3
    python dining_philosophers/semaphore/dp_semaphore.py --meals 3
    python dining_philosophers/monitor/dp_monitor.py --meals 3
Options: `--delay` (scale all sleeps), `--seed` (repeatable timing), `--out` (HTML path).

Each run prints the live trace, checks it, writes the HTML into `generated_html/` and opens it in your browser automatically (set OS_NO_OPEN=1 to disable).
the HTML into `generated_html/`. Open that file in any browser; use Start/Step/Reset/Speed/Timeline.

## Known limitations
- Python monitors are built from Lock + Condition (no native monitor keyword).
- Python semaphores are not strictly FIFO, so fairness is not formally guaranteed.

## AI tools used
<name the tool> - see ai_prompts/prompts.md (add your prompts and what you changed yourself).
