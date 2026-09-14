from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if start_bucket not in ("one", "two"):
        raise ValueError("start_bucket must be 'one' or 'two'")

    capacities = {"one": bucket_one, "two": bucket_two}
    if start_bucket == "one":
        start = (bucket_one, 0)
    else:
        start = (0, bucket_two)

    def forbidden(state):
        if start_bucket == "one":
            return state[0] == 0 and state[1] == bucket_two
        return state[1] == 0 and state[0] == bucket_one

    def neighbors(a, b):
        yield (bucket_one, b)
        yield (a, bucket_two)
        yield (0, b)
        yield (a, 0)
        amount = min(a, bucket_two - b)
        yield (a - amount, b + amount)
        amount = min(b, bucket_one - a)
        yield (a + amount, b - amount)

    if not forbidden(start):
        queue = deque([(start, 1)])
        visited = {start}
        while queue:
            (a, b), moves = queue.popleft()
            if a == goal:
                return (moves, "one", b)
            if b == goal:
                return (moves, "two", a)
            for nxt in neighbors(a, b):
                if nxt not in visited and not forbidden(nxt):
                    visited.add(nxt)
                    queue.append((nxt, moves + 1))

    raise ValueError("goal is impossible to reach")
