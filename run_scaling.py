"""Scaling study: how do QAOA, greedy and random guessing behave as the number of zones grows?

    python run_scaling.py            # ~5 minutes; writes docs/scaling.json and docs/scaling.png
"""
import json
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from heatshield import Problem, Zone, solve

SIZES = [4, 6, 8, 10, 12]
INSTANCES = 3


def random_problem(n, rng):
    zones = [Zone(f"Z{i + 1}", int(rng.integers(4, 19)) * 50, int(rng.integers(1, 6)), int(rng.integers(1, 5)))
             for i in range(n)]
    budget = max(3, int(round(0.4 * sum(z.units for z in zones))))
    return Problem(zones, budget)


def main():
    rng = np.random.default_rng(2026)
    rows = []
    for n in SIZES:
        for k in range(INSTANCES):
            pb = random_problem(n, rng)
            t0 = time.time()
            r = solve(pb, p=2, restarts=3, shots=1024, seed=10 + k, maxiter=150)
            dt = time.time() - t0
            ev = r.exact[0]
            rows.append({"zones": n, "instance": k, "penalties_ok": r.penalties_ok,
                         "greedy_ratio": r.greedy[0] / ev, "qaoa_ratio": r.best_sample[0] / ev,
                         "p_optimal": r.stats["p_optimal"], "p_random": r.stats["p_optimal_random"],
                         "mean_feasible_ratio": r.stats["mean_value_feasible"] / ev,
                         "mean_feasible_ratio_random": r.stats["mean_value_feasible_random"] / ev,
                         "qaoa_seconds": dt})
            print(f"n={n:2d} #{k}  greedy {rows[-1]['greedy_ratio']:.3f}  QAOA(best of 1024) {rows[-1]['qaoa_ratio']:.3f}  "
                  f"P(opt) {r.stats['p_optimal']:.4f} vs random {r.stats['p_optimal_random']:.4f}  {dt:.0f}s", flush=True)
    json.dump(rows, open("docs/scaling.json", "w"), indent=2)

    def mean(key, n):
        return float(np.mean([r[key] for r in rows if r["zones"] == n]))

    TEAL, AMBER, SLATE = "#0b7c88", "#c4701b", "#56667c"
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    ax[0].plot(SIZES, [mean("greedy_ratio", n) for n in SIZES], "-o", color=AMBER, label="Greedy")
    ax[0].plot(SIZES, [mean("qaoa_ratio", n) for n in SIZES], "-o", color=TEAL, label="QAOA, best of 1024 shots")
    ax[0].set_ylim(0.8, 1.02)
    ax[0].set_title("Quality of best allocation (1.0 = optimal)", fontsize=10)
    ax[1].semilogy(SIZES, [mean("p_optimal", n) for n in SIZES], "-o", color=TEAL, label="QAOA")
    ax[1].semilogy(SIZES, [mean("p_random", n) for n in SIZES], "--o", color=SLATE, label="Random guess")
    ax[1].set_title("Chance a single shot is the optimum", fontsize=10)
    ax[2].plot(SIZES, [mean("mean_feasible_ratio", n) for n in SIZES], "-o", color=TEAL, label="QAOA shots")
    ax[2].plot(SIZES, [mean("mean_feasible_ratio_random", n) for n in SIZES], "--o", color=SLATE, label="Random guess")
    ax[2].set_title("Average value of shots within budget (share of optimum)", fontsize=10)
    for a in ax:
        a.set_xlabel("number of zones (qubits)")
        a.set_xticks(SIZES)
        a.legend(fontsize=8, frameon=False)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig("docs/scaling.png", dpi=160)
    print("Saved docs/scaling.json and docs/scaling.png")


if __name__ == "__main__":
    main()
