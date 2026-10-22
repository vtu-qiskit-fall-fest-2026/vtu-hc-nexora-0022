"""Run the trained QAOA circuit on a noisy simulator or on real IBM Quantum hardware.

    python run_hardware.py --backend fake                # noisy simulation of a real IBM chip (no account needed)
    python run_hardware.py --backend ibm_brisbane        # real hardware (needs a saved IBM Quantum account)
    python run_hardware.py --backend least_busy          # real hardware, least busy device

Parameters (beta, gamma) are trained noise-free first, then the circuit is transpiled to the
device's native gates and sampled.  Real-device access: see README ("IBM Quantum account").
"""
import argparse
import json
import numpy as np
from qiskit import transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from heatshield import Problem, solve
from heatshield.qaoa import bits_of, distribution


def get_backend(name, fake_name):
    if name == "fake":
        from qiskit_aer import AerSimulator
        from qiskit_ibm_runtime import fake_provider
        fake = getattr(fake_provider, fake_name)()
        return AerSimulator.from_backend(fake), fake, f"noisy simulation of {fake.name}"
    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService()                       # uses the account saved with save_account()
    backend = service.least_busy(operational=True, simulator=False) if name == "least_busy" \
        else service.backend(name)
    return backend, backend, f"real device {backend.name}"


def sample(backend, target, circuit, shots, real):
    pm = generate_preset_pass_manager(optimization_level=3, backend=target)
    isa = pm.run(circuit)
    if real:
        from qiskit_ibm_runtime import SamplerV2
        sampler = SamplerV2(mode=backend)
    else:
        from qiskit_aer.primitives import SamplerV2
        sampler = SamplerV2.from_backend(backend)
    counts = sampler.run([isa], shots=shots).result()[0].data.meas.get_counts()
    return counts, isa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="fake")
    ap.add_argument("--fake-name", default="FakeSherbrooke")
    ap.add_argument("--layers", type=int, default=2, help="QAOA depth; keep small on hardware")
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="docs/hardware_result.json")
    a = ap.parse_args()

    pb = Problem()
    r = solve(pb, p=a.layers, restarts=6, shots=1024, seed=a.seed)
    backend, target, label = get_backend(a.backend, a.fake_name)
    circuit = r.ansatz.assign_parameters(r.params)
    circuit.measure_all()
    counts, isa = sample(backend, target, circuit, a.shots, real=a.backend != "fake")

    total = sum(counts.values())
    dist = {}
    for bs, c in counts.items():
        x = bits_of(bs.replace(" ", ""))
        dist[x] = dist.get(x, 0) + c / total
    ev, ex = r.exact
    feas = {x: q for x, q in dist.items() if pb.is_feasible(x)}
    p_feas = sum(feas.values())
    mean_feas = sum(q * pb.value_of(x) for x, q in feas.items()) / p_feas if p_feas else 0.0
    best = max(((pb.value_of(x), x) for x in feas), default=(0.0, None))
    ops = isa.count_ops()
    two_q = sum(v for k, v in ops.items() if k in ("cz", "ecr", "cx"))

    ideal = r.stats
    print(f"Device: {label} | layers p={a.layers} | shots={a.shots}")
    print(f"Transpiled circuit: depth {isa.depth()}, two-qubit gates {two_q}")
    print(f"\n{'':<22}{'ideal simulator':>16}{'this run':>12}{'random guess':>14}")
    print(f"{'P(optimal)':<22}{ideal['p_optimal']:>16.4f}{dist.get(ex, 0):>12.4f}{ideal['p_optimal_random']:>14.4f}")
    print(f"{'P(within budget)':<22}{ideal['p_feasible']:>16.3f}{p_feas:>12.3f}{ideal['p_feasible_random']:>14.3f}")
    print(f"{'Mean value (feasible)':<22}{ideal['mean_value_feasible']:>16.1f}{mean_feas:>12.1f}{ideal['mean_value_feasible_random']:>14.1f}")
    print(f"\nBest allocation within budget seen: value {best[0]:.1f} of {ev:.1f} -> "
          f"{', '.join(pb.zone_names(best[1])) if best[1] else 'none'}")

    with open(a.out, "w") as f:
        json.dump({"device": label, "layers": a.layers, "shots": a.shots, "depth": isa.depth(),
                   "two_qubit_gates": two_q, "p_optimal": dist.get(ex, 0), "p_feasible": p_feas,
                   "mean_value_feasible": mean_feas, "best_value": best[0],
                   "ideal": ideal}, f, indent=2, default=float)
    print(f"Saved {a.out}")


if __name__ == "__main__":
    main()
