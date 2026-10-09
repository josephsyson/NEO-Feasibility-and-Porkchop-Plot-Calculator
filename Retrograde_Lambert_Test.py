import math
import numpy as np
from scipy.integrate import solve_ivp

from Main_Orbital import retrograde, z_Solver_Retrograde, Lambert_Langrange_Solver


def solve_lambert_retrograde(
    r1, r2, tof_days, mu
):  # Runs the Lambert Solver for a retrograde orbit. Identical to the prograde version except it uses the retrograde transfer angle and the retrograde z solver.
    r1_norm = np.linalg.norm(r1)
    r2_norm = np.linalg.norm(r2)
    cos_ratio = np.dot(r1, r2) / (r1_norm * r2_norm)
    dtheta = retrograde(cos_ratio, np.cross(r1, r2))
    A = math.sin(dtheta) * math.sqrt(r1_norm * r2_norm / (1 - math.cos(dtheta)))
    Y = z_Solver_Retrograde(r1_norm, r2_norm, A, tof_days, mu)
    return Lambert_Langrange_Solver(r1_norm, r2_norm, r1, r2, mu, Y, A)


def propagate(r0, v0, tof_s, mu):
    # Independent two-body propagation (no Lambert code involved).

    def rhs(
        t, s
    ):  # Defines the right-hand side of the differential equation for the two-body problem. The state vector is [x, y, z, vx, vy, vz].
        r = s[:3]  # Position vector
        return np.concatenate(
            [s[3:], -mu * r / np.linalg.norm(r) ** 3]
        )  # Creates a column vector of the velocity and acceleration components of the state vector stored as [vx, vy, vz, ax, ay, az].

    sol = solve_ivp(rhs, [0, tof_s], np.concatenate([r0, v0]), rtol=1e-11, atol=1e-11)
    return sol.y[
        :3, -1
    ]  # Uses solve_ivp from scipy to utilize the Runge-Kutta method to solve the IVP for the two-body problem from t=0 to t=tof_s. Starts at the initial position and velocity and has a tolerance of 1e-11. The final position vector is returned.


def test_round_trip_retrograde():  # Using Earth as the central body, calculates the initial velocity vector v1 using my coded retrograde Lambert solver. Propagates the initial position and velocity vectors using the two-body problem to get the final position vector r2_prop after an hour. Calculates the error between the propagated final position vector and the target final position vector. The round trip alone passes for any valid orbit, so it also checks the sign of the angular momentum h = r1 x v1 to confirm the orbit really goes the opposite way around.
    mu_earth = 398600.0  # Curtis example 5.2 values
    r1 = np.array([5000.0, 10000.0, 2100.0])
    r2 = np.array([-14600.0, 2500.0, 7000.0])
    tof_days = 3600.0 / 86400.0

    v1, v2 = solve_lambert_retrograde(
        r1, r2, tof_days, mu_earth
    )  # Calculates the initial and final velocity vectors using my coded retrograde Lambert solver.
    r2_prop = propagate(
        r1, v1, tof_days * 86400.0, mu_earth
    )  # Propagates the initial position and velocity vectors using the two-body problem to get the final position vector r2_prop.
    err_km = np.linalg.norm(
        r2_prop - r2
    )  # Calculates the error between the propagated final position vector and the target final position vector.
    h_z = np.cross(r1, v1)[
        2
    ]  # The z-component of the angular momentum. Positive means counterclockwise (prograde) and negative means clockwise (retrograde) when viewed from above.

    print("\nv1 retrograde:", v1)
    print("v2 retrograde:", v2)
    print(f"Retrograde round-trip miss distance: {err_km:.3e} km, h_z = {h_z:.1f}")
    assert err_km < 1e-3
    assert (
        h_z < 0
    )  # The prograde orbit for these inputs has h_z > 0, so a retrograde orbit must have h_z < 0.


if __name__ == "__main__":
    try:
        test_round_trip_retrograde()
        print(f"PASS: test_round_trip_retrograde")
    except AssertionError:
        print(f"FAIL: test_round_trip_retrograde")
