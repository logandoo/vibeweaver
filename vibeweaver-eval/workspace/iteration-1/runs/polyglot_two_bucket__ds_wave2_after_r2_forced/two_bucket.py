from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    start = (bucket_one, 0) if start_bucket == "one" else (0, bucket_two)

    queue = deque([(start[0], start[1], 1)])
    visited = {start}

    while queue:
        one, two, actions = queue.popleft()

        if one == goal:
            return actions, "one", two
        if two == goal:
            return actions, "two", one

        for nxt in _successors(one, two, bucket_one, bucket_two):
            if _forbidden(nxt, start_bucket, bucket_one, bucket_two):
                continue
            if nxt in visited:
                continue
            visited.add(nxt)
            queue.append((nxt[0], nxt[1], actions + 1))

    raise ValueError("No solution is possible.")


def _successors(one, two, cap_one, cap_two):
    states = [
        (cap_one, two),
        (one, cap_two),
        (0, two),
        (one, 0),
    ]
    pour = min(one, cap_two - two)
    states.append((one - pour, two + pour))
    pour = min(two, cap_one - one)
    states.append((one + pour, two - pour))
    return states


def _forbidden(state, start_bucket, cap_one, cap_two):
    one, two = state
    if start_bucket == "one":
        return one == 0 and two == cap_two
    return two == 0 and one == cap_one
