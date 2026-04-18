"""Smoke tests — verify minimal imports work in CI."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_azure_functions_import() -> None:
    import azure.functions as func  # noqa: F401

    assert func.FunctionApp is not None


def test_function_app_instantiation() -> None:
    import azure.functions as func

    app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
    assert app is not None


def test_documents_trigger_import() -> None:
    from triggers import http_documents

    assert http_documents.ALLOWED_CONTAINERS
