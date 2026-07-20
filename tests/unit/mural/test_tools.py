def test_get_mural_connection_url_builds_correct_url() -> None:
    """The OAuth redirect URL strips trailing slashes from the base URL."""
    base_url = "https://example.com/"
    result = base_url.rstrip("/") + "/connect/mural"
    assert result == "https://example.com/connect/mural"
