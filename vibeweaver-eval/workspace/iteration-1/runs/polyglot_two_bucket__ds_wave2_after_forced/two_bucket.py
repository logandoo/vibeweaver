from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    """Determine how many actions are required to measure ``goal`` liters.

    Returns a tuple ``(actions, goal_bucket, other_bucket_liters)``:

    - ``actions``: total number of actions, including the first fill of the
      starting bucket;
    - ``goal_bucket``: ``"one"`` or ``"two"`` — the bucket holding the goal;
    - ``other_bucket_liters``: liters left in the other bucket.

    Raises ``ValueError`` when the goal cannot be measured with the two given
    buckets.

    The search is a breadth-first search over bucket states ``(one, two)``
    with every action costing one move, which guarantees the fewest actions.
    The first action is always filling the starting bucket.  States in which
    the starting bucket is empty and the other bucket is full are illegal and
    are never entered.
    """
    start_is_one = start_bucket == "one"

    def is_forbidden(one, two):
        # May not arrive at: starting bucket empty and the other bucket full.
        if start_is_one:
            return one == 0 and two == bucket_two
        return two == 0 and one == bucket_one

    def successors(one, two):
        moves = [
            (bucket_one, two),            # fill bucket one
            (one, bucket_two),            # fill bucket two
            (0, two),                     # empty bucket one
            (one, 0),                     # empty bucket two
        ]
        pour = min(one, bucket_two - two)
        moves.append((one - pour, two + pour))    # pour one into two
        pour = min(two, bucket_one - one)
        moves.append((one + pour, two - pour))    # pour two into one
        return moves

    start = (bucket_one, 0) if start_is_one else (0, bucket_two)

    queue = deque([(start[0], start[1], 1)])
    visited = {start}

    while queue:
        one, two, steps = queue.popleft()
        if one == goal:
            return (steps, "one", two)
        if two == goal:
            return (steps, "two", one)
        for nxt in successors(one, two):
            if nxt in visited or is_forbidden(nxt[0], nxt[1]):
                continue
            visited.add(nxt)
            queue.append((nxt[0], nxt[1], steps + 1))

    raise ValueError("goal is not reachable")
