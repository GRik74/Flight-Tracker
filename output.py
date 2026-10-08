DEBUG = True

def show_planes(planes):
    for plane in planes:
        plane_info = f"Hex Code: {plane.hex_code:7}"
        plane_info += f"| {plane.flight:10}" if not plane.flight is None else ""
        if plane.distance_available: plane_info += f" | Dist.: {str(round(plane.dist_nm, 1)):>6} | Bearing: {str(int(round(plane.bearing_to_plane, 0))):>4}"
        if plane.relational_info_available: plane_info += f" | Track: {str(int(round(plane.track, 0))):>4}"
        plane_info += f" | Alt: {str(round(plane.alt_ft, 1)):>7} ft" if plane.altitude_available else f" | Alt: {'unknown':>7} ft"
        plane_info += f" | GS: {str(int(round(plane.speed_kts, 0))):>8} kts" if plane.groundspeed_available else f" | GS: {'unknown':>8} kts"

        print(plane_info)
        if DEBUG: print(f"""

-----------------------------        
DEBUG: {plane.hex_code} | Age: {plane.age} | Missing from receiver: {plane.missing_from_receiver} | Buffer grace: {plane.buffer_grace} | Interesting: {plane.interesting} \n

Score:
Proximity:     {round(plane.debug_score['proximity score'], 1)}
Altitude:      {round(plane.debug_score['altitude score'], 1)}
Closing Prox.: {round(plane.debug_score['closing prox. score'], 1)}
Closing Time:  {round(plane.debug_score['closing time score'], 1)}
-----------------------------
Total Score:   {round(plane.score, 1)}
-----------------------------

""")
