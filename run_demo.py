"""Command-line demo: QAOA (Qiskit) versus exact search and greedy on the sample campus.

    python run_demo.py [--layers 3] [--shots 1024] [--budget 7]
"""
import argparse
import json

from heatshield import DEFAULT_BUDGET, Problem, solve
from heatshield.qaoa import energy_summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", type=int, default=3, help="QAOA depth p")
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    ap.add_argument("--restarts", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="docs/result.json")
    a = ap.parse_args()

    pb = Problem(budget=a.budget)
    r = solve(pb, p=a.layers, restarts=a.restarts, shots=a.shots, seed=a.seed)
    e_rand, e_min = energy_summary(pb, r.penalties, r.scale)

    print(f"Qubits: {pb.n} (one per zone), QAOA layers p={a.layers}, shots={a.shots}, "
          f"penalties L1={r.penalties[0]}, L2={r.penalties[1]}")
    print(f"<H> after QAOA: {r.energy:.3f}   (random guess {e_rand:.3f}, lowest possible {e_min:.3f})\n")
    print(f"{'Method':<28}{'Value':>8}{'% of best':>11}   Zones cooled")
    ev = r.exact[0]
    for label, (val, x) in [("Exact (exhaustive)", r.exact), ("Greedy value/unit", r.greedy),
                            (f"QAOA (best of {a.shots} shots)", r.best_sample)]:
        print(f"{label:<28}{val:>8.1f}{100 * val / ev:>10.1f}%   {', '.join(pb.zone_names(x)) or 'none'}")
    s = r.stats
    print(f"\nP(a shot is the optimum):      {s['p_optimal']:.4f}   (random guess {s['p_optimal_random']:.4f})")
    print(f"P(a shot is within budget):    {s['p_feasible']:.3f}    (random guess {s['p_feasible_random']:.3f})")
    print(f"Mean value of in-budget shots: {s['mean_value_feasible']:.1f}     (random guess {s['mean_value_feasible_random']:.1f})")

    with open(a.out, "w") as f:
        json.dump({"layers": a.layers, "penalties": list(r.penalties), "scale": r.scale,
                   "exact": list(r.exact), "greedy": list(r.greedy), "qaoa_best": list(r.best_sample),
                   "stats": s, "energy": r.energy,
                   "beta_gamma": [float(v) for v in r.params]}, f, indent=2)


if __name__ == "__main__":
    main()
