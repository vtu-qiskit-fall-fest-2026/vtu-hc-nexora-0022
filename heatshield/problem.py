"""The allocation problem: cool the zones that cover the most exposure within the unit budget."""

import itertools

import numpy as np

from .data import DEFAULT_BUDGET, DEFAULT_ZONES


class Problem:
    """x[i] = 1 means zone i receives cooling.

    maximise   sum_i value_i x_i          (value_i = population_i * risk_i / 100)
    subject to sum_i cost_i  x_i <= budget
    """

    def __init__(self, zones=None, budget=DEFAULT_BUDGET):
        self.zones = list(DEFAULT_ZONES if zones is None else zones)
        self.budget = int(budget)
        self.n = len(self.zones)
        self.names = [z.name for z in self.zones]
        self.population = np.array([z.population for z in self.zones], dtype=float)
        self.risk = np.array([z.risk for z in self.zones], dtype=float)
        self.cost = np.array([z.units for z in self.zones], dtype=int)
        self.value = np.array([z.exposure for z in self.zones], dtype=float)
        self.value_norm = self.value / self.value.max()           # rewards scaled to (0, 1]
        # every possible allocation, one row each (2^n x n)
        self.all_x = np.array(list(itertools.product([0, 1], repeat=self.n)))
        self.all_cost = self.all_x @ self.cost
        self.all_value = self.all_x @ self.value

    def cost_of(self, x) -> int:
        return int(self.cost @ np.asarray(x))

    def value_of(self, x) -> float:
        return float(self.value @ np.asarray(x))

    def people_of(self, x) -> int:
        return int(self.population @ np.asarray(x))

    def is_feasible(self, x) -> bool:
        return self.cost_of(x) <= self.budget

    def zone_names(self, x):
        return [self.names[i] for i in range(self.n) if x[i]]
