"""Classical baselines used to judge the QAOA result."""

import numpy as np


def exact_best(problem):
    """Exhaustive search over all 2^n allocations. Returns (value, bits). Always optimal."""
    ok = problem.all_cost <= problem.budget
    values = np.where(ok, problem.all_value, -1.0)
    i = int(np.argmax(values))
    if values[i] < 0:
        return 0.0, tuple([0] * problem.n)
    return float(values[i]), tuple(int(v) for v in problem.all_x[i])


def greedy_best(problem):
    """Cool zones in order of exposure per unit until the budget runs out. Returns (value, bits)."""
    order = np.argsort(-problem.value / problem.cost, kind="stable")
    used, x = 0, np.zeros(problem.n, dtype=int)
    for i in order:
        if used + problem.cost[i] <= problem.budget:
            x[i], used = 1, used + problem.cost[i]
    return problem.value_of(x), tuple(int(v) for v in x)
