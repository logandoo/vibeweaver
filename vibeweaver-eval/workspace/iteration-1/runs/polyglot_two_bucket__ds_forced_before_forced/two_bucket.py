from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    caps = (bucket_one, bucket_two)
    start_index = 0 if start_bucket == "one" else 1
    other_index = 1 - start_index

    forbidden = [0, 0]
    forbidden[other_index] = caps[other_index]
    forbidden = tuple(forbidden)

    start = [0, 0]
    start[start_index] = caps[start_index]
    start = tuple(start)

    if start[start_index] == goal:
        return (1, start_bucket, start[other_index])

    queue = deque([(start, 1)])
    visited = {start}

    while queue:
        state, count = queue.popleft()
        for nxt in neighbors(state, caps):
            if nxt == forbidden or nxt in visited:
                continue
            if nxt[0] == goal:
                return (count + 1, "one", nxt[1])
            if nxt[1] == goal:
                return (count + 1, "two", nxt[0])
            visited.add(nxt)
            queue.append((nxt, count + 1))

    raise ValueError("impossible")


def neighbors(state, caps):
    a, b = state
    cap_one, cap_two = caps
    yield (cap_one, b)
    yield (a, cap_two)
    yield (0, b)
    yield (a, 0)
    pour = min(a, cap_two - b)
    yield (a - pour, b + pour)
    pour = min(b, cap_one - a)
    yield (a + pour, b - pour)
