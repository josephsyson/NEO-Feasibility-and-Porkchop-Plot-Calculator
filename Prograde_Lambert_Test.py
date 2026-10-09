import math
import numpy as np
from scipy.integrate import solve_ivp

from Main_Orbital import prograde, z_Solver_Prograde, Lambert_Langrange_Solver


def solve_lambert_prograde(
    r1, r2, tof_days, mu
):  # Runs the Lambert Solver for a prograde orbit.
    r1_norm = np.linalg.norm(r1)
    r2_norm = np.linalg.norm(r2)
    cos_ratio = np.dot(r1, r2) / (r1_norm * r2_norm)
    dtheta = prograde(cos_ratio, np.cross(r1, r2))
    A = math.sin(dtheta) * math.sqrt(r1_norm * r2_norm / (1 - math.cos(dtheta)))
    Y = z_Solver_Prograde(r1_norm, r2_norm, A, tof_days, mu)
    return Lambert_Langrange_Solver(r1_norm, r2_norm, r1, r2, mu, Y, A)


def propagate(r0, v0, tof_s, mu): # Independent two-body propagation (no Lambert code involved).

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


def test_curtis_example():  # Uses example 5.2 from Curtis, H.D (2005). Orbital Mechanics for Engineering Students (1st ed.). Elsevier Butterworth-Heinemann. to test the Lambert solver and solve for v1 and v2. The results are compared to the book's values.
    mu_earth = 398600.0  # km^3/s^2
    r1 = np.array([5000.0, 10000.0, 2100.0])
    r2 = np.array([-14600.0, 2500.0, 7000.0])
    tof_days = 3600.0 / 86400.0
    v1_book = np.array([-5.9925, 1.9254, 3.2456])
    v2_book = np.array([-3.3125, -4.1966, -0.38529])

    v1, v2 = solve_lambert_prograde(r1, r2, tof_days, mu_earth)
    print("\nv1 mine:", v1, "| book:", v1_book)
    print("v2 mine:", v2, "| book:", v2_book)
    assert np.allclose(v1, v1_book, atol=1e-3)
    assert np.allclose(v2, v2_book, atol=1e-3)


def test_round_trip_earth():  # Using Earth as the central body,calculates the initial velocity vector v1 using my coded Lambert solver. Propagates the initial position and velocity vectors using the two-body problem to get the final position vector r2_prop after an hour. Calculates the error between the propagated final position vector and the target final position vector.
    mu_earth = 398600.0  # Curtis example 5.2 values
    r1 = np.array([5000.0, 10000.0, 2100.0])
    r2 = np.array([-14600.0, 2500.0, 7000.0])
    tof_days = 3600.0 / 86400.0

    v1, _ = solve_lambert_prograde(
        r1, r2, tof_days, mu_earth
    )  # Calculates the initial velocity vector v1 using my coded Lambert solver.
    r2_prop = propagate(
        r1, v1, tof_days * 86400.0, mu_earth
    )  # Propagates the initial position and velocity vectors using the two-body problem to get the final position vector r2_prop.
    err_km = np.linalg.norm(
        r2_prop - r2
    )  # Calculates the error between the propagated final position vector and the target final position vector.
    print(f"\nEarth round-trip miss distance: {err_km:.3e} km")
    assert err_km < 1e-3


def test_round_trip_heliocentric():  # Using the Sun as the central body, calculates the initial velocity vector v1 using my coded Lambert solver. Propagates the initial position and velocity vectors using the two-body problem to get the final position vector r2_prop after 200 days. Calculates the error between the propagated final position vector and the target final position vector.
    mu_sun = 1.32712440018e11  # km^3/s^2
    AU = 149597870.7
    r1 = np.array([AU, 0.0, 0.0])
    ang = math.radians(100.0)
    r2 = (
        1.52 * AU * np.array([math.cos(ang), math.sin(ang), 0.0])
    )  # Uses made up positions from the Sun to Mars for a heliocentric round trip test.
    tof_days = 200.0

    v1, _ = solve_lambert_prograde(r1, r2, tof_days, mu_sun)
    r2_prop = propagate(r1, v1, tof_days * 86400.0, mu_sun)
    err_km = np.linalg.norm(r2_prop - r2)
    print(f"\nHeliocentric round-trip miss distance: {err_km:.3e} km")
    assert err_km < 100.0  # ~4e-7 of the 2e8 km distance


if __name__ == "__main__":
    for t in (test_curtis_example, test_round_trip_earth, test_round_trip_heliocentric):
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError:
            print(f"FAIL: {t.__name__}")
