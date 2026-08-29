from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    capacities = (bucket_one, bucket_two)
    start_index = 0 if start_bucket == "one" else 1

    start_state = [0, 0]
    start_state[start_index] = capacities[start_index]

    forbidden = [0, 0]
    forbidden[1 - start_index] = capacities[1 - start_index]

    def is_goal(state):
        return state[0] == goal or state[1] == goal

    if is_goal(start_state):
        other = start_state[1 - start_index]
        return (1, start_bucket, other)

    visited = {tuple(start_state)}
    queue = deque([(start_state[0], start_state[1], 1)])

    while queue:
        v1, v2, moves = queue.popleft()
        for nxt in next_states(v1, v2, capacities):
            if nxt == tuple(forbidden):
                continue
            if nxt in visited:
                continue
            visited.add(nxt)
            nv1, nv2 = nxt
            if is_goal((nv1, nv2)):
                if nv1 == goal:
                    return (moves + 1, "one", nv2)
                return (moves + 1, "two", nv1)
            queue.append((nv1, nv2, moves + 1))

    raise ValueError("The goal amount cannot be measured.")


def next_states(v1, v2, capacities):
    cap1, cap2 = capacities
    states = []
    if v1 < cap1:
        states.append((cap1, v2))
    if v2 < cap2:
        states.append((v1, cap2))
    if v1 > 0:
        states.append((0, v2))
    if v2 > 0:
        states.append((v1, 0))
    if v1 > 0 and v2 < cap2:
        pour = min(v1, cap2 - v2)
        states.append((v1 - pour, v2 + pour))
    if v2 > 0 and v1 < cap1:
        pour = min(v2, cap1 - v1)
        states.append((v1 + pour, v2 - pour))
    return states
