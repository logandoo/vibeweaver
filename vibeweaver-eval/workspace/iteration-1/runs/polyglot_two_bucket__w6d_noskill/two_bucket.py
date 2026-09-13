from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    if start_bucket == "one":
        start_name, other_name = "one", "two"
    else:
        start_name, other_name = "two", "one"

    capacities = {"one": bucket_one, "two": bucket_two}
    start_cap = capacities[start_name]
    other_cap = capacities[other_name]

    initial = (start_cap, 0)
    queue = deque([(initial, 1)])
    visited = {initial}

    while queue:
        (s, o), actions = queue.popleft()

        if s == goal:
            return actions, start_name, o
        if o == goal:
            return actions, other_name, s

        for state in _next_states(s, o, start_cap, other_cap):
            if state not in visited:
                visited.add(state)
                queue.append((state, actions + 1))

    raise ValueError("No solution possible")


def _next_states(s, o, start_cap, other_cap):
    candidates = [
        (start_cap, o),
        (s, other_cap),
        (0, o),
        (s, 0),
    ]

    poured_into_other = min(s, other_cap - o)
    candidates.append((s - poured_into_other, o + poured_into_other))

    poured_into_start = min(o, start_cap - s)
    candidates.append((s + poured_into_start, o - poured_into_start))

    return [
        (ns, no)
        for ns, no in candidates
        if not (ns == 0 and no == other_cap)
    ]
