"""Assertions shared by the run scripts."""


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rejects(action, message="Changed content was accepted"):
    try:
        action()
    except ValueError:
        return
    raise AssertionError(message)
