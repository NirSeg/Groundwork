import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load_board_sync():
    loader = SourceFileLoader("board_sync", str(Path("scripts/board-sync")))
    spec = importlib.util.spec_from_loader("board_sync", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_board_sync_only_syncs_p0():
    mod = _load_board_sync()
    assert list(mod.LANES.keys()) == ["p0"], (
        f"board-sync should only sync p0, got: {list(mod.LANES.keys())}"
    )
