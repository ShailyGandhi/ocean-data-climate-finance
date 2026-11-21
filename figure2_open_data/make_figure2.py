"""
Rebuild Figure 2 of sustainability-4547676 from open data only (no scaling, interpolation or modelling).

Panels
  (a) Absolute sea-level anomaly, basin means    NOAA Laboratory for Satellite Altimetry (LSA)
  (b) Relative sea-level anomaly, SIDS gauges    PSMSL Revised Local Reference (RLR) annual means
  (c) Ocean heat content anomaly 0-2000 m        NOAA NCEI basin time series (pentadal, +/- 1 s.e.)
  (d) Surface-ocean pH and aragonite saturation  Hawaii Ocean Time-series (HOT), Station ALOHA
  (e) Adaptation-related development finance     OECD Climate-related development finance, recipient
      by OECD recipient region                   perspective (commitments, constant 2024 USD)
  (f) Same, Small Island Developing States       as (e), recipients matched to the UN list of SIDS

Downloads are cached in ./data_raw; ./data_raw/manifest.csv holds the versions used for the paper (URL, retrieval time,
size, SHA-256) and ./data_raw/run_log.csv the versions used in the current run (see ../provenance.py);
every plotted value and every fitted trend is written to ./data_out.
"""
import io
import os
import re
import sys
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import provenance  # noqa: E402  (package root: cached, checksummed downloads)

RAW = os.path.join(HERE, "data_raw")
OUT = os.path.join(HERE, "data_out")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

BASELINE = (1995, 2014)  # IPCC AR6 reference period, used for all anomaly panels (a-c)
PERIOD = (1993, 2024)    # common display and trend window for the ocean panels (a-d): satellite-altimetry era


def fetch(url, name):
    """Download once into data_raw and record provenance in data_raw/manifest.csv (see provenance.py)."""
    return provenance.fetch(url, name, RAW)


