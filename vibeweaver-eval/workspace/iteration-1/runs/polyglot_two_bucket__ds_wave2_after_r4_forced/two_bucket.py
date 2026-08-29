"""two_bucket — Exercism "two-bucket" exercise.

Measure exactly `goal` liters using two buckets. Each action (fill, empty, or
pour) counts as one move. The first move always fills the starting bucket.

Returns (moves, "one"|"two", liters_in_other_bucket). Raises ValueError when
the goal cannot be reached.
"""

from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    """Return the fewest actions to measure `goal` liters of water.

    A "state" is (liters in bucket one, liters in bucket two).  The search
    starts from the state produced by filling the starting bucket (1 action).
    The state where the starting bucket is empty and the other bucket is full
    is forbidden and never entered.  Each action is fill/empty/pour of a
    single bucket.  Returns (moves, "one"|"two", other) where `other` is the
    liters in the bucket that does not hold the goal.  Raises ValueError if
    the goal is unreachable.
    """
    if start_bucket == "one":
        start_state = (bucket_one, 0)
    else:
        start_state = (0, bucket_two)

    def goal_bucket(state):
        amount_one, amount_two = state
        if amount_one == goal:
            return "one", amount_two
        if amount_two == goal:
            return "two", amount_one
        return None

    def forbidden(state):
        amount_one, amount_two = state
        if start_bucket == "one":
            return amount_one == 0 and amount_two == bucket_two
        return amount_one == bucket_one and amount_two == 0

    def neighbors(state):
        amount_one, amount_two = state
        yield (bucket_one, amount_two)              # fill bucket one
        yield (amount_one, bucket_two)              # fill bucket two
        yield (0, amount_two)                       # empty bucket one
        yield (amount_one, 0)                       # empty bucket two
        pour = min(amount_one, bucket_two - amount_two)
        if pour > 0:
            yield (amount_one - pour, amount_two + pour)   # one -> two
        pour = min(amount_two, bucket_one - amount_one)
        if pour > 0:
            yield (amount_one + pour, amount_two - pour)   # two -> one

    initial_result = goal_bucket(start_state)
    if initial_result is not None:
        bucket, other = initial_result
        return (1, bucket, other)

    seen = {start_state}
    frontier = deque([(start_state, 1)])
    while frontier:
        state, moves = frontier.popleft()
        for nxt in neighbors(state):
            if nxt in seen or forbidden(nxt):
                continue
            result = goal_bucket(nxt)
            if result is not None:
                bucket, other = result
                return (moves + 1, bucket, other)
            seen.add(nxt)
            frontier.append((nxt, moves + 1))

    raise ValueError("No more moves!")
