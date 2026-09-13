import math
from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if goal > max(bucket_one, bucket_two):
        raise ValueError("Goal is larger than either bucket")

    if goal % math.gcd(bucket_one, bucket_two) != 0:
        raise ValueError("Goal is not reachable with given bucket sizes")

    if goal == bucket_one:
        if start_bucket == "one":
            return (1, "one", 0)
        else:
            return (2, "one", bucket_two)

    if goal == bucket_two:
        if start_bucket == "two":
            return (1, "two", 0)
        else:
            return (2, "two", bucket_one)

    visited = set()
    # State: (bucket_one_liters, bucket_two_liters)
    # Forbidden state: start_bucket is empty and other is full
    if start_bucket == "one":
        forbidden = (0, bucket_two)
    else:
        forbidden = (bucket_one, 0)

    # BFS
    # First action: fill the starting bucket
    if start_bucket == "one":
        initial = (bucket_one, 0)
    else:
        initial = (0, bucket_two)

    if initial == (goal, 0) or initial[0] == goal:
        return (1, "one", initial[1])
    if initial == (0, goal) or initial[1] == goal:
        if start_bucket == "two":
            return (1, "two", initial[0])
        else:
            return (2, "two", initial[0])

    queue = deque()
    queue.append((initial, 1))
    visited.add(initial)

    while queue:
        (b1, b2), steps = queue.popleft()

        # Generate all possible next states
        next_states = []

        # Pour bucket_one into bucket_two
        pour_amount = min(b1, bucket_two - b2)
        next_states.append((b1 - pour_amount, b2 + pour_amount))

        # Pour bucket_two into bucket_one
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
            if state in visited:
                continue
            if state == forbidden:
                continue

            visited.add(state)
            new_steps = steps + 1

            if state[0] == goal:
                return (new_steps, "one", state[1])
            if state[1] == goal:
                return (new_steps, "two", state[0])

            queue.append((state, new_steps))

    raise ValueError("Goal is not reachable")
