import math
import numpy as np
from scipy.integrate import solve_ivp

from Main_Orbital import (
    Mean_Anomaly_of_Inputted_Date,
    Eccentric_Anomaly_Calculation,
    True_Anomaly_Calculation,
    True_Anomaly_Dot_Calculation,
    C_1,
    C_3,
)

MU_SUN_KM = 1.32712440018e11  # km^3/s^2
MU_SUN_AU_DAY = (
    2.9591220828559115e-4  # AU^3/day^2, the same GM as above in different units
)
AU_TO_KM = 149597870.7


def NEO_State_Vector(
    epoch_osculation,
    mean_motion,
    initial_mean_anomaly,
    e,
    a,
    raan,
    argument_of_perihelion,
    inclination,
    target_JD,
):  # Converts the NEO's orbital elements into its heliocentric position (km) and velocity (km/s) vectors at the Julian Date target_JD, using two-body motion from the osculating epoch. Angles (raan, argument_of_perihelion, inclination) are in RADIANS. This mirrors the math inside Lambert_TOF_Sweep_Preparation and Porkchop_Sweep.
    AU_to_Km = 149597870.7

    Mean_Anomaly = Mean_Anomaly_of_Inputted_Date(
        epoch_osculation, target_JD, mean_motion, initial_mean_anomaly
    )
    Eccentric_Anomaly = Eccentric_Anomaly_Calculation(Mean_Anomaly, e)
    True_Anomaly = True_Anomaly_Calculation(Eccentric_Anomaly, e)

    r_NEO = (a * (1 - e**2)) / (1 + (e * math.cos(True_Anomaly)))  # AU
    True_Anomaly_dot = True_Anomaly_Dot_Calculation(a, e, r_NEO)  # rad/s
    r_dot_NEO = (
        ((a * (1 - e**2)) * (e * math.sin(True_Anomaly)))
        / (1 + (e * math.cos(True_Anomaly))) ** 2
    ) * True_Anomaly_dot  # AU/s

    # Position and velocity in the perifocal frame (the orbit's own plane, x toward perihelion).
    r_perifocal = np.array(
        [r_NEO * math.cos(True_Anomaly), r_NEO * math.sin(True_Anomaly), 0.0]
    )
    v_perifocal = np.array(
        [
            (r_dot_NEO * math.cos(True_Anomaly))
            - (r_NEO * math.sin(True_Anomaly) * True_Anomaly_dot),
            (r_dot_NEO * math.sin(True_Anomaly))
            + (r_NEO * math.cos(True_Anomaly) * True_Anomaly_dot),
            0.0,
        ]
    )

    # Rotate from the perifocal frame into the inertial (ecliptic) frame.
    C_pi = C_3(argument_of_perihelion) @ C_1(inclination) @ C_3(raan)
    C_ip = C_pi.T

    r_km = (C_ip @ r_perifocal) * AU_to_Km  # AU -> km
    v_kms = (C_ip @ v_perifocal) * AU_to_Km  # AU/s -> km/s
    return r_km, v_kms


# A made-up orbit used by the offline tests (no internet needed). Angles in degrees here, converted to radians when used.
A_AU, ECC, INC, RAAN, ARGP, M0 = 1.8, 0.55, 12.0, 60.0, 110.0, 40.0
EPOCH_JD = 2460000.5
# Mean motion that is consistent with the Sun's GM and the semi-major axis, in degrees/day (the unit NASA's API uses).
N_DEG_DAY = math.degrees(math.sqrt(MU_SUN_AU_DAY / A_AU**3))


def elements(m0=M0):
    return (
        EPOCH_JD,
        N_DEG_DAY,
        m0,
        ECC,
        A_AU,
        math.radians(RAAN),
        math.radians(ARGP),
        math.radians(INC),
    )


def propagate(r0, v0, tof_s, mu):
    # Use a simple two-body propagator to fly the state forward in time. This is used by the offline tests to check that the NEO_State_Vector function is internally consistent.

    def rhs(t, s):
        r = s[:3]
        return np.concatenate([s[3:], -mu * r / np.linalg.norm(r) ** 3])

    sol = solve_ivp(rhs, [0, tof_s], np.concatenate([r0, v0]), rtol=1e-11, atol=1e-11)
    return sol.y[:3, -1]


def test_matches_two_body_propagation():  # Gets the state at the epoch, flies it forward 150 days with the independent propagator, and compares with the function's state 150 days after the epoch. Catches velocity, unit, and mean motion errors.
    r0, v0 = NEO_State_Vector(*elements(), EPOCH_JD)
    r1, _ = NEO_State_Vector(*elements(), EPOCH_JD + 150.0)
    r1_prop = propagate(r0, v0, 150.0 * 86400.0, MU_SUN_KM)
    err_km = np.linalg.norm(r1_prop - r1)
    print(f"\nPropagation vs. function after 150 days: {err_km:.3e} km")
    assert err_km < 1.0


