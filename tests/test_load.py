import pytest

from log10.load import get_log10_session_tags, log10_session, log10_tags, with_log10_tags


def test_log10_tags():
    # Test single tag
    with log10_tags(["test_tag"]):
        assert get_log10_session_tags() == ["test_tag"]
    assert get_log10_session_tags() == []

    # Test multiple tags
    with log10_tags(["tag1", "tag2"]):
        assert get_log10_session_tags() == ["tag1", "tag2"]
    assert get_log10_session_tags() == []

    # Test nested tags
    with log10_tags(["outer"]):
        assert get_log10_session_tags() == ["outer"]
        with log10_tags(["inner"]):
            assert get_log10_session_tags() == ["outer", "inner"]
        assert get_log10_session_tags() == ["outer"]

    # Test that tags are cleared after context
    assert get_log10_session_tags() == []


def test_log10_session():
    # Test session with no tags
    with log10_session():
        assert get_log10_session_tags() == []

    # Test session with tags
    with log10_session(tags=["session_tag"]):
        assert get_log10_session_tags() == ["session_tag"]


def test_log10_tags_session():
    # Test nested session and tags
    with log10_session(tags=["outer_session"]):
        assert get_log10_session_tags() == ["outer_session"]
        with log10_tags(["inner_tag"]):
            assert get_log10_session_tags() == ["outer_session", "inner_tag"]
        assert get_log10_session_tags() == ["outer_session"]
    assert get_log10_session_tags() == []

    with log10_tags(["outer_tag"]):
        assert get_log10_session_tags() == ["outer_tag"]
        with log10_session(tags=["inner_session"]):
            assert get_log10_session_tags() == ["outer_tag", "inner_session"]
        assert get_log10_session_tags() == ["outer_tag"]
    assert get_log10_session_tags() == []


@pytest.mark.asyncio
async def test_log10_session_async():
    # Test async session with tags
    async with log10_session(tags=["async_session"]):
        assert get_log10_session_tags() == ["async_session"]

    # Test that tags are cleared after async session
    assert get_log10_session_tags() == []


def test_log10_tags_invalid_input():
    # Test with non-list input
    with log10_tags("not_a_list"):
        assert get_log10_session_tags() == []

    # Test with non-string tags
    with log10_tags(["valid", 123, {"invalid": "tag"}]):
        assert get_log10_session_tags() == ["valid"]


def test_log10_session_invalid_input():
    # Test with non-list tags
    with log10_session(tags="not_a_list"):
        assert get_log10_session_tags() == []

    # Test with non-string tags
    with log10_session(tags=["valid", 123, {"invalid": "tag"}]):
        assert get_log10_session_tags() == ["valid"]


def test_with_log10_tags_decorator():
    @with_log10_tags(["decorator_tag1", "decorator_tag2"])
    def decorated_function():
        return get_log10_session_tags()

    # Test that the decorator adds tags
    assert decorated_function() == ["decorator_tag1", "decorator_tag2"]

    # Test that tags are cleared after the decorated function call
    assert get_log10_session_tags() == []

    # Test nested decorators
    @with_log10_tags(["outer_tag"])
    def outer_function():
        @with_log10_tags(["inner_tag"])
        def inner_function():
            return get_log10_session_tags()

        return inner_function()

    assert outer_function() == ["outer_tag", "inner_tag"]
    assert get_log10_session_tags() == []
