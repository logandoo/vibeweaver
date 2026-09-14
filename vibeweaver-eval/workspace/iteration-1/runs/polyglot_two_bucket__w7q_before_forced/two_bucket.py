import math
from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if goal > max(bucket_one, bucket_two):
        raise ValueError("Goal is larger than both buckets")

    if goal % math.gcd(bucket_one, bucket_two) != 0:
        raise ValueError("Goal is not reachable with given bucket sizes")

    # State: (liters_in_bucket_one, liters_in_bucket_two)
    # Start by filling the designated start bucket (counts as action 1)
    if start_bucket == "one":
        start_state = (bucket_one, 0)
    else:
        start_state = (0, bucket_two)

    # Forbidden state: start bucket empty, other bucket full
    if start_bucket == "one":
        forbidden = (0, bucket_two)
    else:
        forbidden = (bucket_one, 0)

    # Check if the start state already meets the goal
    if start_state[0] == goal:
        return (1, "one", start_state[1])
    if start_state[1] == goal:
        return (1, "two", start_state[0])

    # BFS
    visited = set()
    visited.add(start_state)
    queue = deque()
    queue.append((start_state, 1))

    while queue:
        (b1, b2), actions = queue.popleft()

        # Generate all possible next states
        next_states = []

        # Pour bucket_one -> bucket_two
        pour_amount = min(b1, bucket_two - b2)
        next_states.append((b1 - pour_amount, b2 + pour_amount))

        # Pour bucket_two -> bucket_one
        pour_amount = min(b2, bucket_one - b1)
        next_states.append((b1 + pour_amount, b2 - pour_amount))

        # Empty bucket_one
        next_states.append((0, b2))

        # Empty bucket_two
        next_states.append((b1, 0))

        # Fill bucket_one
        next_states.append((bucket_one, b2))

        # Fill bucket_two
        next_states.append((b1, bucket_two))

        for state in next_states:
            if state == forbidden:
                continue
            if state in visited:
                continue
            visited.add(state)

            nb1, nb2 = state
            new_actions = actions + 1

            if nb1 == goal:
                return (new_actions, "one", nb2)
            if nb2 == goal:
                return (new_actions, "two", nb1)

            queue.append((state, new_actions))

    raise ValueError("Goal is not reachable")
