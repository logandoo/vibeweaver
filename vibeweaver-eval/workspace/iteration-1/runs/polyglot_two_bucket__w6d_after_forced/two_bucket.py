from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    cap_one, cap_two = bucket_one, bucket_two

    if start_bucket == "one":
        initial = (cap_one, 0)
    else:
        initial = (0, cap_two)

    def forbidden(state):
        one, two = state
        if start_bucket == "one":
            return one == 0 and two == cap_two
        return one == cap_one and two == 0

    def successors(state):
        one, two = state
        candidates = [
            (cap_one, two),
            (one, cap_two),
            (0, two),
            (one, 0),
        ]
        transfer = min(one, cap_two - two)
        candidates.append((one - transfer, two + transfer))
        transfer = min(two, cap_one - one)
        candidates.append((one + transfer, two - transfer))
        return candidates

    visited = {initial}
    queue = deque([(initial, 1)])

    while queue:
        state, moves = queue.popleft()
        one, two = state
        if one == goal:
            return (moves, "one", two)
        if two == goal:
            return (moves, "two", one)
        for candidate in successors(state):
            if candidate in visited or forbidden(candidate):
                continue
            visited.add(candidate)
            queue.append((candidate, moves + 1))

    raise ValueError("No solution possible for the given bucket sizes and goal")
