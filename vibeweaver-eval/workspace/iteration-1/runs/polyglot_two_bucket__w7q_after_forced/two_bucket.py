from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    """Solve the two bucket problem using BFS.

    Returns a tuple: (actions, goal_bucket, other_bucket_amount)
    """
    if goal > max(bucket_one, bucket_two):
        raise ValueError("Goal is larger than both buckets")

    # Check if goal is reachable via GCD
    import math
    if goal % math.gcd(bucket_one, bucket_two) != 0:
        raise ValueError("Goal is not reachable with given bucket sizes")

    # The forbidden state depends on which bucket we start with
    # Rule: "you may not arrive at a state where the initial starting
    # bucket is empty and the other bucket is full"
    if start_bucket == "one":
        forbidden = (0, bucket_two)
    else:
        forbidden = (bucket_one, 0)

    # BFS: (b1, b2) -> number of actions to reach this state
    # First action is always filling the start bucket
    if start_bucket == "one":
        start_state = (bucket_one, 0)
    else:
        start_state = (0, bucket_two)

    actions = 1  # the initial fill counts as one action

    # Check if the initial fill already solves it
    if start_state[0] == goal:
        return (actions, "one", start_state[1])
    if start_state[1] == goal:
        return (actions, "two", start_state[0])

    visited = {start_state}
    queue = deque([(start_state, actions)])

    while queue:
        (b1, b2), step = queue.popleft()
        next_step = step + 1

        # Generate all possible next states
        next_states = []

        # 1. Pour bucket_one -> bucket_two
        pour_amount = min(b1, bucket_two - b2)
        next_states.append((b1 - pour_amount, b2 + pour_amount))

        # 2. Pour bucket_two -> bucket_one
        pour_amount = min(b2, bucket_one - b1)
        next_states.append((b1 + pour_amount, b2 - pour_amount))

        # 3. Empty bucket_one
        next_states.append((0, b2))

        # 4. Empty bucket_two
        next_states.append((b1, 0))

        # 5. Fill bucket_one
        next_states.append((bucket_one, b2))

        # 6. Fill bucket_two
        next_states.append((b1, bucket_two))

        for state in next_states:
            # Skip forbidden state
            if state == forbidden:
                continue
            # Skip visited states
            if state in visited:
                continue

            visited.add(state)

            nb1, nb2 = state
            if nb1 == goal:
                return (next_step, "one", nb2)
            if nb2 == goal:
                return (next_step, "two", nb1)

            queue.append((state, next_step))

    raise ValueError("Goal is not reachable")