def test_vis_viva():  # The vis-viva equation v^2 = mu * (2/r - 1/a) must hold for any two-body orbit. Checks that the speed and distance agree with each other and with a.
    r, v = NEO_State_Vector(*elements(), EPOCH_JD + 37.0)
    lhs = np.dot(v, v)
    rhs = MU_SUN_KM * (2.0 / np.linalg.norm(r) - 1.0 / (A_AU * AU_TO_KM))
    rel_err = abs(lhs - rhs) / rhs
    print(f"\nVis-viva relative error: {rel_err:.3e}")
    assert rel_err < 1e-6


def test_orbit_orientation():  # Checks that the inclination and ascending node are applied the right way around. The direction of the angular momentum h = r x v is fully set by i and RAAN: h_hat = [sin(i)sin(RAAN), -sin(i)cos(RAAN), cos(i)].
    r, v = NEO_State_Vector(*elements(), EPOCH_JD + 37.0)
    h = np.cross(r, v)
    h_hat = h / np.linalg.norm(h)
    i, om = math.radians(INC), math.radians(RAAN)
    expected = np.array(
        [math.sin(i) * math.sin(om), -math.sin(i) * math.cos(om), math.cos(i)]
    )
    err = np.linalg.norm(h_hat - expected)
    print(f"\nAngular momentum direction error: {err:.3e}")
    assert err < 1e-6


def test_perihelion_direction():  # At mean anomaly 0 the NEO is at perihelion, so its position must point along the perihelion direction, which depends on RAAN, inclination, and argument of perihelion.
    r, _ = NEO_State_Vector(*elements(m0=0.0), EPOCH_JD)
    i, om, w = math.radians(INC), math.radians(RAAN), math.radians(ARGP)
    expected = np.array(
        [
            math.cos(om) * math.cos(w) - math.sin(om) * math.sin(w) * math.cos(i),
            math.sin(om) * math.cos(w) + math.cos(om) * math.sin(w) * math.cos(i),
            math.sin(w) * math.sin(i),
        ]
    )
    err = np.linalg.norm(r / np.linalg.norm(r) - expected)
    print(f"\nPerihelion direction error: {err:.3e}")
    assert err < 1e-6



def horizons_comparison(
    neo_id, api_key, offsets_days=(0, 30, 90, 180, 365), extra_dates=()
): # compares the two-body orbital elements method with the JPL Horizons ephemeris for a given NEO. The offsets_days are days from the osculating epoch of the orbital elements, and extra_dates are specific calendar dates to check. Prints a table of position and velocity errors.
    import requests
    from datetime import datetime
    import julian
    from astroquery.jplhorizons import Horizons

    data = requests.get(
        f"https://api.nasa.gov/neo/rest/v1/neo/{neo_id}?api_key={api_key}"
    ).json()
    orbit = data["orbital_data"]
    epoch = float(orbit["epoch_osculation"])
    args = (
        epoch,
        float(orbit["mean_motion"]),
        float(orbit["mean_anomaly"]),
        float(orbit["eccentricity"]),
        float(orbit["semi_major_axis"]),
        math.radians(float(orbit["ascending_node_longitude"])),
        math.radians(float(orbit["perihelion_argument"])),
        math.radians(float(orbit["inclination"])),
    )

    # Build the list of Julian Dates to compare: offsets from the osculating epoch, plus any specific calendar dates.
    targets = [(f"epoch {o:+d} d", epoch + o) for o in offsets_days]
    for d in extra_dates:
        jd = julian.to_jd(datetime.strptime(d, "%Y-%m-%d"), fmt="jd")
        targets.append((d, jd))
    targets.sort(key=lambda t: t[1])

    # Horizons: heliocentric ecliptic position/velocity of the same object at the same dates.
    designation = data.get("designation", str(neo_id))
    obj = Horizons(
        id=designation,
        id_type="smallbody",
        location="500@10",
        epochs=[t[1] for t in targets],
    )
    vec = obj.vectors()

    print(f"\n{data['name']}  (epoch of elements: JD {epoch})")
    print(
        f"{'target':>18} {'JD':>14} {'position error (km)':>22} {'velocity error (m/s)':>22}"
    )
    for k, (label, jd) in enumerate(targets):
        r_h = np.array([vec["x"][k], vec["y"][k], vec["z"][k]]) * AU_TO_KM
        v_h = np.array([vec["vx"][k], vec["vy"][k], vec["vz"][k]]) * AU_TO_KM / 86400.0
        r_m, v_m = NEO_State_Vector(*args, jd)
        pos_err = np.linalg.norm(r_m - r_h)
        vel_err = np.linalg.norm(v_m - v_h) * 1000.0
        print(f"{label:>18} {jd:>14.1f} {pos_err:>22.1f} {vel_err:>22.3f}")


if __name__ == "__main__":
    for t in (
        test_matches_two_body_propagation,
        test_vis_viva,
        test_orbit_orientation,
        test_perihelion_direction,
    ):
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError:
            print(f"FAIL: {t.__name__}")

    answer = input("\nRun the Horizons comparison? (y/n): ").strip().lower()
    if answer == "y":
        neo_id = (
            input("NEO ID from NASA (press Enter for Apophis, 2099942): ").strip()
            or "2099942"
        )
        api_key = input("NASA API key: ").strip()
        # Add specific dates you care about, e.g. dates before and after a close planetary flyby.
        horizons_comparison(neo_id, api_key, extra_dates=("2029-03-01", "2029-06-01"))
