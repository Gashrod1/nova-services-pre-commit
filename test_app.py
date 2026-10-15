import pytest

from app import calculate, get_password


def test_addition():
    assert calculate(2, 3, "add") == 5


def test_subtraction():
    assert calculate(5, 2, "subtract") == 3


def test_multiplication():
    assert calculate(4, 2.5, "multiply") == 10


def test_division():
    assert calculate(9, 3, "divide") == 3


def test_division_by_zero():
    with pytest.raises(ValueError):
        calculate(10, 0, "divide")


def test_unknown_operation():
    with pytest.raises(ValueError):
        calculate(1, 2, "power")


def test_expression_injection_refused():
    with pytest.raises(ValueError):
        calculate(1, 2, "__import__('os').system('id')")


def test_password_from_environment(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "valeur-de-test")
    assert get_password() == "valeur-de-test"  # pragma: allowlist secret


def test_missing_password_raises(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    with pytest.raises(RuntimeError):
        get_password()
