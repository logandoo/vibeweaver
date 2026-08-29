from collections import deque
from math import gcd


def measure(bucket_one, bucket_two, goal, start_bucket):
    if start_bucket not in ("one", "two"):
        raise ValueError("start_bucket must be 'one' or 'two'")

    if goal > max(bucket_one, bucket_two):
        raise ValueError("goal is larger than both buckets")

    if goal % gcd(bucket_one, bucket_two) != 0:
        raise ValueError("goal is impossible to measure with these buckets")

    def is_forbidden(one, two):
        if start_bucket == "one":
            return one == 0 and two == bucket_two
        return two == 0 and one == bucket_one

    initial = (0, 0)
    queue = deque([(initial, 0)])
    visited = {initial}

    while queue:
        (one, two), actions = queue.popleft()

        candidates = (
            (bucket_one, two),
            (one, bucket_two),
            (0, two),
            (one, 0),
            (one - min(one, bucket_two - two), two + min(one, bucket_two - two)),
            (one + min(two, bucket_one - one), two - min(two, bucket_one - one)),
        )

        for n_one, n_two in candidates:
            if (n_one, n_two) in visited:
                continue
            if is_forbidden(n_one, n_two):
                continue

            steps = actions + 1

            if n_one == goal:
                return (steps, "one", n_two)
            if n_two == goal:
                return (steps, "two", n_one)

            visited.add((n_one, n_two))
            queue.append(((n_one, n_two), steps))

    raise ValueError("goal is impossible to measure with these buckets")
