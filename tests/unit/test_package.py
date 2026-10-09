"""Phase 0 smoke tests for the project structure."""


def test_optimizer_package_imports() -> None:
    """The top-level package is importable and exposes its version."""
    import optimizer

    assert optimizer.__version__ == "0.1.0"

