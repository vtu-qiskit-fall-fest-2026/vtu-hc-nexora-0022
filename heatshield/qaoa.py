"""QAOA with Qiskit: circuit, classical optimisation of the angles, readout statistics."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import minimize

from qiskit.circuit.library import QAOAAnsatz
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import Statevector

from .classical import exact_best, greedy_best
from .hamiltonian import energies, ising_operator, pick_penalties


def bits_of(bitstring: str) -> Tuple[int, ...]:
    """Qiskit bitstring (qubit 0 on the right) -> (x_0, x_1, ...)."""
    return tuple(int(ch) for ch in bitstring[::-1])


def distribution(ansatz, params) -> Dict[Tuple[int, ...], float]:
    """Exact measurement probabilities of the bound circuit, keyed by (x_0, ..., x_{n-1})."""
    state = Statevector(ansatz.assign_parameters(params))
    return {bits_of(bs): p for bs, p in state.probabilities_dict().items()}


def energy_summary(problem, penalties, scale):
    """(mean energy of a random guess, lowest possible energy), in the circuit's scaled units."""
    e = energies(problem, *penalties) * scale
    return float(e.mean()), float(e.min())


@dataclass
class Solution:
    problem: object
    penalties: Tuple[float, float]
    penalties_ok: bool
    scale: float
    hamiltonian: object
    ansatz: object                      # QAOA circuit (H, then cost and mixer layers), parameters unbound
    params: np.ndarray                  # [beta_1..beta_p, gamma_1..gamma_p]
    energy: float                       # expected energy <H> after training
    probs: Dict[Tuple[int, ...], float]
    history: List[float]                # best energy seen so far, per circuit evaluation
    exact: Tuple[float, tuple]
    greedy: Tuple[float, tuple]
    best_sample: Tuple[float, tuple]    # best allocation within budget among the sampled shots
    shots: int
    layers: int
    stats: dict = field(default_factory=dict)


def solve(problem, p=3, restarts=8, shots=1024, seed=7, maxiter=300) -> Solution:
    """Train a p-layer QAOA circuit and compare it with exact search, greedy search and random guessing."""
    ex = exact_best(problem)
    gr = greedy_best(problem)
    l1, l2, ok = pick_penalties(problem, ex[0])
    H, scale = ising_operator(problem, l1, l2)

    ansatz = QAOAAnsatz(cost_operator=H, reps=p).decompose(reps=2)
    estimator = StatevectorEstimator()
    rng = np.random.default_rng(seed)
    history: List[float] = []
    running = [np.inf]

    def objective(theta):
        e = float(estimator.run([(ansatz, H, theta)]).result()[0].data.evs)
        running[0] = min(running[0], e)
        history.append(running[0])
        return e

    best = None
    for _ in range(restarts):
        theta0 = np.concatenate([rng.uniform(0.1, 1.5, p), rng.uniform(0.05, 1.2, p)])
        res = minimize(objective, theta0, method="COBYLA", options={"maxiter": maxiter})
        if best is None or res.fun < best.fun:
            best = res
    params = np.array(best.x)
    probs = distribution(ansatz, params)

    # readout statistics (exact probabilities) and random-guess reference
    feas = {x: q for x, q in probs.items() if problem.is_feasible(x)}
    p_feas = sum(feas.values())
    ok_mask = problem.all_cost <= problem.budget
    stats = {
        "p_optimal": probs.get(ex[1], 0.0),
        "p_optimal_random": 1.0 / 2 ** problem.n,
        "p_feasible": p_feas,
        "p_feasible_random": float(ok_mask.mean()),
        "mean_value_feasible": sum(q * problem.value_of(x) for x, q in feas.items()) / p_feas if p_feas else 0.0,
        "mean_value_feasible_random": float(problem.all_value[ok_mask].mean()) if ok_mask.any() else 0.0,
    }

    # finite-shot readout, as on hardware: keep the best allocation within budget
    srng = np.random.default_rng(seed)
    keys = list(probs.keys())
    pr = np.array([probs[k] for k in keys])
    draws = srng.choice(len(keys), size=shots, p=pr / pr.sum())
    best_sample = (0.0, tuple([0] * problem.n))
    for d in draws:
        x = keys[d]
        if problem.is_feasible(x) and problem.value_of(x) > best_sample[0]:
            best_sample = (problem.value_of(x), x)

    return Solution(problem, (l1, l2), ok, scale, H, ansatz, params, float(best.fun), probs, history,
                    ex, gr, best_sample, shots, p, stats)
