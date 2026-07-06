"""Sri Lankan location lookup shared by the source modules.

Maps common cities/towns to their administrative district and the province
label used by LankaPropertyWeb. "Colombo 1".."Colombo 15" are handled as
cities in the Colombo district. Unknown areas return None so callers can
report "not searched" instead of guessing.
"""

import re

# district -> LPW province label (LPW writes "North" for the Northern province
# and "North West"/"North Central" with spaces; spaces become "+" in URLs)
DISTRICT_PROVINCE = {
    "colombo": "Western", "gampaha": "Western", "kalutara": "Western",
    "kandy": "Central", "matale": "Central", "nuwara eliya": "Central",
    "galle": "Southern", "matara": "Southern", "hambantota": "Southern",
    "jaffna": "North", "kilinochchi": "North", "mannar": "North",
    "vavuniya": "North", "mullaitivu": "North",
    "kurunegala": "North West", "puttalam": "North West",
    "anuradhapura": "North Central", "polonnaruwa": "North Central",
    "trincomalee": "Eastern", "batticaloa": "Eastern", "ampara": "Eastern",
    "badulla": "Uva", "monaragala": "Uva",
    "ratnapura": "Sabaragamuwa", "kegalle": "Sabaragamuwa",
}

CITY_DISTRICT = {
    # Colombo district
    "colombo": "colombo", "nugegoda": "colombo", "dehiwala": "colombo",
    "mount lavinia": "colombo", "battaramulla": "colombo", "kottawa": "colombo",
    "maharagama": "colombo", "malabe": "colombo", "homagama": "colombo",
    "piliyandala": "colombo", "pannipitiya": "colombo", "moratuwa": "colombo",
    "rajagiriya": "colombo", "kotte": "colombo", "boralesgamuwa": "colombo",
    "athurugiriya": "colombo", "kaduwela": "colombo", "kolonnawa": "colombo",
    "kohuwala": "colombo", "kirulapone": "colombo", "padukka": "colombo",
    "avissawella": "colombo", "angoda": "colombo", "wellampitiya": "colombo",
    "nawinna": "colombo", "embuldeniya": "colombo", "udahamulla": "colombo",
    # Gampaha
    "negombo": "gampaha", "gampaha": "gampaha", "kadawatha": "gampaha",
    "wattala": "gampaha", "ja-ela": "gampaha", "kelaniya": "gampaha",
    "kiribathgoda": "gampaha", "ragama": "gampaha", "minuwangoda": "gampaha",
    "nittambuwa": "gampaha", "veyangoda": "gampaha", "seeduwa": "gampaha",
    "katunayake": "gampaha",
    # Kalutara
    "kalutara": "kalutara", "panadura": "kalutara", "wadduwa": "kalutara",
    "horana": "kalutara", "beruwala": "kalutara", "aluthgama": "kalutara",
    "bandaragama": "kalutara", "matugama": "kalutara",
    # Central
    "kandy": "kandy", "peradeniya": "kandy", "katugastota": "kandy",
    "pilimatalawa": "kandy", "kundasale": "kandy",
    "matale": "matale", "dambulla": "matale",
    "nuwara eliya": "nuwara eliya", "hatton": "nuwara eliya",
    # Southern
    "galle": "galle", "hikkaduwa": "galle", "unawatuna": "galle",
    "ahangama": "galle", "ambalangoda": "galle", "bentota": "galle",
    "karapitiya": "galle",
    "matara": "matara", "weligama": "matara", "mirissa": "matara",
    "dickwella": "matara",
    "hambantota": "hambantota", "tangalle": "hambantota",
    "tissamaharama": "hambantota", "beliatta": "hambantota",
    # North / East
    "jaffna": "jaffna", "chavakachcheri": "jaffna",
    "trincomalee": "trincomalee", "batticaloa": "batticaloa",
    "ampara": "ampara", "arugam bay": "ampara",
    # North West / North Central
    "kurunegala": "kurunegala", "kuliyapitiya": "kurunegala",
    "narammala": "kurunegala",
    "puttalam": "puttalam", "chilaw": "puttalam", "wennappuwa": "puttalam",
    "marawila": "puttalam",
    "anuradhapura": "anuradhapura", "polonnaruwa": "polonnaruwa",
    # Uva / Sabaragamuwa
    "badulla": "badulla", "bandarawela": "badulla", "ella": "badulla",
    "haputale": "badulla",
    "monaragala": "monaragala", "wellawaya": "monaragala",
    "ratnapura": "ratnapura", "embilipitiya": "ratnapura",
    "balangoda": "ratnapura",
    "kegalle": "kegalle", "mawanella": "kegalle",
}


def lookup(area):
    """Return (city, district, province) for a user-entered area, or None.
    city/district are lowercase; province is the LPW-style label."""
    a = re.sub(r"\s+", " ", area.strip().lower())
    if re.fullmatch(r"colombo\s*\d{1,2}", a):
        city = "colombo " + a.split()[-1]
        return (city, "colombo", "Western")
    district = CITY_DISTRICT.get(a)
    if district is None:
        return None
    return (a, district, DISTRICT_PROVINCE[district])


def slug(name, sep="-"):
    """'Mount Lavinia' -> 'mount-lavinia' (or any separator)."""
    return re.sub(r"[^a-z0-9]+", sep, name.strip().lower()).strip(sep)
