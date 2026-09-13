import math
from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if goal < 0:
        raise ValueError("Goal must be non-negative")
    if goal > max(bucket_one, bucket_two):
        raise ValueError("Goal must be reachable")

    # Check if goal is achievable via GCD
    if goal % math.gcd(bucket_one, bucket_two) != 0:
        raise ValueError("Goal is not reachable")

    # Determine the forbidden state
    # Rule: "After an action, you may not arrive at a state where the initial
    # starting bucket is empty and the other bucket is full."
    if start_bucket == "one":
        forbidden = (0, bucket_two)
    else:
        forbidden = (bucket_one, 0)

    # BFS: state = (liters in bucket_one, liters in bucket_two)
    if start_bucket == "one":
        start = (bucket_one, 0)
    else:
        start = (0, bucket_two)

    if start == forbidden:
        raise ValueError("Start state is forbidden")

    if start[0] == goal:
        return (1, "one", start[1])
    if start[1] == goal:
        return (1, "two", start[0])

    visited = {start}
    queue = deque([(start, 1)])

    while queue:
        (b1, b2), actions = queue.popleft()

        # Generate all possible next states
        next_states = []

        # Pour bucket_one into bucket_two
        pour = min(b1, bucket_two - b2)
        next_states.append((b1 - pour, b2 + pour))

        # Pour bucket_two into bucket_one
        pour = min(b2, bucket_one - b1)
        next_states.append((b1 + pour, b2 - pour))

        # Empty bucket_one
        next_states.append((0, b2))

        # Empty bucket_two
        next_states.append((b1, 0))

        # Fill bucket_one
        next_states.append((bucket_one, b2))

        # Fill bucket_two
        next_states.append((b1, bucket_two))

        for nb1, nb2 in next_states:
            if (nb1, nb2) == forbidden:
                continue
            if (nb1, nb2) in visited:
                continue

            new_actions = actions + 1

            if nb1 == goal:
                return (new_actions, "one", nb2)
            if nb2 == goal:
                return (new_actions, "two", nb1)

            visited.add((nb1, nb2))
            queue.append(((nb1, nb2), new_actions))

    raise ValueError("Goal is not reachable")
