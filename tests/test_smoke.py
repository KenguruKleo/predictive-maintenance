"""Smoke tests — verify minimal imports work in CI."""


def test_azure_functions_import() -> None:
    import azure.functions as func  # noqa: F401

    assert func.FunctionApp is not None


def test_function_app_instantiation() -> None:
    import azure.functions as func

    app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
    assert app is not None
