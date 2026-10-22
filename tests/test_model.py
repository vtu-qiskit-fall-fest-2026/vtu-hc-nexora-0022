import numpy as np
from qiskit.quantum_info import Statevector

from heatshield import Problem, exact_best, greedy_best, pick_penalties, ising_operator, qubo_energy, solve


def test_greedy_never_beats_exact():
    pb = Problem()
    assert greedy_best(pb)[0] <= exact_best(pb)[0] + 1e-9


def test_default_instance_optimum():
    pb = Problem()
    value, x = exact_best(pb)
    assert abs(value - 58.0) < 1e-9
    assert pb.is_feasible(x)


def test_penalties_make_ground_state_optimal():
    pb = Problem()
    l1, l2, ok = pick_penalties(pb, exact_best(pb)[0])
    assert ok


def test_ising_matches_qubo_for_every_allocation():
    pb = Problem()
    l1, l2, _ = pick_penalties(pb, exact_best(pb)[0])
    H, scale = ising_operator(pb, l1, l2)
    for x in pb.all_x:
        idx = int("".join(str(int(b)) for b in x[::-1]), 2)     # qubit 0 = lowest bit
        e = Statevector.from_int(idx, 2 ** pb.n).expectation_value(H).real
        assert abs(e - qubo_energy(pb, x, l1, l2) * scale) < 1e-9


def test_qaoa_beats_random_guessing():
    pb = Problem()
    r = solve(pb, p=2, restarts=3, shots=256, seed=3, maxiter=120)
    assert r.stats["p_optimal"] > r.stats["p_optimal_random"]
    assert r.stats["mean_value_feasible"] > r.stats["mean_value_feasible_random"]
    assert pb.is_feasible(r.best_sample[1])
