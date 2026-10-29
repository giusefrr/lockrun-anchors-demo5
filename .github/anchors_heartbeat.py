"""The anchors repository's heartbeat (risk's decision of 2026-10-29: no gap is ever accepted). Run hourly
by the repository's own scheduled job (.github/workflows/anchors-heartbeat.yml), independent of the
service and the operator droplet: when no deposit landed in the last hour, append one line

  {"kind": "heartbeat", "note": "no deposit received", "time", "last_deposit", "heads": {log: {count, head}}}

each log's heads those of its last line (anchor or heartbeat). verify-repo counts it as a point of its
logs' cadence; a heartbeat naming other heads than the line before it is a tamper. Standard library only.

  python3 anchors_heartbeat.py anchors.jsonl     (ANCHORS_HEARTBEAT_NOW overrides the time, for tests)
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

QUIET = timedelta(hours=1)        # no deposit for longer than this: a heartbeat
ONCE = timedelta(minutes=50)      # and not twice in one hourly run's window


def main(path: str) -> int:
    now = os.environ.get("ANCHORS_HEARTBEAT_NOW")
    now = datetime.fromisoformat(now) if now else datetime.now(timezone.utc).replace(microsecond=0)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if text and not text.endswith("\n"):
        print(f"{path} does not end with a newline: not appending", file=sys.stderr)
        return 1
    heads, last_deposit, last_line = {}, None, None
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            a = json.loads(line)
            if a.get("kind") == "heartbeat":
                heads.update(a["heads"])
                last_line = datetime.fromisoformat(a["time"])
            elif a.get("kind") == "restore":
                continue
            else:
                heads[a["holdout_id"]] = {"count": a["count"], "head": a["head"]}
                last_deposit = a["time"]
                last_line = datetime.fromisoformat(a["time"])
        except (ValueError, KeyError, TypeError, AttributeError):
            print(f"{path} line {i} is not an anchor or a heartbeat: not appending", file=sys.stderr)
            return 1
    if last_deposit is None or now - datetime.fromisoformat(last_deposit) <= QUIET or now - last_line < ONCE:
        return 0
    beat = {"kind": "heartbeat", "note": "no deposit received", "time": now.isoformat(),
            "last_deposit": last_deposit, "heads": heads}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(beat, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"heartbeat: no deposit since {last_deposit}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
