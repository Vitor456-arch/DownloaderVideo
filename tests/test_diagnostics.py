from downloadervideo.diagnostics import safe_message


def test_no_credentials_in_errors():
    value = safe_message('Failed https://user:password@example.com/media?token=secret#private Cookie=sessionSecret token=anotherSecret')
    assert "secret" not in value.lower()
    assert "sessionSecret" not in value
    assert "user:password" not in value
    assert "example.com/media" in value
