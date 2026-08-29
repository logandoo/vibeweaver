from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if start_bucket == "one":
        initial = (bucket_one, 0)
    else:
        initial = (0, bucket_two)

    if initial[0] == goal:
        return (1, "one", initial[1])
    if initial[1] == goal:
        return (1, "two", initial[0])

    def is_allowed(state):
        b1, b2 = state
        if start_bucket == "one":
            return not (b1 == 0 and b2 == bucket_two)
        return not (b2 == 0 and b1 == bucket_one)

    visited = {initial}
    queue = deque([(initial, 1)])

    while queue:
        (b1, b2), moves = queue.popleft()
        next_moves = moves + 1

        states = []

        pour = min(b1, bucket_two - b2)
        if pour > 0:
            states.append((b1 - pour, b2 + pour))

        pour = min(b2, bucket_one - b1)
        if pour > 0:
            states.append((b1 + pour, b2 - pour))

        states.append((bucket_one, b2))
        states.append((b1, bucket_two))
        states.append((0, b2))
        states.append((b1, 0))

        for n1, n2 in states:
            state = (n1, n2)
            if state in visited or not is_allowed(state):
                continue
            if n1 == goal:
                return (next_moves, "one", n2)
            if n2 == goal:
                return (next_moves, "two", n1)
            visited.add(state)
            queue.append((state, next_moves))

    return None
