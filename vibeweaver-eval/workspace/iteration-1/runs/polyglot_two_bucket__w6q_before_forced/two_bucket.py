import math
from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if goal < 0:
        raise ValueError("Goal must be non-negative")
    if goal > max(bucket_one, bucket_two):
        raise ValueError("Goal is unreachable")
    if goal % math.gcd(bucket_one, bucket_two) != 0:
        raise ValueError("Goal is unreachable")

    if start_bucket == "one":
        fill_first = (bucket_one, 0)
        forbidden = (0, bucket_two)
    elif start_bucket == "two":
        fill_first = (0, bucket_two)
        forbidden = (bucket_one, 0)
    else:
        raise ValueError("start_bucket must be 'one' or 'two'")

    # Check if the first fill already achieves the goal
    if start_bucket == "one" and fill_first[0] == goal:
        return (1, "one", fill_first[1])
    if start_bucket == "two" and fill_first[1] == goal:
        return (1, "two", fill_first[0])

    visited = set()
    visited.add(fill_first)
    visited.add((0, 0))
    queue = deque()
    queue.append((fill_first, 1))

    while queue:
        (b1, b2), actions = queue.popleft()

        next_states = []

        # Pour bucket one into bucket two
        pour = min(b1, bucket_two - b2)
        next_states.append((b1 - pour, b2 + pour))

        # Pour bucket two into bucket one
        pour = min(b2, bucket_one - b1)
        next_states.append((b1 + pour, b2 - pour))

        # Empty bucket one
        next_states.append((0, b2))

        # Empty bucket two
        next_states.append((b1, 0))

        # Fill bucket one
        next_states.append((bucket_one, b2))

        # Fill bucket two
        next_states.append((b1, bucket_two))

        for ns in next_states:
            if ns == forbidden:
                continue
            if ns in visited:
                continue
            visited.add(ns)

            if ns[0] == goal:
                return (actions + 1, "one", ns[1])
            if ns[1] == goal:
                return (actions + 1, "two", ns[0])

            queue.append((ns, actions + 1))

    raise ValueError("Goal is unreachable")
