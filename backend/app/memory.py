"""Keep the process inside the small memory of the free host (512 MB on Render).

glibc gives every thread that allocates its own malloc arena and rarely hands freed memory back, so a
FastAPI app answering sync endpoints from a 40-thread pool grows until it is killed even when Python
has freed everything. Two arenas are plenty for one worker, and a trim after heavy work returns the
freed pages. Both are no-ops off glibc (Windows, macOS, musl).
"""
import ctypes
import ctypes.util
import gc

M_ARENA_MAX = -8
_libc = None


def _glibc():
    global _libc
    if _libc is None:
        try:
            name = ctypes.util.find_library("c")
            lib = ctypes.CDLL(name) if name else None
            _libc = lib if lib is not None and hasattr(lib, "malloc_trim") and hasattr(lib, "mallopt") else False
        except OSError:
            _libc = False
    return _libc or None


def limit_arenas(count: int = 2) -> bool:
    lib = _glibc()
    return bool(lib and lib.mallopt(M_ARENA_MAX, count))


def release_memory() -> None:
    gc.collect()
    lib = _glibc()
    if lib:
        lib.malloc_trim(0)
