#!/usr/bin/env python3
"""
osx01 UI - Sci-fi terminal dashboard
Kasutus: python osx01_ui.py "sinu ülesanne"

Nõuab: pip install openai rich
"""

import sys
import time
import random
import threading

try:
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    raise SystemExit("[viga] Puudub 'rich' pakett. Paigalda: pip install rich")

import osx01

# ---------------------------------------------------------
# ÜHINE SEISUND
# ---------------------------------------------------------
state = {
    "task": "",
    "model": osx01.DEFAULT_MODEL,
    "status": "BOOT",
    "step": 0,
    "max_steps": 20,
    "log": [],
    "counts": {k: 0 for k in osx01.TOOL_MAP},
    "t0": time.time(),
    "done": False,
    "result": "",
    "osc": [1] * 16,
}

_lock = threading.Lock()

# ---------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------

def on_step(step: int):
    with _lock:
        state["step"] = step
        state["status"] = "RUNNING"
        state["osc"] = [random.randint(3, 8) for _ in range(16)]


def on_tool(name: str, args: dict, result: str):
    with _lock:
        state["counts"][name] += 1
        first_arg = str(next(iter(args.values()), "")) if args else ""
        state["log"].append((name, first_arg[:42]))
        if len(state["log"]) > 8:
            state["log"].pop(0)
        spike = [random.randint(1, 4) for _ in range(16)]
        spike[random.randint(0, 15)] = 8
        spike[random.randint(0, 15)] = 7
        state["osc"] = spike


def on_done(result: str):
    with _lock:
        state["status"] = "DONE"
        state["result"] = result
        state["done"] = True
        state["osc"] = [1] * 16

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

C   = "#00e5ff"
DIM = "#1a5566"
ORG = "#ffaa00"
GRN = "#00ff88"
WHT = "bright_white"
BLK = "on black"
BLOCKS = " ▁▂▃▄▅▆▇█"


def _bar(value: int, max_val: int, width: int = 18) -> str:
    if max_val == 0:
        return "░" * width
    filled = min(width, int(value / max_val * width))
    return "█" * filled + "░" * (width - filled)


def _osc_col(v: int) -> str:
    if v >= 7: return WHT
    if v >= 5: return ORG
    return C


