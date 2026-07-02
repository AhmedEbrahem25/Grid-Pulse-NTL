"""Step 1 - Energy balance (mass balance).

measured_loss_w = power out of the transformer - sum of registered (metered) load.
A large positive value means energy is leaving that nobody pays for: either
natural technical loss (step 2 explains it) or theft.
"""


def measured_loss_w(edge_total_active_w: float, registered_load_w: float) -> float:
    return edge_total_active_w - registered_load_w
