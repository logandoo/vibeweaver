from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    """Return (actions, goal_bucket, other_liters) to measure ``goal`` liters.

    Breadth-first search over reachable (amount_one, amount_two) states gives
    the minimum number of actions.  The first action always fills the bucket
    named by ``start_bucket``.  After any action the state where the starting
    bucket is empty and the other bucket is full is forbidden.
    """
    if start_bucket == "one":
        start = (bucket_one, 0)
    else:
        start = (0, bucket_two)

    def is_forbidden(one, two):
        if start_bucket == "one":
            return one == 0 and two == bucket_two
        return two == 0 and one == bucket_one

    def goal_of(state):
        one, two = state
        if one == goal:
            return ("one", two)
        if two == goal:
            return ("two", one)
        return None

    hit = goal_of(start)
    if hit is not None:
        return (1, hit[0], hit[1])

    seen = {start}
    queue = deque([(start, 1)])

    while queue:
        (one, two), actions = queue.popleft()

        poured = min(one, bucket_two - two)
        poured_back = min(two, bucket_one - one)

        candidates = (
            (bucket_one, two),
            (one, bucket_two),
            (0, two),
            (one, 0),
            (one - poured, two + poured),
            (one + poured_back, two - poured_back),
        )

        for state in candidates:
            if state in seen or is_forbidden(*state):
                continue
            hit = goal_of(state)
            if hit is not None:
                return (actions + 1, hit[0], hit[1])
            seen.add(state)
            queue.append((state, actions + 1))

    raise ValueError("Goal is unreachable with the given buckets")
