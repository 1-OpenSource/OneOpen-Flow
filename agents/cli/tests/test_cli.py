"""CLI agent unit tests."""


def mask_secrets(text: str, secrets: dict[str, str]) -> str:
    masked = text
    for value in secrets.values():
        if value:
            masked = masked.replace(value, "***")
    return masked


def test_secret_masking():
    assert mask_secrets("password=hunter2", {"x": "hunter2"}) == "password=***"


def test_allowed_exit_codes():
    allowed = {0, 2}
    assert 0 in allowed
    assert 1 not in allowed
