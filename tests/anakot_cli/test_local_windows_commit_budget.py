"""Windows unified-memory commit room sizes local-model launch and prompt caches."""

from types import SimpleNamespace

from anakot_cli.local_runtime import hardware
from anakot_cli.local_runtime.estimator import HardwareBudget


GIB = 1 << 30


def test_windows_commit_room_leaves_desktop_margin(monkeypatch):
    stat = SimpleNamespace(ullTotalPhys=50 * GIB, ullAvailPageFile=40 * GIB, ullTotalPageFile=60 * GIB)
    monkeypatch.setattr(hardware, "_windows_memory_status", lambda: stat)
    room = hardware._windows_commit_room()
    assert room == 40 * GIB - max(hardware._MARGIN_FLOOR, int(50 * GIB * hardware._MARGIN_FRACTION))


def test_prompt_cache_uses_remaining_commit_room_per_resident():
    live = HardwareBudget(usable_vram_bytes=8 * GIB, total_device_bytes=8 * GIB,
                          ram_available_bytes=0, uma=True, commit_room_bytes=15 * GIB)
    assert hardware.prompt_cache_bytes(live, 4 * GIB) == 8 * GIB
    assert hardware.prompt_cache_bytes(live, 4 * GIB, residents=2) == (5 * GIB) // 2


def test_launch_budget_narrows_uma_capacity(monkeypatch):
    capacity = HardwareBudget(usable_vram_bytes=16 * GIB, total_device_bytes=20 * GIB,
                              ram_available_bytes=0, uma=True)
    monkeypatch.setattr(hardware, "_windows_commit_room", lambda own_bytes=0: 10 * GIB)
    live = hardware.launch_budget(capacity)
    assert live is not None
    assert live.commit_room_bytes == 10 * GIB
    assert live.usable_vram_bytes == int(10 * GIB * (1 - hardware._UMA_HEADROOM_FRACTION))
