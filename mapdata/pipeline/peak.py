"""The peak memory of a stage: the build's own process, its largest worker, and all of them together (P4-T1l).

A thread looks every half second at this process and its child processes (the
workers of a pool). A worker's peak comes from Windows, which keeps it, so a
short spike between two looks is not missed; the build's own process and the
total of all of them are only as good as the looks. On other systems the
numbers are zeros and nothing is said.
"""
from __future__ import annotations

import os
import sys
import threading

INTERVAL_S = 0.5


def _win_api():
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    class ENTRY(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]

    k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(ENTRY)]
    k32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ENTRY)]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]

    def children(pid: int) -> list[int]:
        snap = k32.CreateToolhelp32Snapshot(0x2, 0)   # TH32CS_SNAPPROCESS
        if not snap or snap == wintypes.HANDLE(-1).value:
            return []
        out = []
        try:
            e = ENTRY()
            e.dwSize = ctypes.sizeof(ENTRY)
            ok = k32.Process32First(snap, ctypes.byref(e))
            while ok:
                if e.th32ParentProcessID == pid:
                    out.append(int(e.th32ProcessID))
                ok = k32.Process32Next(snap, ctypes.byref(e))
        finally:
            k32.CloseHandle(snap)
        return out

    def memory(pid: int) -> tuple[int, int] | None:
        """(working set now, peak working set) in bytes, or None if the process has gone."""
        h = k32.OpenProcess(0x1000 | 0x0010, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ
        if not h:
            h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return None
        try:
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            if not psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                return None
            return int(pmc.WorkingSetSize), int(pmc.PeakWorkingSetSize)
        finally:
            k32.CloseHandle(h)

    return children, memory


class PeakWatch:
    """Use as `with PeakWatch() as w: ...`; then w.main_mb, w.worker_mb and w.total_mb, and w.sentence().

    main_mb is the largest working set of this process seen at a look: Windows keeps one peak for a process's
    whole life, which for a build is every stage before, so it cannot be used. worker_mb is the largest peak of
    any child process, from Windows, as each pool's workers live only for one stage; total_mb the largest sum of
    all of them seen at one look."""

    def __init__(self, interval: float = INTERVAL_S):
        self.interval = interval
        self.main_mb = self.worker_mb = self.total_mb = 0.0
        self.workers_seen = 0
        self._stop = threading.Event()
        self._thread = None
        self._api = _win_api() if sys.platform == "win32" else None
        self._peaks: dict[int, int] = {}

    def _look(self) -> None:
        children, memory = self._api
        me = os.getpid()
        total = 0
        mine = memory(me)
        if mine:
            total += mine[0]
            self.main_mb = max(self.main_mb, mine[0] / 2 ** 20)
        for pid in children(me):
            got = memory(pid)
            if got:
                total += got[0]
                self._peaks[pid] = max(self._peaks.get(pid, 0), got[1])
        self.worker_mb = max((v / 2 ** 20 for v in self._peaks.values()), default=0.0)
        self.workers_seen = len(self._peaks)
        self.total_mb = max(self.total_mb, total / 2 ** 20)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self._look()
            except Exception:   # a watch must never stop a build
                pass

    def __enter__(self):
        if self._api is not None:
            try:
                self._look()
            except Exception:
                self._api = None
            else:
                self._thread = threading.Thread(target=self._run, name="peak-memory", daemon=True)
                self._thread.start()
        return self

    def __exit__(self, *exc):
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
            try:
                self._look()
            except Exception:
                pass
        return False

    def sentence(self) -> str:
        """A plain sentence for the build log, or "" where nothing was measured."""
        if self._api is None or not self.main_mb:
            return ""
        text = f"Peak memory: the build's own process {self.main_mb:,.0f} MB"
        if self.workers_seen:
            text += f", the largest worker {self.worker_mb:,.0f} MB, all together {self.total_mb:,.0f} MB"
        return text + "."
