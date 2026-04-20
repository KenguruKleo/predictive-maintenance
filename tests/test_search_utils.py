from importlib import reload
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import shared.search_utils as search_utils


def test_get_search_client_falls_back_to_admin_key(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_SEARCH_KEY", raising=False)
    monkeypatch.setenv("AZURE_SEARCH_ADMIN_KEY", "admin-key")

    module = reload(search_utils)
    client = module._get_search_client("idx-incident-history")

    assert module.SEARCH_KEY == "admin-key"
    assert client._credential.key == "admin-key"

    monkeypatch.delenv("AZURE_SEARCH_ADMIN_KEY", raising=False)
    reload(search_utils)