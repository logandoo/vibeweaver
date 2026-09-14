from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if bucket_one <= 0 or bucket_two <= 0:
        raise ValueError("bucket sizes must be positive integers")

    if goal <= 0:
        raise ValueError("goal must be a positive integer")

    if goal > max(bucket_one, bucket_two):
        raise ValueError("goal cannot exceed the largest bucket")

    capacities = (bucket_one, bucket_two)
    start = 0 if start_bucket == "one" else 1

    initial = [0, 0]
    initial[start] = capacities[start]
    initial = (initial[0], initial[1])

    if initial[0] == goal:
        return (1, "one", initial[1])
    if initial[1] == goal:
        return (1, "two", initial[0])

    visited = {initial}
    queue = deque([(initial, 1)])

    while queue:
        (amount_one, amount_two), steps = queue.popleft()

        for next_one, next_two in _next_states(
            amount_one, amount_two, bucket_one, bucket_two
        ):
            if (next_one, next_two) in visited:
                continue

            if start == 0:
                if next_one == 0 and next_two == bucket_two:
                    continue
            else:
                if next_two == 0 and next_one == bucket_one:
                    continue

            if next_one == goal:
                return (steps + 1, "one", next_two)
            if next_two == goal:
                return (steps + 1, "two", next_one)

            visited.add((next_one, next_two))
            queue.append(((next_one, next_two), steps + 1))

    raise ValueError("goal cannot be measured with these buckets")


def _next_states(amount_one, amount_two, bucket_one, bucket_two):
    yield (bucket_one, amount_two)
    yield (amount_one, bucket_two)
    yield (0, amount_two)
    yield (amount_one, 0)

    poured = min(amount_one, bucket_two - amount_two)
    yield (amount_one - poured, amount_two + poured)

    poured = min(amount_two, bucket_one - amount_one)
    yield (amount_one + poured, amount_two - poured)
