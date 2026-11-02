"""Run independent jobs on several processor cores at once.

The same approach as the PO's OMR project (src/omr/parallel.py). The laptop
has 4 cores (8 threads). Heavy jobs gain little from the second thread on each
core, and the chip slows down when hot, so the default is 3 workers, which
leaves the machine usable. Results come back to the main process, which alone
writes the log and the caches. With one worker the jobs run in the main
process, with no pool.

The graphics card is not used: the pipeline's work is polygon geometry
(GEOS, through Shapely), which has no graphics card version on Windows.
"""
from __future__ import annotations

import concurrent.futures as cf
import contextlib
import os

DEFAULT_WORKERS = 3
AWAY_WORKERS = 6        # when the PO is away from the laptop (DP103)
ROOM_MB = 6000          # free memory needed before another job is started


def max_workers() -> int:
    return os.cpu_count() or 1


def check_workers(workers: int) -> int:
    if workers < 1:
        raise ValueError(f"the number of workers must be at least 1, not {workers}")
    if workers > max_workers():
        raise ValueError(f"this computer has {max_workers()} logical processors, so {workers} workers is too many")
    return workers


class _InProcess:
    """An executor that runs each job at once, in the main process."""

    def submit(self, function, *args, **kwargs):
        future = cf.Future()
        try:
            future.set_result(function(*args, **kwargs))
        except BaseException as error:  # handed back through the future, as a pool would
            future.set_exception(error)
        return future


@contextlib.contextmanager
def pool(workers: int):
    """An executor with `workers` processes, or one that runs in the main process for 1."""
    check_workers(workers)
    if workers == 1:
        yield _InProcess()
        return
    executor = cf.ProcessPoolExecutor(max_workers=workers)
    try:
        yield executor
    except BaseException:
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    executor.shutdown(wait=True)


def memory_mb() -> tuple[float, float]:
    """This process's private memory and the system's available memory, in MB (Windows; zeros elsewhere)."""
    import sys

    if sys.platform != "win32":
        return 0.0, 0.0
    import ctypes

    class MSX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    msx = MSX()
    msx.dwLength = ctypes.sizeof(MSX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(msx))
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    kernel32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.PagefileUsage / 2 ** 20, msx.ullAvailPhys / 2 ** 20


def room_for_another(running: int, room_mb: float = ROOM_MB) -> bool:
    """Whether another job may start: always the first, then only with room_mb free (DP103).

    Each worker holds its own shapes, so on a big area memory, not the
    processor, is the limit. When memory is short, fewer jobs run at once
    instead of the build stopping.
    """
    if running == 0:
        return True
    _mine, free = memory_mb()
    return not free or free >= room_mb
