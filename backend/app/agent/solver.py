"""
OR-Tools Constraint Solver to find optimal package components.
"""
from typing import Any, List
from decimal import Decimal
from ortools.sat.python import cp_model

def optimize_package(components: List[dict[str, Any]], budget_cap: float) -> List[dict[str, Any]]:
    """
    Selects exactly one component per slot that maximizes rating while staying under budget.
    """
    # Group components by their slot (e.g. "Day 1 - Morning")
    slots = {}
    for c in components:
        slot_key = f"{c['day_index']}_{c['slot']}"
        if slot_key not in slots:
            slots[slot_key] = []
        slots[slot_key].append(c)
        
    model = cp_model.CpModel()
    
    # Create variables
    x = {} # x[(slot_key, comp_id)] = 1 if selected, 0 otherwise
    for slot_key, comps in slots.items():
        for c in comps:
            x[(slot_key, c['component_id'])] = model.NewBoolVar(f"x_{c['component_id']}")
            
    # Constraint 1: Exactly one component per slot
    for slot_key, comps in slots.items():
        model.AddExactlyOne(x[(slot_key, c['component_id'])] for c in comps)
        
    # Constraint 2: Total cost <= budget
    # CP-SAT requires integers. Multiply by 100 to handle cents.
    budget_int = int(budget_cap * 100)
    total_cost = sum(
        int(float(c['price_delta']) * 100) * x[(slot_key, c['component_id'])]
        for slot_key, comps in slots.items()
        for c in comps
    )
    model.Add(total_cost <= budget_int)
    
    # Objective: Maximize total rating (or 0 if none)
    # We'll use 5 if no rating is provided just to have a baseline
    total_rating = sum(
        int(c.get('rating', 5) * 10) * x[(slot_key, c['component_id'])]
        for slot_key, comps in slots.items()
        for c in comps
    )
    model.Maximize(total_rating)
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    selected_components = []
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for slot_key, comps in slots.items():
            for c in comps:
                if solver.Value(x[(slot_key, c['component_id'])]) == 1:
                    selected_components.append(c)
    
    return selected_components
