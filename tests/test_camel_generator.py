def camel_generator():
    # Capture conversation passes, and the ability to summarize if needed (running out of turns, or conversation going in circles)
    yield ("a", 1)
    yield ("b", 2)
    yield ("c", 3)

def test_camel_generator():
    *_, last = camel_generator()
    assert last == ('c', 3)