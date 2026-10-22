"""HEATSHIELD-Q demo app (Streamlit). Every number here is computed with Qiskit.

    streamlit run app.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from heatshield import Problem, Zone, DEFAULT_ZONES, DEFAULT_BUDGET, solve
from heatshield.qaoa import energy_summary

st.set_page_config(page_title="HEATSHIELD-Q", page_icon=None, layout="wide")

TEAL, SLATE, AMBER, RED = "#0b7c88", "#2f3f5c", "#c4701b", "#c0463a"

st.markdown(
    "<h1 style='margin-bottom:0'>HEATSHIELD-Q</h1>"
    "<p style='color:#56667c;margin-top:2px'>Quantum allocation of limited campus cooling resources "
    "with QAOA (Qiskit) compared against classical methods.</p>", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def run_solver(zone_rows, budget, layers, restarts, shots, seed):
    problem = Problem([Zone(*row) for row in zone_rows], budget)
    return solve(problem, p=layers, restarts=restarts, shots=shots, seed=seed)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.subheader("Scenario")
    budget = st.slider("Cooling units available", 3, 12, DEFAULT_BUDGET)
    st.subheader("QAOA settings")
    layers = st.select_slider("Layers (p)", options=[1, 2, 3, 4], value=3)
    restarts = st.slider("Optimiser restarts", 1, 10, 4)
    shots = st.select_slider("Measurement shots", options=[256, 512, 1024, 2048], value=1024)
    seed = st.number_input("Random seed", 0, 9999, 7)
    st.caption("The circuit is simulated exactly with Qiskit's statevector primitives (6 qubits).")

with st.expander("Edit zones (people, heat risk, units needed)"):
    table = pd.DataFrame([{"Zone": z.name, "People": z.population, "Heat risk (1-5)": z.risk,
                           "Units needed": z.units} for z in DEFAULT_ZONES])
    edited = st.data_editor(
        table, hide_index=True, width="stretch", disabled=["Zone"],
        column_config={"People": st.column_config.NumberColumn(min_value=50, max_value=5000, step=50),
                       "Heat risk (1-5)": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
                       "Units needed": st.column_config.NumberColumn(min_value=1, max_value=6, step=1)})

rows = tuple((str(r["Zone"]), int(r["People"]), int(r["Heat risk (1-5)"]), int(r["Units needed"]))
             for _, r in edited.iterrows())
with st.spinner("Training the QAOA circuit..."):
    res = run_solver(rows, int(budget), int(layers), int(restarts), int(shots), int(seed))
pb = res.problem
ev, ex = res.exact
gv, gx = res.greedy
qv, qx = res.best_sample

# ------------------------------------------------------------------ comparison
st.subheader("Quantum versus classical")
cols = st.columns(3)
for col, title, v, x, note in [
        (cols[0], "Exact search", ev, ex, "all 2^n combinations"),
        (cols[1], "Greedy (value per unit)", gv, gx, "fast heuristic"),
        (cols[2], f"QAOA, best of {res.shots} shots", qv, qx, f"{layers}-layer Qiskit circuit")]:
    with col:
        with st.container(border=True):
            st.markdown(f"**{title}**  \n<span style='color:#56667c'>{note}</span>", unsafe_allow_html=True)
            st.metric("Exposure covered", f"{v:.1f}")
            st.caption(f"{100 * v / ev:.1f}% of the best possible")
            st.write(f"{pb.people_of(x):,} people · {pb.cost_of(x)}/{pb.budget} units")
            st.write(", ".join(pb.zone_names(x)) or "No zone cooled")

s = res.stats
m = st.columns(4)
e_rand, e_min = energy_summary(pb, res.penalties, res.scale)
for col, label, val, note in [
        (m[0], "Shots returning the optimum", f"{100 * s['p_optimal']:.1f}%", f"random guess {100 * s['p_optimal_random']:.1f}%"),
        (m[1], "Mean value, feasible shots", f"{s['mean_value_feasible']:.1f}", f"random guess {s['mean_value_feasible_random']:.1f}"),
        (m[2], "Shots within budget", f"{100 * s['p_feasible']:.0f}%", f"random guess {100 * s['p_feasible_random']:.0f}%"),
        (m[3], "Final <H>", f"{res.energy:.2f}", f"random {e_rand:.2f} · lowest {e_min:.2f}")]:
    col.metric(label, val)
    col.caption(note)

# ------------------------------------------------------------------ charts
c1, c2 = st.columns(2)
with c1:
    st.subheader("What the circuit measures")
    top = sorted(res.probs.items(), key=lambda kv: -kv[1])[:10][::-1]
    fig, ax = plt.subplots(figsize=(6, 3.8))
    labels = ["·".join(n[:2].upper() for n in pb.zone_names(x)) or "none" for x, _ in top]
    colors = [TEAL if x == ex else (TEAL if pb.is_feasible(x) else RED) for x, _ in top]
    alphas = [1 if x == ex else (0.45 if pb.is_feasible(x) else 0.85) for x, _ in top]
    ax.barh(range(len(top)), [p for _, p in top], color=colors)
    for patch, a in zip(ax.patches, alphas):
        patch.set_alpha(a)
    ax.set_yticks(range(len(top)), labels, fontsize=8)
    ax.axvline(1 / 2 ** pb.n, color="#56667c", ls="--", lw=1)
    ax.set_xlabel("probability  (dashed = random guess)")
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig, clear_figure=True)
    st.caption("Dark teal: optimal. Light teal: within budget. Red: over budget.")
with c2:
    st.subheader("Training")
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.plot(res.history, color=TEAL, lw=2)
    ax.axhline(e_rand, color="#56667c", ls="--", lw=1)
    ax.axhline(e_min, color="#56667c", ls="--", lw=1)
    ax.text(len(res.history) * 0.98, e_rand, "random guess", ha="right", va="bottom", fontsize=8, color="#56667c")
    ax.text(len(res.history) * 0.98, e_min, "lowest possible", ha="right", va="top", fontsize=8, color="#56667c")
    ax.set_xlabel("circuit evaluations")
    ax.set_ylabel("best <H> so far")
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig, clear_figure=True)
    st.caption("COBYLA tunes the angles from several random starts; the curve keeps the best value seen.")

# ------------------------------------------------------------------ internals
with st.expander("Circuit and Hamiltonian"):
    fig = res.ansatz.draw("mpl", fold=-1, scale=0.7)
    st.pyplot(fig, clear_figure=True)
    st.write(f"Optimised angles: " + ", ".join(
        f"{'beta' if i < layers else 'gamma'}{i % layers + 1} = {v:.3f}" for i, v in enumerate(res.params)))
    terms = pd.DataFrame({"Pauli term (qubit 0 on the right)": res.hamiltonian.paulis.to_labels(),
                          "Coefficient": [float(c.real) for c in res.hamiltonian.coeffs]})
    st.dataframe(terms, hide_index=True, width="stretch")
    st.caption(f"Penalty weights L1={res.penalties[0]}, L2={res.penalties[1]} "
               f"(chosen so the lowest-energy state is the true optimum).")

path = os.path.join(os.path.dirname(__file__), "docs", "hardware_result.json")
if os.path.exists(path):
    with st.expander("Noisy device / real hardware run"):
        h = json.load(open(path))
        st.write(f"**{h['device']}** · {h['layers']} layers · {h['shots']} shots · transpiled depth "
                 f"{h['depth']} · {h['two_qubit_gates']} two-qubit gates")
        ideal = h["ideal"]
        st.dataframe(pd.DataFrame({
            "": ["P(optimal)", "P(within budget)", "Mean value (feasible)"],
            "Ideal simulator": [ideal["p_optimal"], ideal["p_feasible"], ideal["mean_value_feasible"]],
            "This run": [h["p_optimal"], h["p_feasible"], h["mean_value_feasible"]],
            "Random guess": [ideal["p_optimal_random"], ideal["p_feasible_random"],
                             ideal["mean_value_feasible_random"]]}).round(4),
            hide_index=True, width="stretch")
        st.caption("Results for the default scenario, produced by run_hardware.py.")
