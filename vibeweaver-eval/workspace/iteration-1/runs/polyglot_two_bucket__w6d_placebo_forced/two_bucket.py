from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if start_bucket not in ("one", "two"):
        raise ValueError("start_bucket must be 'one' or 'two'")

    if start_bucket == "one":
        start = (bucket_one, 0)
    else:
        start = (0, bucket_two)

    def forbidden(state):
        first, second = state
        if start_bucket == "one":
            return first == 0 and second == bucket_two
        return second == 0 and first == bucket_one

    def neighbours(state):
        first, second = state
        candidates = []
        if first < bucket_one:
            candidates.append((bucket_one, second))
        if second < bucket_two:
            candidates.append((first, bucket_two))
        if first > 0:
            candidates.append((0, second))
        if second > 0:
            candidates.append((first, 0))
        pour = min(first, bucket_two - second)
        if pour > 0:
            candidates.append((first - pour, second + pour))
        pour = min(second, bucket_one - first)
        if pour > 0:
            candidates.append((first + pour, second - pour))
        return candidates

    if start[0] == goal:
        return (1, "one", start[1])
    if start[1] == goal:
        return (1, "two", start[0])

    queue = deque([(start, 1)])
    visited = {start}

    while queue:
        state, actions = queue.popleft()
        for candidate in neighbours(state):
            if candidate in visited or forbidden(candidate):
                continue
            first, second = candidate
            if first == goal or second == goal:
                if first == goal:
                    return (actions + 1, "one", second)
                return (actions + 1, "two", first)
            visited.add(candidate)
            queue.append((candidate, actions + 1))

    raise ValueError("no solution")
