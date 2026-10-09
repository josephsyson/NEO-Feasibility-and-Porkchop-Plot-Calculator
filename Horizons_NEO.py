from datetime import timedelta
import numpy as np
from astroquery.jplhorizons import Horizons


def NEO_Horizons_Vectors(
    designation, first_date, last_date, step_days=5
):  # Pulls the NEO's heliocentric position (km) and velocity (km/s) from JPL Horizons at step_days intervals from first_date to last_date (datetime objects), in the same ecliptic J2000 frame as Earth_Data_Range. Horizons includes planetary gravity and close flybys, which the two-body orbital-elements method does not. Returns a dictionary {"YYYY-MM-DD": (r_km, v_kms)}, or None if the query fails so the caller can fall back to the two-body method.
    AU_to_Km = 149597870.7

    epochs = {
        "start": first_date.strftime("%Y-%m-%d"),
        "stop": last_date.strftime("%Y-%m-%d"),
        "step": f"{step_days}d",
    }  # Same style of epoch range as Earth_Data_Range so Earth and the NEO use the same time convention.

    try:
        obj = Horizons(
            id=str(designation) , id_type="designation", location="500@10", epochs=epochs
        )
        vectors = obj.vectors()
    except Exception as error:
        print(
            f"Horizons query failed for {designation} ({error}). Falling back to the two-body orbital elements method."
        )
        return None

    expected_rows = ((last_date - first_date).days // step_days) + 1
    if len(vectors) != expected_rows:
        print(
            f"Horizons returned {len(vectors)} rows for {designation} but {expected_rows} were expected. Falling back to the two-body orbital elements method."
        )
        return None

    states = {}
    for k in range(len(vectors)):
        date_key = (first_date + timedelta(days=step_days * k)).strftime("%Y-%m-%d")
        position_km = (
            np.array([vectors["x"][k], vectors["y"][k], vectors["z"][k]]) * AU_to_Km
        )  # Horizons returns AU
        velocity_kms = (
            np.array([vectors["vx"][k], vectors["vy"][k], vectors["vz"][k]])
            * AU_to_Km
            / 86400.0
        )  # Horizons returns AU/day
        states[date_key] = (position_km, velocity_kms)

    return states
