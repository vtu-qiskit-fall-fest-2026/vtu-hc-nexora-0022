"""QUBO with unbalanced penalisation, and its conversion to an Ising Hamiltonian for Qiskit.

Let h = B - sum_i c_i x_i be the spare budget (h < 0 means the budget is broken).

    f(x) = - sum_i (v_i / v_max) x_i  +  ( -L1 * h + L2 * h^2 )

No slack qubits are needed: the penalty is zero-ish for small spare budget and grows
quadratically when the budget is exceeded.  Reference: Montanez-Barrera et al.,
"Unbalanced penalization", arXiv:2211.13914.
With x = (1 - Z) / 2 the function becomes  const + sum h_i Z_i + sum J_ij Z_i Z_j.
"""
import numpy as np
from qiskit.quantum_info import SparsePauliOp

# (L1, L2) pairs tried in order; the first one whose lowest-energy state is the true optimum wins
PENALTY_CANDIDATES = [(0.2, 0.15), (0.2, 0.2), (0.2, 0.3), (0.3, 0.3), (0.1, 0.3), (0.1, 0.6),
                      (0.4, 0.6), (0.0, 0.6), (0.5, 1.0), (0.5, 2.0), (0.5, 4.0)]


def qubo_energy(problem, x, l1, l2):
    h = problem.budget - problem.cost_of(x)
    return float(-(problem.value_norm @ np.asarray(x)) - l1 * h + l2 * h * h)


def energies(problem, l1, l2):
    """QUBO energy of every allocation, same order as problem.all_x."""
    h = problem.budget - problem.all_x @ problem.cost
    return -(problem.all_x @ problem.value_norm) - l1 * h + l2 * h * h


def pick_penalties(problem, optimum_value):
    """First (L1, L2) whose QUBO ground state is the exact optimum (checked by enumeration)."""
    for l1, l2 in PENALTY_CANDIDATES:
        e = energies(problem, l1, l2)
        g = problem.all_x[int(np.argmin(e))]
        if problem.is_feasible(g) and abs(problem.value_of(g) - optimum_value) < 1e-9:
            return l1, l2, True
    l1, l2 = PENALTY_CANDIDATES[-1]
    return l1, l2, False


def ising_operator(problem, l1, l2):
    """Return (SparsePauliOp, scale). Energies are rescaled to a spread of 10 so that
    QAOA angles stay in a friendly range. Qiskit labels have qubit 0 on the right."""
    n, B, c = problem.n, problem.budget, problem.cost
    a = -problem.value_norm + l1 * c + l2 * (c ** 2 - 2 * B * c)      # linear terms in x_i
    const = -l1 * B + l2 * B ** 2
    z_lin = np.zeros(n)
    terms = []
    for i in range(n):
        const += a[i] / 2                    # a*x = a/2 - (a/2) Z
        z_lin[i] -= a[i] / 2
    for i in range(n):
        for j in range(i + 1, n):
            b = 2 * l2 * c[i] * c[j]         # b*x_i*x_j = b/4 (1 - Z_i - Z_j + Z_i Z_j)
            const += b / 4
            z_lin[i] -= b / 4
            z_lin[j] -= b / 4
            lab = ["I"] * n
            lab[i] = lab[j] = "Z"
            terms.append(("".join(lab[::-1]), b / 4))
    for i in range(n):
        lab = ["I"] * n
        lab[i] = "Z"
        terms.append(("".join(lab[::-1]), z_lin[i]))
    terms.append(("I" * n, const))
    e = energies(problem, l1, l2)
    scale = 10.0 / (e.max() - e.min())
    return SparsePauliOp.from_list(terms).simplify() * scale, scale
