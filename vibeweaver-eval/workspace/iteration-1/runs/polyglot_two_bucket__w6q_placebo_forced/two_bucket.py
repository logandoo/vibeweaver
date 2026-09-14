from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if goal < 0:
        raise ValueError("Goal must be non-negative")

    if goal > max(bucket_one, bucket_two):
        raise ValueError("Goal is larger than either bucket")

    # Determine the forbidden state based on which bucket starts
    if start_bucket == "one":
        # Cannot end up with bucket_one=0 and bucket_two=bucket_two
        forbidden = (0, bucket_two)
    else:
        # Cannot end up with bucket_one=bucket_one and bucket_two=0
        forbidden = (bucket_one, 0)

    # BFS: state = (amount_in_bucket_one, amount_in_bucket_two)
    # Start by filling the designated starting bucket (counts as action 1)
    if start_bucket == "one":
        initial = (bucket_one, 0)
    else:
        initial = (0, bucket_two)

    if initial == (goal, 0) or initial == (0, goal):
        other = initial[1] if initial[0] == goal else initial[0]
        return (1, start_bucket, other)

    visited = {initial}
    queue = deque([(initial, 1)])  # (state, action_count)

    while queue:
        (b1, b2), actions = queue.popleft()

        # Generate all possible next states
        next_states = []

        # Pour bucket_one into bucket_two
        pour1 = min(b1, bucket_two - b2)
        next_states.append((b1 - pour1, b2 + pour1))

        # Pour bucket_two into bucket_one
        pour2 = min(b2, bucket_one - b1)
        next_states.append((b1 + pour2, b2 - pour2))

        # Empty bucket_one
        next_states.append((0, b2))

        # Empty bucket_two
        next_states.append((b1, 0))

        # Fill bucket_one
        next_states.append((bucket_one, b2))

        # Fill bucket_two
        next_states.append((b1, bucket_two))

        for state in next_states:
            if state == forbidden or state in visited:
                continue

            visited.add(state)

            if state[0] == goal:
                return (actions + 1, "one", state[1])
            if state[1] == goal:
                return (actions + 1, "two", state[0])

            queue.append((state, actions + 1))

    raise ValueError("Goal is not reachable")