def build_ui() -> Group:
    with _lock:
        task    = state["task"]
        model   = state["model"]
        status  = state["status"]
        step    = state["step"]
        max_s   = state["max_steps"]
        log     = list(state["log"])
        counts  = dict(state["counts"])
        osc     = list(state["osc"])
        t0      = state["t0"]

    elapsed   = int(time.time() - t0)
    remaining = max(0, max_s - step)

    # ── PÄIS ──────────────────────────────────────────────
    hdr_grid = Table.grid(expand=True)
    hdr_grid.add_column(); hdr_grid.add_column(justify="right")

    left = Text()
    left.append("CORE ", style=f"bold {C}")
    left.append("// ", style=f"dim {C}")
    left.append("osx01\n", style=f"bold {WHT}")
    left.append("V.1.0.0", style=f"dim {C}")

    right = Text(justify="right")
    right.append("SYS.ONL: ", style=f"dim {C}")
    right.append("TRUE\n", style=f"bold {C}")
    right.append("NEXUS: OLLAMA  ", style=f"dim {C}")
    right.append(f"T-MINUS: {remaining:02d}", style=C)

    bars = "".join("█" if random.random() > 0.3 else "░" for _ in range(4))
    mid = Text()
    mid.append(f"  UPLINK {bars}  ", style=f"dim {C}")
    mid.append("STATUS: ", style=f"dim {C}")
    status_col = GRN if status == "DONE" else (ORG if status == "BOOT" else C)
    mid.append(status, style=f"bold {status_col}")
    mid.append(f"   STEP {step}/{max_s}", style=f"dim {C}")

    hdr_grid.add_row(left, right)
    header = Panel(Group(hdr_grid, mid), border_style=C, padding=(0, 1), style=BLK)

    # ── TARGET IDENTIFICATION ──────────────────────────────
    task_short = task[:58] + ("…" if len(task) > 58 else "")
    tgt = Text()
    tgt.append("TARGET IDENTIFICATION\n", style=f"dim {C}")
    tgt.append(f"\n  {task_short}\n\n", style=f"bold {WHT}")
    tgt.append("  MODEL     ", style=f"dim {C}"); tgt.append(f"{model}\n", style=C)
    tgt.append("  ELAPSED   ", style=f"dim {C}"); tgt.append(f"{elapsed}s\n", style=C)
    tgt.append("  LOC COORD ", style=f"dim {C}")
    tgt.append(f"X:{step:02d} Y:{elapsed:02d} Z:{remaining:02d}\n", style=C)
    target = Panel(tgt, border_style=C, padding=(0, 1), style=BLK)

    # ── SUBSYSTEM METRICS ─────────────────────────────────
    max_c = max(counts.values()) or 1
    met = Text()
    met.append("SUBSYSTEM METRICS\n\n", style=f"dim {C}")

    GROUPS = [
        ("BASH EXEC     ", "bash"),
        ("FILE READ     ", "read_file"),
        ("FILE WRITE    ", "write_file"),
        ("FILE EDIT     ", "edit_file"),
        ("DIR LIST      ", "ls"),
        ("GLOB SCAN     ", "glob"),
        ("GREP SCAN     ", "grep"),
    ]
    for label, key in GROUPS:
        v = counts[key]
        warn = key in ("write_file", "edit_file") and v > 3
        col = ORG if warn else C
        tag = " [WARN]" if warn else ""
        met.append(f"  {label}{tag}\n", style=f"dim {col}")
        met.append(f"  {_bar(v, max_c)}  ", style=col)
        met.append(f"{v}\n\n", style=WHT)

    metrics = Panel(met, border_style=C, padding=(0, 1), style=BLK)

    # ── ACTIVITY LOG ──────────────────────────────────────
    log_txt = Text()
    log_txt.append("ACTIVITY LOG\n\n", style=f"dim {C}")
    if log:
        for name, entry in log[-6:]:
            log_txt.append(f"  [{name}] ", style=C)
            log_txt.append(f"{entry}\n", style=WHT)
    else:
        log_txt.append("  ...\n", style=f"dim {C}")
    activity = Panel(log_txt, border_style=C, padding=(0, 1), style=BLK)

    # ── FREQ. OSCILLATOR ──────────────────────────────────
    osc_txt = Text()
    osc_txt.append("FREQ. OSCILLATOR\n\n  ", style=f"dim {C}")
    for v in osc:
        osc_txt.append(BLOCKS[v] * 2, style=_osc_col(v))
    osc_txt.append("\n")
    oscillator = Panel(osc_txt, border_style=C, padding=(0, 1), style=BLK)

    return Group(header, target, metrics, activity, oscillator)


# ---------------------------------------------------------
# PEAPROGRAM
# ---------------------------------------------------------

def main():
    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "Uuri selle projekti struktuuri ja kirjuta lühike kokkuvõte."

    console = Console()

    with _lock:
        state["task"]  = goal
        state["model"] = osx01.DEFAULT_MODEL
        state["t0"]    = time.time()

    def _run():
        osx01.run_agent(
            goal,
            max_steps=state["max_steps"],
            on_step=on_step,
            on_tool=on_tool,
            on_done=on_done,
        )

    threading.Thread(target=_run, daemon=True).start()

    def _idle_osc():
        while not state["done"]:
            time.sleep(0.4)
            with _lock:
                if state["status"] != "RUNNING":
                    state["osc"] = [random.randint(0, 2) for _ in range(16)]

    threading.Thread(target=_idle_osc, daemon=True).start()

    with Live(build_ui(), console=console, refresh_per_second=4, transient=False) as live:
        while not state["done"]:
            live.update(build_ui())
            time.sleep(0.25)
        live.update(build_ui())

    if state["result"]:
        console.print()
        console.print(Panel(
            Text(state["result"], style=WHT),
            title=Text("TULEMUS", style=f"bold {GRN}"),
            border_style=GRN, style=BLK, padding=(1, 2),
        ))


if __name__ == "__main__":
    main()
