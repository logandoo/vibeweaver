from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    cap_one, cap_two = bucket_one, bucket_two
    initial = (cap_one, 0) if start_bucket == "one" else (0, cap_two)
    forbidden = (0, cap_two) if start_bucket == "one" else (cap_one, 0)

    if initial == forbidden:
        raise ValueError("Goal is not reachable")
    if initial[0] == goal:
        return (1, "one", initial[1])
    if initial[1] == goal:
        return (1, "two", initial[0])

    def neighbors(state):
        a, b = state
        pour_one_to_two = min(a, cap_two - b)
        pour_two_to_one = min(b, cap_one - a)
        return (
            (cap_one, b),
            (a, cap_two),
            (0, b),
            (a, 0),
            (a - pour_one_to_two, b + pour_one_to_two),
            (a + pour_two_to_one, b - pour_two_to_one),
        )

    seen = {initial}
    queue = deque([(initial, 1)])
    while queue:
        state, actions = queue.popleft()
        for nxt in neighbors(state):
            if nxt == state or nxt == forbidden or nxt in seen:
                continue
            if nxt[0] == goal:
                return (actions + 1, "one", nxt[1])
            if nxt[1] == goal:
                return (actions + 1, "two", nxt[0])
            seen.add(nxt)
            queue.append((nxt, actions + 1))
    raise ValueError("Goal is not reachable")
