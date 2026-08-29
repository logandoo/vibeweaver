from collections import deque


def measure(bucket_one, bucket_two, goal, start_bucket):
    capacities = (bucket_one, bucket_two)
    start_index = 0 if start_bucket == "one" else 1

    initial = [0, 0]
    initial[start_index] = capacities[start_index]

    forbidden = [0, 0]
    forbidden[1 - start_index] = capacities[1 - start_index]

    def possible_next_states(a, b):
        states = [
            (capacities[0], b),
            (a, capacities[1]),
            (0, b),
            (a, 0),
            (max(0, a - (capacities[1] - b)), min(capacities[1], a + b)),
            (min(capacities[0], a + b), max(0, b - (capacities[0] - a))),
        ]
        return states

    queue = deque([(tuple(initial), 1)])
    visited = {tuple(initial)}

    while queue:
        state, actions = queue.popleft()
        if goal in state:
            goal_index = state.index(goal)
            goal_bucket = "one" if goal_index == 0 else "two"
            return actions, goal_bucket, state[1 - goal_index]

        for next_state in possible_next_states(*state):
            if next_state == tuple(forbidden) or next_state in visited:
                continue
            visited.add(next_state)
            queue.append((next_state, actions + 1))

    raise ValueError("No more moves!")