def ols_trend(x, y):
    """Least-squares linear trend with its standard error, adjusted for lag-1 autocorrelation of the
    residuals via an effective sample size n_eff = n (1 - r1) / (1 + r1) (Santer et al. 2000)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    order = np.argsort(x)
    x, y = x[order], y[order]
    n = len(x)
    A = np.vstack([x - x.mean(), np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    r1 = np.corrcoef(resid[:-1], resid[1:])[0, 1]
    n_eff = n * (1 - r1) / (1 + r1) if r1 > 0 else n
    n_eff = max(n_eff, 3.0)
    s2 = resid @ resid / (n_eff - 2)
    se = np.sqrt(s2 / ((x - x.mean()) ** 2).sum())
    return coef[0], se, r1, n_eff


trends = []  # (panel, series, variable, period, trend, se_ar1, units, n, lag1_autocorr, n_eff)

# ---------------------------------------------------------------- (a) altimetry
LSA = "https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/slr_sla_{}_keep_ref_90.csv"
BASINS_ALT = {"gbl": "Global ocean", "pac": "Pacific Ocean", "atl": "Atlantic Ocean", "ind": "Indian Ocean"}


def load_altimetry(code):
    df = pd.read_csv(fetch(LSA.format(code), f"lsa_{code}.csv"), comment="#")
    # one column per mission; missions do not overlap in this product, so take the row-wise mean
    sla = df.drop(columns="year").mean(axis=1)
    s = pd.DataFrame({"year": np.floor(df["year"]).astype(int), "sla_mm": sla})
    annual = s.groupby("year")["sla_mm"].agg(["mean", "count"])
    annual = annual[annual["count"] >= 20]["mean"]  # drop incomplete years (~36 cycles per full year)
    return annual - annual.loc[BASELINE[0]:BASELINE[1]].mean()


alt = pd.DataFrame({name: load_altimetry(code) for code, name in BASINS_ALT.items()})
alt = alt.loc[PERIOD[0]:PERIOD[1]]
alt.index.name = "year"
alt.round(2).to_csv(os.path.join(OUT, "panel_a_altimetry_sla_mm.csv"))
alt_fit = {}
for name in alt.columns:
    s = alt[name].dropna()
    t = s.index.values.astype(float)
    c = np.polyfit(t - t.mean(), s.values, 2)
    r, se, r1, neff = ols_trend(t, s.values)
    alt_fit[name] = (r, se, 2 * c[0])  # linear OLS rate (mm/yr) and its s.e.; quadratic acceleration (mm/yr^2)
    trends.append(("a", name, "absolute sea level (linear)", f"{int(t[0])}-{int(t[-1])}", r, se, "mm/yr", len(s), r1, neff))
    trends.append(("a", name, "absolute sea level (quadratic acceleration)", f"{int(t[0])}-{int(t[-1])}",
                   2 * c[0], np.nan, "mm/yr^2", len(s), np.nan, np.nan))

# ---------------------------------------------------------------- (b) SIDS tide gauges
PSMSL_ZIP = "https://psmsl.org/data/obtaining/rlr.annual.data/rlr_annual.zip"
# PSMSL country codes (filelist.txt) of SIDS that are UN Member States -> (country, ISO3, region).
# Covers every SIDS on the UN-OHRLLS list (UN Member States) that has at least one PSMSL RLR station, identified from
# station names and coordinates in filelist.txt (26 countries). The other 12 SIDS (e.g., Barbados, Belize, Guyana,
# Suriname, Comoros, Timor-Leste) have no PSMSL RLR station. Every station of these codes is screened below and listed in
# psmsl_sids_station_screening.csv. Codes 730/750/770 are the Gilbert, Phoenix and Line Islands of Kiribati.
SIDS_PSMSL = {
    "890": ("Trinidad and Tobago", "TTO", "Atlantic/Caribbean"), "893": ("Grenada", "GRD", "Atlantic/Caribbean"),
    "913": ("Dominica", "DMA", "Atlantic/Caribbean"), "932": ("Jamaica", "JAM", "Atlantic/Caribbean"),
    "934": ("Haiti", "HTI", "Atlantic/Caribbean"), "936": ("Dominican Republic", "DOM", "Atlantic/Caribbean"),
    "941": ("Bahamas", "BHS", "Atlantic/Caribbean"), "482": ("Bahrain", "BHR", "Persian Gulf"),
    "742": ("Fiji", "FJI", "Pacific"), "732": ("Tuvalu", "TUV", "Pacific"), "741": ("Vanuatu", "VUT", "Pacific"),
    "670": ("Papua New Guinea", "PNG", "Pacific"), "710": ("Micronesia", "FSM", "Pacific"),
    "711": ("Palau", "PLW", "Pacific"), "715": ("Nauru", "NRU", "Pacific"),
    "720": ("Marshall Islands", "MHL", "Pacific"), "730": ("Kiribati", "KIR", "Pacific"),
    "750": ("Kiribati", "KIR", "Pacific"), "770": ("Kiribati", "KIR", "Pacific"),
    "734": ("Solomon Islands", "SLB", "Pacific"), "744": ("Tonga", "TON", "Pacific"),
    "746": ("Samoa", "WSM", "Pacific"),
    "442": ("Seychelles", "SYC", "Indian"), "450": ("Mauritius", "MUS", "Indian"),
    "454": ("Maldives", "MDV", "Indian"), "555": ("Singapore", "SGP", "Singapore Strait"),
    "930": ("Cuba", "CUB", "Atlantic/Caribbean"), "380": ("Cabo Verde", "CPV", "Atlantic/Caribbean"),
}
NOT_SIDS_STATIONS = {595: "Wake Island (United States territory; listed under the Marshall Islands code)",
                     2341: "Palmyra Island (United States territory; listed under the Kiribati Line Islands code)"}
# One station per country: the station with the most valid annual values in 1993-2024 (ties: more baseline values).
# Documented exception: Maldives uses Male (capital; most of the population) rather than Gan II (2 more valid years).
STATION_OVERRIDE = {"Maldives": (1753, "gauge at the capital, Malé, where most of the population lives; "
                                       "Gan II (PSMSL 1707) has two more valid years and is reported as a sensitivity case")}
MIN_YEARS = 20  # minimum valid annual values since 1993
MIN_BASE = 10   # minimum valid annual values within the baseline period


def load_psmsl(z, sid):
    raw = z.read(f"rlr_annual/data/{sid}.rlrdata").decode()
    df = pd.read_csv(io.StringIO(raw), sep=";", header=None, names=["year", "mm", "missing", "flag"],
                     dtype={"flag": str, "missing": str})
    # keep values without quality flags; 'missing' = Y marks years with some missing days (kept)
    df = df[(df["mm"] > -99999) & (df["flag"].str.strip() == "000")]
    return df.set_index("year")["mm"].astype(float)


DISPLAY = {1839: "Funafuti", 1805: "Lautoka", 1841: "Port Vila", 1846: "Pointe La Rue", 1673: "Port Louis",
           1753: "Malé", 563: "Gibara", 1914: "Palmeira", 1860: "Lombrum", 1251: "Yap", 1252: "Malakal",
           1844: "Nauru", 513: "Kwajalein", 1804: "Betio", 1861: "Honiara", 1842: "Nuku'alofa", 1840: "Apia",
           1746: "Tanjong Pagar", 1707: "Gan"}


def title_case(sid, name):
    return DISPLAY.get(sid) or " ".join(w.capitalize() for w in name.replace("-B", " B").replace("-C", " C").split())


zpath = fetch(PSMSL_ZIP, "psmsl_rlr_annual.zip")
zf = zipfile.ZipFile(zpath)
filelist = [l.split(";") for l in zf.read("rlr_annual/filelist.txt").decode("latin1").splitlines() if l.strip()]
cand = []
for sid, lat, lon, name, ccode, *_ in filelist:
    sid, ccode = int(sid), ccode.strip()
    if ccode not in SIDS_PSMSL:
        continue
    country, iso3, region = SIDS_PSMSL[ccode]
    try:
        s = load_psmsl(zf, sid)
    except KeyError:
        continue
    yrs = s.loc[PERIOD[0]:PERIOD[1]]
    n_base = s.loc[BASELINE[0]:BASELINE[1]].count()
    cand.append({"psmsl_id": sid, "station": name.strip(), "country": country, "iso3": iso3, "region": region,
                 "lat": float(lat), "lon": float(lon), "n_valid_1993_2024": int(yrs.count()),
                 "n_valid_baseline": int(n_base),
                 "first_valid_year": int(yrs.index.min()) if len(yrs) else np.nan,
                 "last_valid_year": int(yrs.index.max()) if len(yrs) else np.nan})
cand = pd.DataFrame(cand)
cand["excluded_reason"] = cand["psmsl_id"].map(NOT_SIDS_STATIONS).fillna("")
cand["qualifies"] = ((cand["n_valid_1993_2024"] >= MIN_YEARS) & (cand["n_valid_baseline"] >= MIN_BASE)
                     & (cand["excluded_reason"] == ""))
cand["selected"] = False
cand["selection_note"] = ""
for country, g in cand[cand["qualifies"]].groupby("country"):
    best = g.sort_values(["n_valid_1993_2024", "n_valid_baseline"], ascending=False).index[0]
    note = "most valid annual values in 1993-2024 among qualifying stations in the country"
    if country in STATION_OVERRIDE:
        sid, note = STATION_OVERRIDE[country]
        best = g.index[g["psmsl_id"] == sid][0]
    cand.loc[best, ["selected", "selection_note"]] = [True, note]
cand = cand.sort_values(["region", "country", "selected", "n_valid_1993_2024"], ascending=[True, True, False, False])
cand.to_csv(os.path.join(OUT, "psmsl_sids_station_screening.csv"), index=False, encoding="utf-8-sig")
print(f"PSMSL stations in SIDS: {len(cand)}, qualifying: {int(cand.qualifies.sum())}, "
      f"countries selected: {int(cand.selected.sum())}")

tg, tg_full, tg_region = {}, {}, {}
for _, c in cand[cand["selected"]].iterrows():
    label = f"{title_case(c['psmsl_id'], c['station'])}, {c['country']}"
    s = load_psmsl(zf, c["psmsl_id"])
    s = s - s.loc[BASELINE[0]:BASELINE[1]].mean()
    tg_full[label] = s
    s = s.loc[PERIOD[0]:PERIOD[1]]
    tg[label], tg_region[label] = s, c["region"]
    r, se, r1, neff = ols_trend(s.index, s.values)
    trends.append(("b", f"{label} (PSMSL {c['psmsl_id']})", "relative sea level (linear)",
                   f"{s.index.min()}-{s.index.max()}", r, se, "mm/yr", s.count(), r1, neff))
# sensitivity station for the Maldives (see STATION_OVERRIDE)
s = load_psmsl(zf, 1707)
s = (s - s.loc[BASELINE[0]:BASELINE[1]].mean()).loc[PERIOD[0]:PERIOD[1]]
r, se, r1, neff = ols_trend(s.index, s.values)
trends.append(("b-sens", "Gan II, Maldives (PSMSL 1707)", "relative sea level (linear)",
               f"{s.index.min()}-{s.index.max()}", r, se, "mm/yr", s.count(), r1, neff))
pd.DataFrame({"year": s.index, "Gan II, Maldives (PSMSL 1707)": s.values}).round(1).to_csv(
    os.path.join(OUT, "sensitivity_b_gan_ii_maldives_rsl_mm.csv"), index=False)
tg = pd.DataFrame(tg)
tg.index.name = "year"
tg.round(1).to_csv(os.path.join(OUT, "panel_b_sids_tide_gauges_rsl_mm.csv"), encoding="utf-8-sig")
tg_full = pd.DataFrame(tg_full)
tg_full.index.name = "year"
tg_full.round(1).to_csv(os.path.join(OUT, "full_record_b_sids_tide_gauges_rsl_mm.csv"), encoding="utf-8-sig")

# ---------------------------------------------------------------- (c) OHC 0-2000 m
NCEI = ("https://www.ncei.noaa.gov/data/oceans/woa/DATA_ANALYSIS/3M_HEAT_CONTENT/DATA/basin/pentad/"
        "pent_h22-{}0-2000m.dat")
BASINS_OHC = {"w": ("WO", "Global ocean"), "p": ("PO", "Pacific Ocean"),
              "a": ("AO", "Atlantic Ocean"), "i": ("IO", "Indian Ocean")}
ohc = {}
for code, (col, name) in BASINS_OHC.items():
    df = pd.read_csv(fetch(NCEI.format(code), f"ncei_ohc_{code}.dat"), sep=r"\s+").set_index("YEAR")
    ohc[name] = df[col] * 10  # file units 10^22 J -> ZJ (10^21 J)
    ohc[name + " SE"] = df[col + "se"] * 10
ohc = pd.DataFrame(ohc)
ohc.index.name = "pentad_centre_year"
ohc.insert(0, "window_start", (ohc.index - 2.5).astype(int))  # NCEI pentad "1957.5" = 5-year mean 1955-1959
ohc.insert(1, "window_end", (ohc.index + 1.5).astype(int))
# full record as published by NCEI (anomalies relative to the 1955-2006 climatology)
ohc.round(2).to_csv(os.path.join(OUT, "full_record_c_ohc_0_2000m_zj_ref_1955_2006.csv"))
names_ohc = [n for _, n in BASINS_OHC.values()]
# re-reference to 1995-2014: mean of the pentads lying entirely within the baseline (1995-1999 ... 2010-2014);
# a constant shift per basin, so trends and s.e. are unchanged
in_base = (ohc["window_start"] >= BASELINE[0]) & (ohc["window_end"] <= BASELINE[1])
# all 16 (overlapping) pentads whose window lies inside 1995-2014, equally weighted; record them for transparency
ohc.loc[in_base, ["window_start", "window_end"] + names_ohc].round(2).to_csv(
    os.path.join(OUT, "ohc_baseline_pentads_1995_2014_ref_1955_2006.csv"))
print("OHC baseline pentads:", int(in_base.sum()))
ohc[names_ohc] = ohc[names_ohc] - ohc.loc[in_base, names_ohc].mean()
# display: pentads centred in the common period whose 5-year window ends by PERIOD[1] (no partial final years)
ohc = ohc[(ohc.index >= PERIOD[0]) & (ohc["window_end"] <= PERIOD[1])]
ohc.round(2).to_csv(os.path.join(OUT, "panel_c_ohc_0_2000m_zj.csv"))
# trend: consecutive NCEI pentads are overlapping 5-year means, so fit only non-overlapping pentads, chosen to tile
# the years up to PERIOD[1] (1995-1999, ..., 2020-2024); plain OLS s.e., as 6 points are too few for an AR(1) estimate
tiles = ohc[((PERIOD[1] - ohc["window_end"]) % 5 == 0)]
for name in names_ohc:
    s = tiles[name]
    x = s.index.values.astype(float)
    k, cov = np.polyfit(x - x.mean(), s.values, 1, cov="unscaled")
    resid = s.values - np.polyval(k, x - x.mean())
    se = np.sqrt(cov[0, 0] * (resid @ resid) / (len(x) - 2))
    trends.append(("c", name, "OHC 0-2000 m (linear, non-overlapping pentads)",
                   f"{tiles['window_start'].min()}-{tiles['window_end'].max()}", k[0], se, "ZJ/yr", len(s),
                   np.nan, np.nan))

# ---------------------------------------------------------------- (d) HOT acidification
HOT = "https://hahana.soest.hawaii.edu/hot/hotco2/HOT_surface_CO2.txt"
hot = pd.read_csv(fetch(HOT, "HOT_surface_CO2.txt"), sep="\t", skiprows=8, na_values=[-999, "-999"])
hot["date"] = pd.to_datetime(hot["date"], format="%d-%b-%y")
hot["t"] = hot["date"].dt.year + (hot["date"].dt.dayofyear - 0.5) / 365.25
# Product version: header lines 3-4 of HOT_surface_CO2.txt ("Last updated ..."); values are cruise means over
# 0-30 dbar (HOT_surface_CO2_readme.pdf). Missing values are coded -999 and read as NaN; cruises without a
# calculated in situ pH or aragonite saturation value are dropped (no gap filling). The 'notes' column marks cruises
# where HOT used substitute or assumed inputs; they are kept in the main analysis (values used as provided) and
# excluded in a sensitivity test.
NOTE_SUBSTITUTIONS = set("abdefmnr")  # Keeling DIC/TA, assumed nTA, deeper samples, WHOTS pH (see readme)
fetch("https://hahana.soest.hawaii.edu/hot/hotco2/HOT_surface_CO2_readme.pdf", "HOT_surface_CO2_readme.pdf")
with open(os.path.join(RAW, "HOT_surface_CO2.txt"), encoding="latin1") as fh:
    HOT_VERSION = [next(fh).strip("\t\n") for _ in range(4)][3]
hot = hot[["date", "t", "pHcalc_insitu", "aragsatcalc_insitu", "notes"]].dropna(subset=["pHcalc_insitu", "aragsatcalc_insitu"])
hot["notes"] = hot["notes"].fillna("").astype(str)
hot["substituted_inputs"] = hot["notes"].map(lambda s: bool(set(s) & NOTE_SUBSTITUTIONS))
hot.round(4).to_csv(os.path.join(OUT, "full_record_d_hot_ph_aragonite.csv"), index=False)
hot = hot[hot["date"].dt.year.between(*PERIOD)]
hot.round(4).to_csv(os.path.join(OUT, "panel_d_hot_ph_aragonite.csv"), index=False)
print("HOT product:", HOT_VERSION, "| cruises 1993-2024:", len(hot), "| with substituted inputs:",
      int(hot["substituted_inputs"].sum()))
for var, units in [("pHcalc_insitu", "pH units/yr"), ("aragsatcalc_insitu", "Omega_ar units/yr")]:
    r, se, r1, neff = ols_trend(hot["t"], hot[var])
    trends.append(("d", "HOT Station ALOHA", var, f"{hot['date'].dt.year.min()}-{hot['date'].dt.year.max()}",
                   r, se, units, len(hot), r1, neff))
    h2 = hot[~hot["substituted_inputs"]]
    r, se, r1, neff = ols_trend(h2["t"], h2[var])
    trends.append(("d-sens", "HOT Station ALOHA, excluding cruises with substituted inputs", var,
                   f"{h2['date'].dt.year.min()}-{h2['date'].dt.year.max()}", r, se, units, len(h2), r1, neff))

# ---------------------------------------------------------------- (e, f) OECD adaptation finance
CRDF = "https://webfs.oecd.org/climate/RecipientPerspective/{}"
CRDF_FILES = ["CRDF-RP_2014-2015.xlsx"] + [f"CRDF-RP_{y}.xlsx" for y in range(2016, 2025)]
REGION_GROUP = {
    "South of Sahara": "Africa", "North of Sahara": "Africa", "Africa": "Africa",
    "Far East Asia": "Asia & Middle East", "South & Central Asia": "Asia & Middle East",
    "Asia": "Asia & Middle East", "Middle East": "Asia & Middle East",
    "Caribbean & Central America": "Latin America & Caribbean", "South America": "Latin America & Caribbean",
    "America": "Latin America & Caribbean",
    "Oceania": "Oceania", "Europe": "Europe",
    "Developing countries unspecified": "Unallocated / multi-region",
}
# UN-OHRLLS list of Small Island Developing States that are UN Member States
SIDS = ["Antigua and Barbuda", "Bahamas", "Barbados", "Belize", "Cabo Verde", "Comoros", "Cuba", "Dominica",
        "Dominican Republic", "Fiji", "Grenada", "Guinea-Bissau", "Guyana", "Haiti", "Jamaica", "Kiribati",
        "Maldives", "Marshall Islands", "Micronesia", "Mauritius", "Nauru", "Palau", "Papua New Guinea", "Samoa",
        "Sao Tome and Principe", "Singapore", "Seychelles", "Solomon Islands", "Saint Kitts and Nevis",
        "Saint Lucia", "Saint Vincent and the Grenadines", "Suriname", "Timor-Leste", "Tonga",
        "Trinidad and Tobago", "Tuvalu", "Vanuatu", "Bahrain"]


def norm(s):
    """Normalize case, accents and punctuation only. Qualifiers are NOT stripped, so regional recipients such as
    'Micronesia, regional' or 'Caribbean, regional' never match an individual country."""
    s = s.lower().replace("st.", "saint").replace("é", "e").replace("ã", "a").replace("&", "and")
    return re.sub(r"[^a-z]", "", s)


SIDS_N = {norm(x): x for x in SIDS}
fin_parts = []
for f in CRDF_FILES:
    path = fetch(CRDF.format(f), f)
    for sheet in pd.ExcelFile(path).sheet_names:
        if sheet.upper() == "NOTES":
            continue
        hdr = pd.read_excel(path, sheet_name=sheet, nrows=0).columns
        ad = [c for c in hdr if re.fullmatch(
            r"Adaptation-related development finance \(includes overlap\) - Commitment - \d{4} USD thousand", c)]
        assert len(ad) <= 1, f"{f}/{sheet}: more than one matching finance column: {ad}"
        if not ad:
            continue
        df = pd.read_excel(path, sheet_name=sheet, usecols=["Year", "Recipient Name", "Recipient Region", ad[0]])
        df = df.rename(columns={ad[0]: "adapt_kusd"})
        df["price_base"] = re.search(r"(\d{4}) USD", ad[0]).group(1)
        fin_parts.append(df)
    print("read", f)
fin = pd.concat(fin_parts, ignore_index=True)
assert fin["price_base"].nunique() == 1, "files use different constant-price bases"
PRICE_BASE = fin["price_base"].iloc[0]
fin = fin.dropna(subset=["adapt_kusd"])
unmapped = set(fin["Recipient Region"].dropna().unique()) - set(REGION_GROUP)
assert not unmapped and fin["Recipient Region"].notna().all(), f"unmapped or missing recipient regions: {unmapped}"
fin["group"] = fin["Recipient Region"].map(REGION_GROUP)  # six mutually exclusive groups; every label is mapped
fin["sids"] = fin["Recipient Name"].astype(str).map(lambda n: SIDS_N.get(norm(n)))
assert not fin.loc[fin["sids"].notna(), "Recipient Name"].str.contains("regional", case=False).any(), \
    "a regional recipient was matched to a SIDS"

by_region = fin.pivot_table(index="Year", columns="group", values="adapt_kusd", aggfunc="sum") / 1e6  # USD bn
by_region.round(3).to_csv(os.path.join(OUT, f"panel_e_adaptation_finance_by_region_usd_bn_{PRICE_BASE}.csv"))
sids_fin = fin[fin["sids"].notna()]
sids_year = sids_fin.groupby("Year")["adapt_kusd"].sum() / 1e6
sids_share = 100 * sids_year / by_region.sum(axis=1)
pd.DataFrame({"SIDS_adaptation_USDbn": sids_year, "SIDS_share_of_total_pct": sids_share}).round(3).to_csv(
    os.path.join(OUT, f"panel_f_sids_adaptation_finance_usd_bn_{PRICE_BASE}.csv"))
sids_fin.groupby(["sids", "Year"])["adapt_kusd"].sum().div(1e3).unstack().round(2).to_csv(
    os.path.join(OUT, f"panel_f_sids_adaptation_finance_by_country_usd_mn_{PRICE_BASE}.csv"))
matched = set(sids_fin["sids"])
print("SIDS matched in OECD data:", len(matched), "| not found:", sorted(set(SIDS) - matched))
yrs = sids_fin.groupby("sids")["Year"].agg(lambda s: ", ".join(str(y) for y in sorted(set(s))))
pd.DataFrame({"sids_un_member_state": sorted(SIDS)}).assign(
    in_oecd_recipient_files=lambda d: d.sids_un_member_state.isin(matched),
    years_with_records=lambda d: d.sids_un_member_state.map(yrs).fillna("")).to_csv(
    os.path.join(OUT, "oecd_sids_recipient_matching.csv"), index=False, encoding="utf-8-sig")

pd.DataFrame(trends, columns=["panel", "series", "variable", "period", "trend", "se_ar1", "units", "n", "lag1_autocorr", "n_eff"]).to_csv(
    os.path.join(OUT, "trends_summary.csv"), index=False, float_format="%.5g", encoding="utf-8-sig")

# ---------------------------------------------------------------- plot
COL = {"Global ocean": "#222222", "Pacific Ocean": "#1f77b4", "Atlantic Ocean": "#2ca02c", "Indian Ocean": "#ff7f0e"}
REG_COL = {"Pacific": "#1f77b4", "Indian": "#ff7f0e", "Atlantic/Caribbean": "#2ca02c", "Singapore Strait": "#9467bd"}
fig, ax = plt.subplots(3, 2, figsize=(14, 13), constrained_layout=True)

a = ax[0, 0]
for name in alt.columns:
    s = alt[name].dropna()
    rate, rate_se, acc = alt_fit[name]
    a.plot(s.index, s.values, "-o", ms=3, lw=1.4, color=COL[name],
           label=f"{name}  ({rate:.1f} ± {rate_se:.1f} mm/yr; accel. {acc:.3f} mm/yr²)")
a.axhline(0, color="grey", lw=0.6)
a.set_title("(a) Absolute sea-level anomaly, satellite altimetry (annual means)")
a.set_ylabel(f"mm, relative to {BASELINE[0]}–{BASELINE[1]}")
a.legend(fontsize=8, loc="upper left")

b = ax[0, 1]
for label in tg.columns:
    reg = tg_region[label]
    s = tg[label].dropna()
    b.plot(s.index, s.values, "-", lw=0.9, alpha=0.75, color=REG_COL[reg])
reg_n = pd.Series(tg_region).value_counts()
for reg in REG_COL:
    if reg in reg_n:
        b.plot([], [], "-", lw=2, color=REG_COL[reg], label=f"{reg} ({reg_n[reg]} gauge{'s' if reg_n[reg] > 1 else ''})")
b.axhline(0, color="grey", lw=0.6)
b.set_title(f"(b) Relative sea-level anomaly at {len(tg.columns)} SIDS tide gauges (includes vertical land motion)")
b.set_ylabel(f"mm, relative to {BASELINE[0]}–{BASELINE[1]}")
b.legend(fontsize=8, loc="lower right")

c = ax[1, 0]
for name in COL:
    m, se = ohc[name], ohc[name + " SE"]
    c.plot(m.index, m.values, lw=1.6, color=COL[name], label=name)
    c.fill_between(m.index, m - se, m + se, color=COL[name], alpha=0.25, lw=0)
c.axhline(0, color="grey", lw=0.6)
c.set_title("(c) Ocean heat content anomaly, 0–2000 m (pentadal means, ±1 s.e.)")
c.set_ylabel(f"ZJ, relative to {BASELINE[0]}–{BASELINE[1]}")
c.legend(fontsize=8, loc="upper left")

d = ax[1, 1]
d.plot(hot["t"], hot["pHcalc_insitu"], ".", ms=3, color="#6a3d9a", alpha=0.6)
k = np.polyfit(hot["t"], hot["pHcalc_insitu"], 1)
d.plot(hot["t"], np.polyval(k, hot["t"]), color="#6a3d9a", lw=1.8, label=f"pH (in situ): {10 * k[0]:+.3f} per decade")
d.set_ylabel("pH (total scale, in situ)", color="#6a3d9a")
d2 = d.twinx()
d2.plot(hot["t"], hot["aragsatcalc_insitu"], ".", ms=3, color="#b15928", alpha=0.5)
k2 = np.polyfit(hot["t"], hot["aragsatcalc_insitu"], 1)
d2.plot(hot["t"], np.polyval(k2, hot["t"]), color="#b15928", lw=1.8,
        label=f"Aragonite saturation: {10 * k2[0]:+.3f} per decade")
d2.set_ylabel("Ω aragonite (in situ)", color="#b15928")
h1, l1 = d.get_legend_handles_labels()
h2, l2 = d2.get_legend_handles_labels()
d.legend(h1 + h2, l1 + l2, fontsize=8, loc="lower left")
d.set_title("(d) Surface-ocean acidification, Station ALOHA (HOT), North Pacific")

e = ax[2, 0]
order = ["Africa", "Asia & Middle East", "Latin America & Caribbean", "Oceania", "Europe",
         "Unallocated / multi-region"]
order = [o for o in order if o in by_region.columns]
e.stackplot(by_region.index, [by_region[o].fillna(0) for o in order], labels=order, alpha=0.85)
e.set_title("(e) Adaptation-related development finance by recipient region (commitments)")
e.set_ylabel(f"USD billion ({PRICE_BASE} constant prices)")
e.set_xlabel("Year")
e.legend(fontsize=8, loc="upper left")

f_ = ax[2, 1]
f_.bar(sids_year.index, sids_year.values, color="#1b9e77", label="SIDS (UN Member States)")
f_.set_ylabel(f"USD billion ({PRICE_BASE} constant prices)")
f3 = f_.twinx()
f3.plot(sids_share.index, sids_share.values, "-o", color="#333333", ms=4, label="Share of all recipients (%)")
f3.set_ylabel("% of total adaptation-related finance")
f3.set_ylim(0, max(10, sids_share.max() * 1.3))
h1, l1 = f_.get_legend_handles_labels()
h2, l2 = f3.get_legend_handles_labels()
f_.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
f_.set_title("(f) Adaptation-related development finance to SIDS (subset of (e), not additive)")
f_.set_xlabel("Year")

for axx in ax.flat:
    axx.grid(alpha=0.3)
for axx in ax[:2].flat:  # common time axis for the ocean panels
    axx.set_xlim(PERIOD[0] - 0.5, PERIOD[1] + 0.5)
    axx.set_xlabel("Year")
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(HERE, f"figure2_open_data.{ext}"), dpi=300)
print("done:", os.path.join(HERE, "figure2_open_data.png"))
