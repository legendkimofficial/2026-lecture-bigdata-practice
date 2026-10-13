"""Probe a larger exact-set run in a child, stopping before system exhaustion.

Uses the unchanged task2_limits.exact_distinct. The stopping threshold is an
explicit practical limit, not a claim that Python or the OS raised MemoryError.
"""
import argparse
import ctypes
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from task2_limits import exact_distinct


class MemoryStatus(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_pagefile", ctypes.c_ulonglong),
                ("available_pagefile", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong)]


class ProcessMemory(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("page_faults", ctypes.c_ulong),
                ("peak_working_set", ctypes.c_size_t),
                ("working_set", ctypes.c_size_t),
                ("quota_peak_paged", ctypes.c_size_t),
                ("quota_paged", ctypes.c_size_t),
                ("quota_peak_nonpaged", ctypes.c_size_t),
                ("quota_nonpaged", ctypes.c_size_t),
                ("pagefile", ctypes.c_size_t),
                ("peak_pagefile", ctypes.c_size_t)]


def memory_status():
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=25_000_000)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--resident-limit-mib", type=int, default=768)
    parser.add_argument("--output", default="limit_probe.json")
    args = parser.parse_args()
    if args.worker:
        count, elapsed, peak = exact_distinct(args.size)
        print(json.dumps({"true_distinct": count, "exact_s": elapsed,
                          "exact_peak_bytes": peak}))
        return

    if sys.platform != "win32":
        raise RuntimeError("This environment probe uses Windows memory APIs")
    start_status = memory_status()
    result = {"n": args.size, "started_at": datetime.now().astimezone().isoformat(),
              "system_total_ram_bytes": start_status.total_physical,
              "system_available_ram_bytes_before": start_status.available_physical,
              "system_load_percent_before": start_status.load,
              "thresholds": {"maximum_seconds": args.seconds,
                             "minimum_available_ram_bytes": 512 * 1024 ** 2,
                             "maximum_child_resident_bytes": args.resident_limit_mib * 1024 ** 2},
              "status": "running", "child_peak_resident_bytes": 0,
              "minimum_system_available_ram_bytes": start_status.available_physical}
    child = subprocess.Popen([sys.executable, "-u", __file__, "--worker",
                              "--size", str(args.size)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
    counters = ProcessMemory()
    counters.cb = ctypes.sizeof(counters)
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemory), ctypes.c_ulong]
    get_memory.restype = ctypes.c_int
    started = time.perf_counter()
    while child.poll() is None:
        status = memory_status()
        elapsed = time.perf_counter() - started
        if get_memory(int(child._handle), ctypes.byref(counters), counters.cb):
            result["child_peak_resident_bytes"] = max(
                result["child_peak_resident_bytes"], counters.peak_working_set)
        result["minimum_system_available_ram_bytes"] = min(
            result["minimum_system_available_ram_bytes"], status.available_physical)
        reason = None
        if status.available_physical < result["thresholds"]["minimum_available_ram_bytes"]:
            reason = "system_available_ram_below_512_MiB"
        elif result["child_peak_resident_bytes"] > result["thresholds"]["maximum_child_resident_bytes"]:
            reason = f"child_resident_memory_above_{args.resident_limit_mib}_MiB"
        elif elapsed >= result["thresholds"]["maximum_seconds"]:
            reason = f"exact_run_exceeded_{args.seconds:g}_seconds"
        if reason:
            child.terminate()
            result.update(status="stopped_at_practical_limit", stopping_reason=reason)
            break
        time.sleep(0.25)
    stdout, stderr = child.communicate()
    result["probe_wall_seconds"] = time.perf_counter() - started
    result["child_exit_code"] = child.returncode
    if result["status"] == "running":
        if child.returncode == 0:
            result.update(status="completed", **json.loads(stdout))
        else:
            result.update(status="worker_failed", error=stderr)
    output = Path(__file__).resolve().parent / "out" / args.output
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
