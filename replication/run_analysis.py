#!/usr/bin/env python3
"""Deterministic analyses for the learning-from-prices study.

This program never invokes MATLAB and never executes deposited source.
It evaluates the prespecified analysis design using exact rational arithmetic
for identities and classifications, converting to binary floats only for
display and plotting payloads.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import mpmath as mp
from fractions import Fraction as F
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
HORIZONS = [1, 2, 3, 5, 10, 20, 50, 99, 100, 200, 500, 1000]
BANDS = [F(1, 10), F(1, 20), F(1, 100), F(1, 1000), F(1, 10000)]
A = F(2)
A0 = F(4, 25)
RESULT_PAYLOAD_NAMES = {
    "finite_horizon_sensitivity.json",
    "starting_value_sensitivity.json",
    "boundary_pole_diagnostics.json",
    "price_gap_grid.json",
    "stability_grid_cells.csv",
    "finite_pole_certificate.json",
    "stability_grid.json",
    "persistence_certificate.json",
    "source_sweep_cells.csv",
}
sys.set_int_max_str_digits(0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def frac(x: F) -> dict[str, Any]:
    return {
        "rational": f"{x.numerator}/{x.denominator}",
        "numerator": x.numerator,
        "denominator": x.denominator,
        "decimal": float(x),
    }


def log10_fraction(x: F) -> float | None:
    if x == 0:
        return None
    n, d = abs(x.numerator), x.denominator
    # Leading digits avoid converting huge exact integers to binary floats.
    ns, ds = str(n), str(d)
    nn, dd = ns[:16], ds[:16]
    return (math.log10(int(nn)) + len(ns) - len(nn)) - (
        math.log10(int(dd)) + len(ds) - len(dd)
    )


def exact_metric_record(x: F) -> dict[str, Any]:
    lg = log10_fraction(x)
    return {
        "exact_zero": x == 0,
        "sign": 0 if x == 0 else (1 if x > 0 else -1),
        "log10_absolute": lg,
        "decimal": (
            0.0
            if x == 0
            else (float(x) if lg is not None and -300 < lg < 300 else None)
        ),
        "exact_representation": "closed_form_rational",
    }


def mp_metric_record(x: mp.mpf, *, exact_zero: bool = False) -> dict[str, Any]:
    if exact_zero:
        return {
            "exact_zero": True,
            "log10_absolute": None,
            "scientific": "0",
            "classification_arithmetic": "exact_identity",
        }
    if x == 0:
        raise AssertionError("high-precision cancellation encoded as zero")
    return {
        "exact_zero": False,
        "log10_absolute": float(mp.log10(abs(x))),
        "scientific": mp.nstr(x, 18),
        "classification_arithmetic": "display_only_not_used_for_classification",
    }


def float_display_record(x: float) -> dict[str, Any]:
    return {
        "decimal": (x if x != 0.0 else None),
        "status": (
            "DISPLAY_ONLY" if x != 0.0 else "FLOAT_CANCELLATION_OR_EXACT_CONTROL"
        ),
        "used_for_classification": False,
    }


def render(x: Any) -> Any:
    if isinstance(x, F):
        return frac(x)
    if isinstance(x, dict):
        return {str(k): render(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [render(v) for v in x]
    return x


def dump(name: str, payload: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(render(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def pow2(n: int) -> F:
    return F(2**n) if n >= 0 else F(1, 2 ** (-n))


def vinf(v: Iterable[F]) -> F:
    return max(abs(x) for x in v)


def rel_coeff(v: tuple[F, ...], star: tuple[F, ...]) -> F:
    return vinf(x - y for x, y in zip(v, star)) / vinf(star)


def price(v: tuple[F, F, F, F], x: F) -> F:
    p0, loading, q, pz = v
    return p0 + loading * x + q + pz


def rel_price(
    v: tuple[F, ...],
    star: tuple[F, ...],
    normalization_star: tuple[F, ...] | None = None,
) -> F:
    # Difference and reference are affine in x, so their absolute maxima on
    # the specified interval occur at an endpoint.  This is exactly equivalent
    # to enumerating all 101 points and avoids unnecessary large-integer work.
    grid = [F(1, 2), F(3, 2)]
    num = max(abs(price(v, x) - price(star, x)) for x in grid)
    normalization_star = star if normalization_star is None else normalization_star
    den = max(abs(price(normalization_star, x)) for x in grid)
    return num / den


def private_root(paper: bool) -> tuple[F, F, F, F]:
    a, b, c = F(4, 25), F(8, 25), F(19, 20)
    t = A * A * b * c
    k = a + t * (a + b)
    p0 = t * b / k
    pv = a * (1 + t) / k
    q = A * a * b / k if paper else A * a * b * (1 + t) / (k * (2 + t))
    return p0, pv, q, -A * b * pv


def private_map(v: tuple[F, F, F, F], paper: bool) -> tuple[str, tuple[F, ...] | None]:
    a, b, c = F(4, 25), F(8, 25), F(19, 20)
    p0, pv, q, pz = v
    d = a * b * pv * pv + c * (a + b) * pz * pz
    h = d - a * b * pv
    if d == 0 or pv == 0:
        return "OUTSIDE_DEFINED_DOMAIN", None
    if h == 0:
        return "EXACT_POLE", None
    return "DEFINED", (
        (b * c * pz * pz - a * b * pv * p0) / h,
        a * c * pz * pz / h,
        -a * b * pv * (q + pz) / (h if paper else d),
        -A * a * b * c * pz * pz / h,
    )


def private_ce_start() -> tuple[F, F, F, F]:
    return F(2, 3), F(1, 3), F(0), F(-16, 75)


def private_trajectory(paper: bool, max_k: int = 1000) -> list[tuple[F, F, F, F]]:
    """Exact private path using the scalar core and one q-fiber recurrence."""
    a, b, c = F(4, 25), F(8, 25), F(19, 20)
    t = A * A * b * c
    kval = a + t * (a + b)
    star = private_root(paper)
    state = private_ce_start()
    q = state[2]
    w = F(1) - (1 + t) / (kval * state[1] / a)
    path = []
    for _k in range(1, max_k + 1):
        pv = star[1] / (1 - w)
        y = kval * pv / a
        if paper:
            q = (-q + A * b * pv) / (y - 1)
        else:
            q = -q / y + A * a * b / kval
        w *= -1 / t
        pv_next = star[1] / (1 - w)
        path.append((1 - pv_next, pv_next, q, -A * b * pv_next))
    return path


def partial_root(a: F, b: F, c: F, h: F) -> tuple[F, F, F, F]:
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    return (
        b * e / p,
        a * h * hb / p,
        A * a * b * h * (1 - h) / p,
        -A * a * b * hb / p,
    )


def partial_map(
    v: tuple[F, F, F, F], a: F, b: F, c: F, h: F
) -> tuple[str, tuple[F, ...] | None]:
    p0, ps, q, pz = v
    beta = a / (a + b)
    if ps == 0:
        den = 1 - beta * (1 - h)
        subj = ((1 - beta) / den, h * beta / den, F(0), -A * a * (1 - beta) / den)
    else:
        subj = v
    s0, ss, sq, sz = subj
    qden = ss * ss * (a + b) + c * sz * sz
    if ss == 0 or qden == 0:
        return "OUTSIDE_DEFINED_DOMAIN", None
    gain = a * ss * ss / qden
    cden = h * (1 - gain) + (1 - h) * (1 - beta) * (1 - gain / ss)
    if cden == 0:
        return "EXACT_POLE", None
    return "DEFINED", (
        (h * (1 - gain) * (1 - beta) + (1 - h) * (1 - beta) * (1 - gain / ss)) / cden,
        h * (1 - gain) * beta / cden,
        -(1 - h) * (1 - beta) * gain * (sq + sz) / (ss * cden),
        -A * a * (1 - beta) * (1 - gain) / cden,
    )


def partial_closed(a: F, b: F, c: F, h: F, k: int) -> tuple[str, tuple[F, ...] | None]:
    """Deposited zero-start orbit, indexed by map applications k>=1."""
    if k < 1:
        return "START_ZERO", (F(0), F(0), F(0), F(0))
    star = partial_root(a, b, c, h)
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    eps = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    status, first = partial_map((F(0), F(0), F(0), F(0)), a, b, c, h)
    assert status == "DEFINED" and first is not None
    r = first[2] * (1 + delta) - star[2]
    x = (-eps) ** (k - 1)
    d = 1 + delta * x
    if d == 0:
        return "EXACT_POLE", None
    ps = star[1] / d
    return "DEFINED", (1 - ps, ps, (star[2] + r * x) / d, -A * b * ps / h)


def finite_closed_orbit_pole(a: F, b: F, c: F, h: F) -> tuple[int | None, int]:
    """Return an exact pole K, if any, and the monotone crossing exponent.

    The closed-orbit denominator is 1 + delta*(-epsilon)**n with n=K-1.
    Since epsilon and delta are nonnegative, a zero requires odd n and
    epsilon**n == 1/delta.  For epsilon != 1 the positive powers are strictly
    monotone, so an exact rational scan stops at the unique crossing.
    """
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    epsilon = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    if epsilon == 0 or delta == 0:
        return None, 0
    target = 1 / delta
    if epsilon == 1:
        return ((2 if target == 1 else None), 1)
    if epsilon < 1 and target >= 1:
        return None, 0
    if epsilon > 1 and target <= 1:
        return None, 0
    power = epsilon
    exponent = 1
    if epsilon < 1:
        while power > target:
            power *= epsilon
            exponent += 1
    else:
        while power < target:
            power *= epsilon
            exponent += 1
    if power == target and exponent % 2 == 1:
        return exponent + 1, exponent
    return None, exponent


def run_finite_pole_guard() -> dict[str, Any]:
    exact_poles: list[dict[str, Any]] = []
    maximum_crossing_exponent = 0
    source_checked = 0
    grid_checked = 0
    for hi in range(1, 101):
        h = F(hi, 100)
        pole_k, crossing = finite_closed_orbit_pole(A0, F(3, 25), F(1, 10), h)
        source_checked += 1
        maximum_crossing_exponent = max(maximum_crossing_exponent, crossing)
        if pole_k is not None:
            exact_poles.append(
                {"surface": "deposited_sweep", "phi_index": hi, "K": pole_k}
            )
    for i in range(-4, 5):
        for j in range(-4, 5):
            b, c = A0 * pow2(i), A0 * pow2(j)
            for hi in range(1, 101):
                h = F(hi, 100)
                pole_k, crossing = finite_closed_orbit_pole(A0, b, c, h)
                grid_checked += 1
                maximum_crossing_exponent = max(maximum_crossing_exponent, crossing)
                if pole_k is not None:
                    exact_poles.append(
                        {
                            "surface": "prespecified_grid",
                            "i": i,
                            "j": j,
                            "phi_index": hi,
                            "K": pole_k,
                        }
                    )
    if exact_poles:
        raise AssertionError(
            f"exact finite closed-orbit poles found: {exact_poles[:3]}"
        )
    return {
        "schema": "learning-from-prices-finite-pole-certificate-v1",
        "status": "PASS",
        "deposited_sweep_cells_checked": source_checked,
        "prespecified_grid_cells_checked": grid_checked,
        "exact_finite_poles": 0,
        "maximum_monotone_crossing_exponent_checked": maximum_crossing_exponent,
        "proof_method": "exact rational monotone power scan of 1 + delta*(-epsilon)^(K-1); at most one positive-magnitude crossing when epsilon != 1",
    }


def persistent_entry(errors: list[F], band: F) -> int | str:
    # errors is indexed by integer K=1,...,1000
    suffix_ok = True
    first: int | None = None
    for k in range(1000, 0, -1):
        suffix_ok = suffix_ok and errors[k - 1] <= band
        if suffix_ok:
            first = k
    if first is None:
        return "NOT_ATTAINED_BY_1000"
    for h in HORIZONS:
        if h >= first:
            return h
    return "NOT_ATTAINED_BY_1000"


def persistent_entry_float(errors: list[float], band: float) -> int | str:
    suffix_ok = True
    first = None
    for k in range(1000, 0, -1):
        suffix_ok = suffix_ok and errors[k - 1] <= band
        if suffix_ok:
            first = k
    if first is None:
        return "NOT_ATTAINED_BY_1000"
    return next((h for h in HORIZONS if h >= first), "NOT_ATTAINED_BY_1000")


def fcoeff(v: tuple[float, ...], star: tuple[float, ...]) -> float:
    return max(abs(x - y) for x, y in zip(v, star)) / max(abs(x) for x in star)


def fprice(v: tuple[float, ...], star: tuple[float, ...]) -> float:
    def p(z: tuple[float, ...], x: float) -> float:
        return z[0] + z[1] * x + z[2] + z[3]

    return max(abs(p(v, x) - p(star, x)) for x in (0.5, 1.5)) / max(
        abs(p(star, x)) for x in (0.5, 1.5)
    )


def partial_float_path(a: F, b: F, c: F, h: F) -> list[tuple[float, ...]]:
    star = partial_root(a, b, c, h)
    af, bf, cf, hf = map(float, (a, b, c, h))
    sf = tuple(map(float, star))
    e = hf * hf + 4 * bf * cf
    hb = hf + 4 * bf * cf
    p = bf * e + af * hf * hb
    eps = hf * (1 - hf) / e
    delta = bf * hf * (1 - hf) / p
    status, first = partial_map((F(0),) * 4, a, b, c, h)
    assert status == "DEFINED" and first
    r = float(first[2]) * (1 + delta) - float(star[2])
    path = []
    x = 1.0
    for _k in range(1, 1001):
        d = 1 + float(delta) * x
        ps = sf[1] / d
        path.append((1 - ps, ps, (sf[2] + r * x) / d, -2 * bf * ps / hf))
        x *= -eps
    return path


def partial_error_exact(a: F, b: F, c: F, h: F, k: int) -> F:
    """Closed-form exact infinity-norm error for the special-start orbit."""
    star = partial_root(a, b, c, h)
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    eps = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    status, first = partial_map((F(0),) * 4, a, b, c, h)
    assert status == "DEFINED" and first
    r = first[2] * (1 + delta) - star[2]
    x = (-eps) ** (k - 1)
    den = abs(1 + delta * x)
    if den == 0:
        raise ZeroDivisionError("partial closed-orbit pole")
    base = star[1] * delta
    constant = max(abs(base), abs(r - star[2] * delta), abs(A * b * base / h))
    return constant * abs(x) / (den * vinf(star))


def partial_boundary_distance_exact(a: F, b: F, c: F, h: F, k: int) -> F:
    """Exact normalized distance to the singular-boundary limit."""
    star = partial_root(a, b, c, h)
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    eps = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    if delta == 0:
        raise ValueError("no singular boundary when delta is zero")
    status, first = partial_map((F(0),) * 4, a, b, c, h)
    assert status == "DEFINED" and first
    r = first[2] * (1 + delta) - star[2]
    x = (-eps) ** (k - 1)
    den = abs(1 + delta * x)
    if den == 0:
        raise ZeroDivisionError("partial closed-orbit pole")
    ps = abs(star[1] / den)
    qgap = abs(delta * star[2] - r) / (abs(delta) * den)
    pzgap = abs(A * b * star[1] / (h * den))
    return max(ps, qgap, pzgap) / vinf(star)


def partial_price_error_exact(a: F, b: F, c: F, h: F, k: int) -> F:
    status, v = partial_closed(a, b, c, h, k)
    assert status == "DEFINED" and v
    return rel_price(v, partial_root(a, b, c, h))


def persistent_partial_exact(a: F, b: F, c: F, h: F, band: F) -> int | str:
    """Exact first listed horizon persistent through K=1000.

    In the stable regime, positivity gives delta<1 and epsilon<1.  The even
    and odd error subsequences are therefore separately decreasing, so the
    exact suffix maxima for a listed K<1000 occur at K and K+1.  The specified
    K=1000 suffix has one point.
    """
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    eps = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    if abs(eps) >= 1:
        return "NOT_ATTAINED_BY_1000"
    assert F(0) <= delta < 1
    for k in HORIZONS:
        if partial_error_exact(a, b, c, h, k) <= band and (
            k == 1000 or partial_error_exact(a, b, c, h, k + 1) <= band
        ):
            return k
    return "NOT_ATTAINED_BY_1000"


def persistent_partial_price_exact(a: F, b: F, c: F, h: F, band: F) -> int | str:
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    eps = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    if abs(eps) >= 1:
        return "NOT_ATTAINED_BY_1000"
    assert F(0) <= delta < 1
    for k in HORIZONS:
        if partial_price_error_exact(a, b, c, h, k) <= band and (
            k == 1000 or partial_price_error_exact(a, b, c, h, k + 1) <= band
        ):
            return k
    return "NOT_ATTAINED_BY_1000"


def private_float_path(paper: bool) -> list[tuple[float, ...]]:
    a, b, c = 0.16, 0.32, 0.95
    state = (2 / 3, 1 / 3, 0.0, -16 / 75)
    out = []
    for _k in range(1, 1001):
        p0, pv, q, pz = state
        d = a * b * pv * pv + c * (a + b) * pz * pz
        hh = d - a * b * pv
        qden = hh if paper else d
        state = (
            (b * c * pz * pz - a * b * pv * p0) / hh,
            a * c * pz * pz / hh,
            -a * b * pv * (q + pz) / qden,
            -2 * a * b * c * pz * pz / hh,
        )
        out.append(state)
    return out


def private_mp_path(paper: bool) -> list[tuple[mp.mpf, ...]]:
    mp.mp.dps = 100
    a, b, c, Amp = map(mp.mpf, ("0.16", "0.32", "0.95", "2"))
    state = tuple(map(mp.mpf, (mp.mpf(2) / 3, mp.mpf(1) / 3, 0, mp.mpf(-16) / 75)))
    out = []
    for _k in range(1, 1001):
        p0, pv, q, pz = state
        d = a * b * pv * pv + c * (a + b) * pz * pz
        hh = d - a * b * pv
        state = (
            (b * c * pz * pz - a * b * pv * p0) / hh,
            a * c * pz * pz / hh,
            -a * b * pv * (q + pz) / (hh if paper else d),
            -Amp * a * b * c * pz * pz / hh,
        )
        out.append(state)
    return out


def private_exact_path(paper: bool, n: int = 120) -> list[tuple[F, ...]]:
    state = private_ce_start()
    out = []
    for _k in range(1, n + 1):
        status, nxt = private_map(state, paper)
        assert status == "DEFINED" and nxt
        state = nxt
        out.append(state)
    return out


def private_persistent_exact(
    path: list[tuple[F, ...]],
    star: tuple[F, ...],
    band: F,
    price_metric: bool = False,
    normalization_star: tuple[F, ...] | None = None,
) -> int | str:
    errors = [
        rel_price(v, star, normalization_star) if price_metric else rel_coeff(v, star)
        for v in path
    ]
    # By K=120 both exact scalar/fiber modes are strictly within every band and
    # contract thereafter at the t>1 anchor; scan the exact finite prefix.
    if errors[-1] > F(1, 10**6):
        raise AssertionError("the exact path has not entered the certified tail region")
    suffix = True
    raw = None
    for k in range(len(errors), 0, -1):
        suffix = suffix and errors[k - 1] <= band
        if suffix:
            raw = k
    if raw is None:
        return "NOT_ATTAINED_BY_1000"
    return next((h for h in HORIZONS if h >= raw), "NOT_ATTAINED_BY_1000")


def run_finite_horizon_sensitivity() -> dict[str, Any]:
    a, b, c, h = F(4, 25), F(3, 25), F(1, 10), F(3, 5)
    branches: dict[str, Any] = {}
    for label, paper in (("article_updater_H", True), ("deposited_D", False)):
        star = private_root(paper)
        normalization_star = private_root(True)
        path = private_mp_path(paper)
        stmp = tuple(mp.mpf(x.numerator) / x.denominator for x in star)
        normmp = tuple(mp.mpf(x.numerator) / x.denominator for x in normalization_star)

        def mc(v):
            return max(abs(x - y) for x, y in zip(v, stmp)) / max(abs(x) for x in stmp)

        def mpprice(v):
            def p(z, x):
                return z[0] + z[1] * x + z[2] + z[3]

            return max(
                abs(p(v, x) - p(stmp, x)) for x in (mp.mpf(".5"), mp.mpf("1.5"))
            ) / max(abs(p(normmp, x)) for x in (mp.mpf(".5"), mp.mpf("1.5")))

        coeff = [mc(state) for state in path]
        prices = [mpprice(state) for state in path]
        xpath = private_exact_path(paper)
        branches[label] = {
            "horizons": {
                str(k): {
                    "coefficient_error": mp_metric_record(coeff[k - 1]),
                    "price_error": mp_metric_record(prices[k - 1]),
                }
                for k in HORIZONS
            },
            "persistent_entry": {
                f"{float(band):g}": {
                    "coefficient": private_persistent_exact(xpath, star, band, False),
                    "price": private_persistent_exact(
                        xpath, star, band, True, normalization_star
                    ),
                }
                for band in BANDS
            },
        }
    branches["partial_revelation_benchmark"] = {
        "horizons": {
            str(k): {
                "coefficient_error": exact_metric_record(
                    partial_error_exact(a, b, c, h, k)
                ),
                "price_error": exact_metric_record(
                    partial_price_error_exact(a, b, c, h, k)
                ),
            }
            for k in HORIZONS
        },
        "persistent_entry": {
            f"{float(band):g}": {
                "coefficient": persistent_partial_exact(a, b, c, h, band),
                "price": persistent_partial_price_exact(a, b, c, h, band),
            }
            for band in BANDS
        },
    }
    return {
        "schema": "learning-from-prices-finite-horizon-v1",
        "indexing": "K is map applications",
        "price_error_normalization": "article/updater-H fixed-price sup norm on [0.5,1.5] for both private branches; corresponding partial fixed-price sup norm for the partial branch",
        "branches": branches,
    }


def iterate_start(
    mapper,
    start: tuple[F, ...],
    star: tuple[F, ...],
    price_normalizer: tuple[F, ...] | None = None,
) -> dict[str, Any]:
    """Classify a named starting value using exact rational map arithmetic."""
    if start == star:
        rows = {
            "0": {"status": "DEFINED", "coefficient_error": exact_metric_record(F(0))},
            **{
                str(k): {
                    "status": "DEFINED",
                    "coefficient_error": exact_metric_record(F(0)),
                    "price_error": exact_metric_record(F(0)),
                }
                for k in HORIZONS
            },
        }
        return {
            "terminal_status": "DEFINED_THROUGH_1000",
            "horizons": rows,
            "classification_arithmetic": "exact_rational",
        }
    state = start
    rows: dict[str, Any] = {
        "0": {
            "status": "DEFINED",
            "coefficient_error": exact_metric_record(rel_coeff(state, star)),
        }
    }
    for k in range(1, 1001):
        status, nxt = mapper(state)
        if status != "DEFINED" or nxt is None:
            rows[str(k)] = {"status": status}
            return {
                "terminal_status": status,
                "terminal_k": k,
                "horizons": {q: rows[q] for q in rows if int(q) in [0] + HORIZONS},
                "classification_arithmetic": "exact_rational",
            }
        state = nxt
        if k in HORIZONS:
            rows[str(k)] = {
                "status": "DEFINED",
                "coefficient_error": exact_metric_record(rel_coeff(state, star)),
                "price_error": exact_metric_record(
                    rel_price(state, star, price_normalizer)
                ),
            }
    return {
        "terminal_status": "DEFINED_THROUGH_1000",
        "horizons": rows,
        "classification_arithmetic": "exact_rational",
    }


def not_applicable(reason: str) -> dict[str, Any]:
    return {"terminal_status": "NOT_APPLICABLE", "reason": reason}


def iterate_private_start(
    paper: bool, start: tuple[F, ...], star: tuple[F, ...]
) -> dict[str, Any]:
    """Private-map start: exact domain classification, high-precision display."""
    if start == star:
        return iterate_start(
            lambda v: private_map(v, paper), start, star, private_root(True)
        )
    first_status, first = private_map(start, paper)
    if first_status != "DEFINED" or first is None:
        return {
            "terminal_status": first_status,
            "terminal_k": 1,
            "horizons": {
                "0": {
                    "status": "DEFINED",
                    "coefficient_error": exact_metric_record(rel_coeff(start, star)),
                },
                "1": {"status": first_status},
            },
            "classification_arithmetic": "exact_rational",
        }

    a, b, c = F(4, 25), F(8, 25), F(19, 20)
    t = A * A * b * c
    kval = a + t * (a + b)
    w = 1 - (1 + t) / (kval * first[1] / a)
    terminal_status = "DEFINED_THROUGH_1000"
    terminal_k = None
    for state_k in range(1, 1000):
        if w == -t:
            terminal_status, terminal_k = "EXACT_POLE", state_k + 1
            break
        if w == 1:
            terminal_status, terminal_k = "CHART_INFINITY", state_k
            break
        w *= -1 / t

    exact_states: dict[int, tuple[F, ...]] = {}
    state = start
    exact_limit = min(120, (terminal_k - 1 if terminal_k is not None else 120))
    for k in range(1, exact_limit + 1):
        status, nxt = private_map(state, paper)
        assert status == "DEFINED" and nxt is not None
        state = nxt
        exact_states[k] = state

    mp.mp.dps = 100
    amp, bmp, cmp, Amp = (
        mp.mpf(a.numerator) / a.denominator,
        mp.mpf(b.numerator) / b.denominator,
        mp.mpf(c.numerator) / c.denominator,
        mp.mpf(A.numerator) / A.denominator,
    )
    mpstate = tuple(mp.mpf(x.numerator) / x.denominator for x in start)
    mpstar = tuple(mp.mpf(x.numerator) / x.denominator for x in star)
    normstar = tuple(mp.mpf(x.numerator) / x.denominator for x in private_root(True))
    mp_states: dict[int, tuple[mp.mpf, ...]] = {}
    mp_limit = terminal_k - 1 if terminal_k is not None else 1000
    for k in range(1, mp_limit + 1):
        p0, pv, q, pz = mpstate
        d = amp * bmp * pv * pv + cmp * (amp + bmp) * pz * pz
        hh = d - amp * bmp * pv
        mpstate = (
            (bmp * cmp * pz * pz - amp * bmp * pv * p0) / hh,
            amp * cmp * pz * pz / hh,
            -amp * bmp * pv * (q + pz) / (hh if paper else d),
            -Amp * amp * bmp * cmp * pz * pz / hh,
        )
        if k in HORIZONS:
            mp_states[k] = mpstate

    def mp_coeff(v):
        return max(abs(x - y) for x, y in zip(v, mpstar)) / max(abs(x) for x in mpstar)

    def mp_price_error(v):
        def p(z, x):
            return z[0] + z[1] * x + z[2] + z[3]

        xs = (mp.mpf("0.5"), mp.mpf("1.5"))
        return max(abs(p(v, x) - p(mpstar, x)) for x in xs) / max(
            abs(p(normstar, x)) for x in xs
        )

    rows = {
        "0": {
            "status": "DEFINED",
            "coefficient_error": exact_metric_record(rel_coeff(start, star)),
        }
    }
    for k in HORIZONS:
        if terminal_k is not None and k >= terminal_k:
            continue
        if k in exact_states:
            rows[str(k)] = {
                "status": "DEFINED",
                "coefficient_error": exact_metric_record(
                    rel_coeff(exact_states[k], star)
                ),
                "price_error": exact_metric_record(
                    rel_price(exact_states[k], star, private_root(True))
                ),
            }
        else:
            rows[str(k)] = {
                "status": "DEFINED",
                "coefficient_error": mp_metric_record(mp_coeff(mp_states[k])),
                "price_error": mp_metric_record(mp_price_error(mp_states[k])),
            }
    result = {
        "terminal_status": terminal_status,
        "horizons": rows,
        "classification_arithmetic": "exact_rational_core_domain; 100-digit display metrics beyond K=120",
    }
    if terminal_k is not None:
        result["terminal_k"] = terminal_k
    return result


def run_starting_value_sensitivity() -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": "learning-from-prices-starting-values-v1",
        "price_error_normalization": "article/updater-H fixed-price sup norm on [0.5,1.5] for both private branches; corresponding partial fixed-price sup norm for the partial branch",
        "branches": {},
    }
    a, b, c, h = F(4, 25), F(3, 25), F(1, 10), F(3, 5)
    pstar = partial_root(a, b, c, h)
    scales = [
        ("minus_full", F(0)),
        ("minus_quarter", F(3, 4)),
        ("fixed", F(1)),
        ("plus_quarter", F(5, 4)),
        ("plus_full", F(2)),
    ]
    partial = {
        "deposited_zero": iterate_start(
            lambda v: partial_map(v, a, b, c, h), (F(0), F(0), F(0), F(0)), pstar
        ),
        "certainty_equivalent": not_applicable(
            "private-map start; not a partial-map start"
        ),
        "projector_direction_starts": not_applicable(
            "the scalar w chart applies only to the shared private-map core"
        ),
    }
    for name, s in scales:
        partial[name] = iterate_start(
            lambda v: partial_map(v, a, b, c, h), tuple(s * x for x in pstar), pstar
        )
    out["branches"]["partial_revelation_benchmark"] = partial
    for label, paper in (("article_updater_H", True), ("deposited_D", False)):
        star = private_root(paper)
        branch = {
            "deposited_zero": not_applicable(
                "the deposited zero/special-first-update start belongs to the partial map"
            ),
            "certainty_equivalent": iterate_private_start(
                paper, private_ce_start(), star
            ),
            "projector_direction_starts": {
                "terminal_status": "APPLICABLE_VIA_SHARED_PRIVATE_SCALAR_REDUCTION",
                "ledger": "private_scalar_starts",
                "estimand_scope": "scalar_chart_domain_safety_only",
                "full_vector_completion": "SCALAR_REDUCTION_ONLY",
                "coefficient_error": {"status": "NOT_APPLICABLE"},
                "price_error": {"status": "NOT_APPLICABLE"},
            },
        }
        for name, s in scales:
            if s == 0:
                branch[name] = {
                    "terminal_status": "OUTSIDE_DEFINED_DOMAIN",
                    "terminal_k": 0,
                    "horizons": {"0": {"status": "OUTSIDE_DEFINED_DOMAIN"}},
                    "classification_arithmetic": "exact_rational",
                }
            else:
                branch[name] = iterate_private_start(
                    paper, tuple(s * x for x in star), star
                )
        out["branches"][label] = branch
    t = F(152, 125)
    out["private_scalar_starts"] = {}
    for w0 in [F(-4), F(-2), F(-1, 2), F(0), F(1, 2), F(2), F(4)]:
        w = w0
        status = "DEFINED_THROUGH_1000"
        terminal = None
        for k in range(0, 1001):
            if w == -t:
                status, terminal = "EXACT_POLE", k
                break
            if w == 1:
                status, terminal = "CHART_INFINITY", k
                break
            w *= -1 / t
        out["private_scalar_starts"][str(w0)] = {
            "status": status,
            "terminal_k": terminal,
            "classification_arithmetic": "exact_rational",
            "applicable_branches": ["article_updater_H", "deposited_D"],
            "estimand_scope": "scalar_chart_domain_safety_only",
            "full_vector_completion": "SCALAR_REDUCTION_ONLY",
            "coefficient_error": {
                "status": "NOT_APPLICABLE",
                "reason": "a full-vector e/q completion is not defined for this diagnostic",
            },
            "price_error": {
                "status": "NOT_APPLICABLE",
                "reason": "a full-vector e/q completion is not defined for this diagnostic",
            },
        }
    return out


def private_scalar_branch_diagnostics(start_w: F, paper: bool) -> dict[str, Any]:
    """Classify one scalar start and certify the branch's finite tail.

    Each branch begins at its own exact fixed q loading. Reporting both branches
    resolves the q-fiber ambiguity in this scalar-only domain diagnostic.
    """
    t = F(152, 125)
    a, b = F(4, 25), F(8, 25)
    kval = a + t * (a + b)
    pvstar = a * (1 + t) / kval
    star = private_root(paper)
    q = star[2]

    # Scalar-domain classification and denominator margin are exact at every K.
    scalar_status = "DEFINED_THROUGH_1000"
    terminal_k = None
    min_margin: F | None = None
    w = start_w
    for k in range(0, 1001):
        if w == 1:
            scalar_status, terminal_k = "CHART_INFINITY", k
            break
        margin = abs(w + t) / (abs(w) + t)
        min_margin = margin if min_margin is None else min(min_margin, margin)
        if w == -t:
            scalar_status, terminal_k = "EXACT_POLE", k
            break
        w *= -1 / t

    scan_end = terminal_k if terminal_k is not None else 200
    w = start_w
    max_coefficient = F(0)
    errors: list[F] = []
    states_scanned = 0
    for k in range(0, scan_end + 1):
        if w == 1:
            break
        pv = pvstar / (1 - w)
        state = (1 - pv, pv, q, -A * b * pv)
        max_coefficient = max(max_coefficient, *(abs(x) for x in state))
        errors.append(rel_coeff(state, star))
        states_scanned += 1
        if w == -t or k == scan_end:
            break
        y = kval * pv / a
        q = ((-q + A * b * pv) / (y - 1)) if paper else (-q / y + A * a * b / kval)
        w *= -1 / t

    if terminal_k is not None:
        return {
            "q_initialization": "branch_exact_fixed_loading",
            "status": scalar_status,
            "terminal_k": terminal_k,
            "maximum_absolute_coefficient_through_defined_states": exact_metric_record(
                max_coefficient
            ),
            "persistent_entry": {
                f"{float(band):g}": "NOT_ATTAINED_BY_1000" for band in BANDS
            },
            "defined_states_scanned": states_scanned,
            "classification_arithmetic": "exact_rational",
        }

    # At K=200 the core is in a small invariant neighborhood.  These exact
    # rational inequalities certify that no later coefficient can leave a band
    # or exceed the maximum already observed. Exact fractions beyond K=200 do
    # not need to be constructed.
    w200 = start_w * (-F(1, 1) / t) ** 200
    u = abs(w200)
    assert u < 1 and len(errors) == 201
    q_error = abs(q - star[2])
    if paper:
        contraction = (1 + u) / (t - u)
        assert contraction < 1
        q_tail_bound = q_error
    else:
        q_tail_bound = max(q_error, u * abs(star[2]) / (t - u))
    v_tail = abs(pvstar) / (1 - u)
    core_error_tail = abs(pvstar) * u / (1 - u)
    relative_tail_bound = max(
        core_error_tail, A * b * core_error_tail, q_tail_bound
    ) / vinf(star)
    absolute_tail_bound = max(
        1 + v_tail, v_tail, abs(star[2]) + q_tail_bound, A * b * v_tail
    )
    assert relative_tail_bound < F(1, 10000)
    assert max_coefficient >= absolute_tail_bound

    persistent: dict[str, int | str] = {}
    for band in BANDS:
        first_persistent_horizon: int | str = "NOT_ATTAINED_BY_1000"
        for horizon in HORIZONS:
            if horizon <= 200:
                ok = (
                    all(error <= band for error in errors[horizon:])
                    and relative_tail_bound <= band
                )
            else:
                ok = relative_tail_bound <= band
            if ok:
                first_persistent_horizon = horizon
                break
        persistent[f"{float(band):g}"] = first_persistent_horizon
    return {
        "q_initialization": "branch_exact_fixed_loading",
        "status": scalar_status,
        "terminal_k": terminal_k,
        "maximum_absolute_coefficient_through_k1000": exact_metric_record(
            max_coefficient
        ),
        "maximum_attained_by_k200": True,
        "tail_absolute_coefficient_upper_bound": exact_metric_record(
            absolute_tail_bound
        ),
        "tail_relative_error_upper_bound": exact_metric_record(relative_tail_bound),
        "persistent_entry": persistent,
        "classification_arithmetic": "exact_rational_prefix_and_exact_invariant_tail_bound",
    }


def run_boundary_pole_diagnostics() -> dict[str, Any]:
    offsets = [F(0)] + [s * F(1, 10**k) for k in range(1, 9) for s in (1, -1)]
    boundary = []
    for d in offsets:
        eps = 1 + d
        errors = [abs(eps) ** k for k in range(1, 1001)]
        maximum_perturbation = max(F(1), abs(eps) ** 1000)
        boundary.append(
            {
                "offset": d,
                "epsilon": eps,
                "classification": "STABLE"
                if abs(eps) < 1
                else ("BOUNDARY" if abs(eps) == 1 else "UNSTABLE"),
                "minimum_normalized_denominator_margin": {
                    "status": "NOT_APPLICABLE_SYNTHETIC_PROJECTOR_EXPERIMENT"
                },
                "maximum_absolute_coefficient": {
                    "status": "NOT_APPLICABLE_SYNTHETIC_NORMALIZED_PERTURBATION"
                },
                "maximum_normalized_perturbation_coefficient": exact_metric_record(
                    maximum_perturbation
                ),
                "horizons": {str(k): errors[k - 1] for k in HORIZONS},
                "persistent_entry": {
                    f"{float(b):g}": persistent_entry(errors, b) for b in BANDS
                },
                "classification_arithmetic": "exact_rational",
            }
        )
    t = F(152, 125)
    pole = []
    for m in range(1, 6):
        base = (-t) ** m
        for d in offsets:
            start_exact = base + d
            # The minimum margin is shared by the two q fibers and exact.
            w = start_exact
            min_margin: F | None = None
            scalar_status = "DEFINED_THROUGH_1000"
            terminal_k = None
            for k in range(0, 1001):
                if w == 1:
                    scalar_status, terminal_k = "CHART_INFINITY", k
                    break
                margin = abs(w + t) / (abs(w) + t)
                min_margin = margin if min_margin is None else min(min_margin, margin)
                if w == -t:
                    scalar_status, terminal_k = "EXACT_POLE", k
                    break
                w *= -1 / t
            pole.append(
                {
                    "preimage_power": m,
                    "offset": d,
                    "start_w": start_exact,
                    "status": scalar_status,
                    "terminal_k": terminal_k,
                    "minimum_normalized_denominator_margin": exact_metric_record(
                        min_margin if min_margin is not None else F(0)
                    ),
                    "branches": {
                        "article_updater_H": private_scalar_branch_diagnostics(
                            start_exact, True
                        ),
                        "deposited_D": private_scalar_branch_diagnostics(
                            start_exact, False
                        ),
                    },
                    "classification_arithmetic": "exact_rational",
                }
            )
    return {
        "schema": "learning-from-prices-boundary-pole-v1",
        "boundary_cases": boundary,
        "pole_preimage_cases": pole,
        "true_pole_w": -t,
        "chart_infinity_w": F(1),
        "q_fiber_policy": "both branches, each initialized at its own exact fixed q loading",
    }


def grid_metrics(
    left: tuple[F, ...], right: tuple[F, ...], normalization: tuple[F, ...]
) -> dict[str, Any]:
    xs = [F(i, 100) for i in range(50, 151)]
    gaps = [abs(price(left, x) - price(right, x)) for x in xs]
    den = max(abs(price(normalization, x)) for x in xs)
    rms2 = sum((g * g for g in gaps), F(0)) / len(gaps)
    if all(g == gaps[0] for g in gaps):
        rms: Any = gaps[0]
    else:
        mp.mp.dps = 100
        value = mp.sqrt(mp.mpf(rms2.numerator) / rms2.denominator)
        rms = {
            "scientific": mp.nstr(value, 30),
            "squared_exact": rms2,
            "classification_arithmetic": "not_applicable_metric_only",
        }
    return {
        "absolute_sup": max(gaps),
        "relative_sup": max(gaps) / den,
        "relative_normalization": "article_updater_H_fixed_price_sup_norm",
        "rms": rms,
        "rms_squared_exact": rms2,
        "gap_at_x_1": abs(price(left, F(1)) - price(right, F(1))),
    }


def run_price_gap_grid() -> dict[str, Any]:
    article_h = private_root(True)
    deposited_d = private_root(False)
    pp = private_mp_path(True)
    lp = private_mp_path(False)
    mp.mp.dps = 100
    pstar = tuple(mp.mpf(x.numerator) / x.denominator for x in article_h)
    den = max(
        abs(pstar[0] + pstar[1] * x + pstar[2] + pstar[3])
        for x in (mp.mpf("0.5"), mp.mpf("1.5"))
    )
    paths = {}
    for k in HORIZONS:
        gap = abs(lp[k - 1][2] - pp[k - 1][2])
        paths[str(k)] = {
            "absolute_sup": mp_metric_record(gap),
            "relative_sup": mp_metric_record(gap / den),
            "rms": mp_metric_record(gap),
            "gap_at_x_1": mp_metric_record(gap),
            "reason_metrics_coincide": "the two paths differ only in q, so the price gap is constant on the prespecified grid",
        }
    st_p, p1 = private_map(private_ce_start(), True)
    st_l, l1 = private_map(private_ce_start(), False)
    assert st_p == st_l == "DEFINED" and p1 is not None and l1 is not None
    first_exact = grid_metrics(l1, p1, article_h)
    assert first_exact["relative_sup"] == F(750000, 3204433)
    paths["1"]["exact_rational_metrics"] = first_exact
    return {
        "schema": "learning-from-prices-price-gap-v1",
        "grid": {"start": F(1, 2), "stop": F(3, 2), "step": F(1, 100), "count": 101},
        "relative_normalization": "article_updater_H_fixed_price_sup_norm",
        "fixed_point": grid_metrics(deposited_d, article_h, article_h),
        "finite_paths": paths,
        "metric_arithmetic": "100-digit deterministic reporting; K=1 and fixed point additionally retain exact rational metrics",
    }


def partial_errors(
    a: F, b: F, c: F, h: F
) -> tuple[list[F], list[F], tuple[F, ...], F, F]:
    star = partial_root(a, b, c, h)
    coeff = []
    magnitude = []
    for k in range(1, 1001):
        status, v = partial_closed(a, b, c, h, k)
        if status != "DEFINED" or v is None:
            raise AssertionError((a, b, c, h, k, status))
        coeff.append(rel_coeff(v, star))
        magnitude.append(vinf(v) / vinf(star))
    eps = h * (1 - h) / (h * h + A * A * b * c)
    return coeff, magnitude, star, eps, min(F(1), abs(1 - eps))


STABILITY_HORIZONS = [1, 2, 3, 10, 99, 100]
STABILITY_BANDS = [F(1, 20), F(1, 100), F(1, 1000), F(1, 10000)]


def partial_stability_cell(
    a: F, b: F, c: F, h: F, identifiers: dict[str, Any]
) -> dict[str, Any]:
    eps = h * (1 - h) / (h * h + A * A * b * c)
    asym = "STABLE" if abs(eps) < 1 else ("BOUNDARY" if abs(eps) == 1 else "UNSTABLE")
    error_k1000 = partial_error_exact(a, b, c, h, 1000)
    boundary_distance = (
        partial_boundary_distance_exact(a, b, c, h, 1000)
        if asym == "UNSTABLE"
        else None
    )
    if asym == "STABLE" and error_k1000 <= F(1, 20):
        limiting = "NONZERO_FIXED_POINT"
    elif (
        asym == "UNSTABLE"
        and boundary_distance is not None
        and boundary_distance <= F(1, 20)
    ):
        limiting = "SINGULAR_BOUNDARY_LIMIT"
    else:
        limiting = "NO_LIMITING_OBJECT_RESOLVED_BY_1000"
    expected = (
        "NONZERO_FIXED_POINT"
        if asym == "STABLE"
        else (
            "BOUNDARY_NO_CONVERGENCE"
            if asym == "BOUNDARY"
            else "SINGULAR_BOUNDARY_LIMIT"
        )
    )
    exact_errors = {k: partial_error_exact(a, b, c, h, k) for k in STABILITY_HORIZONS}
    agreement = {
        str(k): {
            f"{float(band):g}": (
                (exact_errors[k] <= band) == (expected == "NONZERO_FIXED_POINT")
            )
            for band in STABILITY_BANDS
        }
        for k in STABILITY_HORIZONS
    }
    return {
        **identifiers,
        "epsilon": eps,
        "asymptotic": asym,
        "exact_asymptotic_limiting_object": expected,
        "finite_horizon_limiting_object_at_k1000": limiting,
        "boundary_distance_k1000": (
            exact_metric_record(boundary_distance)
            if boundary_distance is not None
            else {"status": "NOT_APPLICABLE"}
        ),
        "error_k1000": exact_metric_record(error_k1000),
        "errors": {
            str(k): exact_metric_record(exact_errors[k]) for k in STABILITY_HORIZONS
        },
        "persistent_entry": {
            f"{float(band):g}": persistent_partial_exact(a, b, c, h, band)
            for band in STABILITY_BANDS
        },
        "agreement": agreement,
        "classification_arithmetic": "exact_rational",
    }


def summarize_stability(
    cells: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    counts = {"STABLE": 0, "BOUNDARY": 0, "UNSTABLE": 0}
    selected: dict[str, int] = {}
    for cell in cells:
        counts[cell["asymptotic"]] += 1
        key = cell["finite_horizon_limiting_object_at_k1000"]
        selected[key] = selected.get(key, 0) + 1
    return counts, selected


def run_stability_grid() -> dict[str, Any]:
    source = []
    for hi in range(1, 101):
        source.append(
            partial_stability_cell(
                A0, F(3, 25), F(1, 10), F(hi, 100), {"phi_index": hi}
            )
        )
    source_counts, source_selected = summarize_stability(source)
    assert source_counts == {"STABLE": 61, "BOUNDARY": 0, "UNSTABLE": 39}, source_counts

    cells = []
    for i in range(-4, 5):
        for j in range(-4, 5):
            b = A0 * pow2(i)
            c = A0 * pow2(j)
            for hi in range(1, 101):
                cells.append(
                    partial_stability_cell(
                        A0, b, c, F(hi, 100), {"i": i, "j": j, "phi_index": hi}
                    )
                )
    counts, selected = summarize_stability(cells)
    assert counts == {"STABLE": 6267, "BOUNDARY": 0, "UNSTABLE": 1833}, counts
    return {
        "schema": "learning-from-prices-stability-grid-v1",
        "source_sweep": {
            "parameters": {"a": A0, "b": F(3, 25), "c": F(1, 10)},
            "counts": source_counts,
            "finite_horizon_limiting_objects_at_k1000": source_selected,
            "cells": source,
        },
        "counts": counts,
        "finite_horizon_limiting_objects_at_k1000": selected,
        "cells": cells,
        "error_metric": "coefficient infinity-norm error normalized by the exact nonzero fixed-point coefficient infinity norm",
        "persistent_band_metric": "coefficient infinity-norm error normalized by the exact nonzero fixed-point coefficient infinity norm",
        "classification_arithmetic": "exact rational for every source-sweep and 8,100-grid decision",
    }


def expected_persistent_partial(a: F, b: F, c: F, h: F, band: F) -> int | str:
    """Recheck the prescribed persistent-band rule through K=1000 exactly."""
    e = h * h + A * A * b * c
    hb = h + A * A * b * c
    p = b * e + a * h * hb
    epsilon = h * (1 - h) / e
    delta = b * h * (1 - h) / p
    if epsilon >= 1:
        return "NOT_ATTAINED_BY_1000"
    assert F(0) <= delta < 1
    for k in HORIZONS:
        candidates = [partial_error_exact(a, b, c, h, k)]
        if k < 1000:
            candidates.append(partial_error_exact(a, b, c, h, k + 1))
        if max(candidates) <= band:
            return k
    return "NOT_ATTAINED_BY_1000"


def run_persistence_guard(stability_results: dict[str, Any]) -> dict[str, Any]:
    """Certify every persistent-band classification and its proof domain."""
    summaries: dict[str, dict[str, Any]] = {}
    for surface, cells in (
        ("deposited_sweep", stability_results["source_sweep"]["cells"]),
        ("prespecified_grid", stability_results["cells"]),
    ):
        stable = unstable = checks = mismatches = delta_ge_one = (
            unstable_endpoint_pass
        ) = 0
        minimum_unstable_endpoint: F | None = None
        for cell in cells:
            h = F(cell["phi_index"], 100)
            if surface == "deposited_sweep":
                b, c = F(3, 25), F(1, 10)
            else:
                b, c = A0 * pow2(cell["i"]), A0 * pow2(cell["j"])
            e = h * h + A * A * b * c
            hb = h + A * A * b * c
            p = b * e + A0 * h * hb
            epsilon = h * (1 - h) / e
            delta = b * h * (1 - h) / p
            if epsilon < 1:
                stable += 1
                if delta >= 1:
                    delta_ge_one += 1
                for band in STABILITY_BANDS:
                    checks += 1
                    observed = cell["persistent_entry"][f"{float(band):g}"]
                    expected = expected_persistent_partial(A0, b, c, h, band)
                    mismatches += int(observed != expected)
            else:
                unstable += 1
                endpoint = partial_error_exact(A0, b, c, h, 1000)
                minimum_unstable_endpoint = (
                    endpoint
                    if minimum_unstable_endpoint is None
                    else min(minimum_unstable_endpoint, endpoint)
                )
                unstable_endpoint_pass += int(endpoint > max(STABILITY_BANDS))
        if delta_ge_one or mismatches or unstable_endpoint_pass != unstable:
            raise AssertionError(
                (surface, delta_ge_one, mismatches, unstable_endpoint_pass, unstable)
            )
        summaries[surface] = {
            "stable_cells": stable,
            "unstable_cells": unstable,
            "stable_cell_band_checks": checks,
            "stable_delta_greater_or_equal_one": delta_ge_one,
            "persistent_classifier_mismatches": mismatches,
            "unstable_k1000_above_largest_band": unstable_endpoint_pass,
            "minimum_unstable_k1000_error": exact_metric_record(
                minimum_unstable_endpoint
            )
            if minimum_unstable_endpoint is not None
            else {"status": "NOT_APPLICABLE"},
        }
    assert summaries["deposited_sweep"]["stable_cell_band_checks"] == 244
    assert summaries["prespecified_grid"]["stable_cell_band_checks"] == 25068
    return {
        "schema": "learning-from-prices-persistence-certificate-v1",
        "status": "PASS",
        "definition": "persistent at a listed K means inside the band at every integer iterate K through 1000",
        "guard_scope": "exact proof-domain and implementation-consistency check based on the same derived error identity",
        "proof": "for stable cells, positivity implies 0<=delta<1 and 0<=epsilon<1, so the exact even and odd error subsequences are separately decreasing and their suffix maxima occur at K and K+1",
        "surfaces": summaries,
    }


def write_csvs(stability_results: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "stability_grid_cells.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            [
                "i",
                "j",
                "phi_index",
                "epsilon",
                "asymptotic",
                "finite_horizon_limiting_object_at_k1000",
                "log10_error_k1",
                "log10_error_k10",
                "log10_error_k99",
                "log10_error_k100",
            ]
        )
        for r in stability_results["cells"]:
            w.writerow(
                [
                    r["i"],
                    r["j"],
                    r["phi_index"],
                    str(r["epsilon"]),
                    r["asymptotic"],
                    r["finite_horizon_limiting_object_at_k1000"],
                    r["errors"]["1"]["log10_absolute"],
                    r["errors"]["10"]["log10_absolute"],
                    r["errors"]["99"]["log10_absolute"],
                    r["errors"]["100"]["log10_absolute"],
                ]
            )
    with (OUT / "source_sweep_cells.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            [
                "phi_index",
                "epsilon",
                "asymptotic",
                "finite_horizon_limiting_object_at_k1000",
                "log10_error_k1",
                "log10_error_k2",
                "log10_error_k3",
                "log10_error_k10",
                "log10_error_k99",
                "log10_error_k100",
            ]
        )
        for r in stability_results["source_sweep"]["cells"]:
            w.writerow(
                [
                    r["phi_index"],
                    str(r["epsilon"]),
                    r["asymptotic"],
                    r["finite_horizon_limiting_object_at_k1000"],
                    *[
                        r["errors"][str(k)]["log10_absolute"]
                        for k in STABILITY_HORIZONS
                    ],
                ]
            )


def main() -> None:
    finite_horizon = run_finite_horizon_sensitivity()
    dump("finite_horizon_sensitivity.json", finite_horizon)
    starting_values = run_starting_value_sensitivity()
    dump("starting_value_sensitivity.json", starting_values)
    boundary_pole = run_boundary_pole_diagnostics()
    dump("boundary_pole_diagnostics.json", boundary_pole)
    price_gap = run_price_gap_grid()
    dump("price_gap_grid.json", price_gap)
    stability = run_stability_grid()
    dump("stability_grid.json", stability)
    write_csvs(stability)
    dump("finite_pole_certificate.json", run_finite_pole_guard())
    dump("persistence_certificate.json", run_persistence_guard(stability))
    observed = {
        p.name
        for p in OUT.iterdir()
        if p.is_file() and p.name != "RESULTS_MANIFEST.json"
    }
    if observed != RESULT_PAYLOAD_NAMES:
        raise RuntimeError(
            f"unexpected result-file set: missing={sorted(RESULT_PAYLOAD_NAMES - observed)} extra={sorted(observed - RESULT_PAYLOAD_NAMES)}"
        )
    manifest = {name: sha256(OUT / name) for name in sorted(RESULT_PAYLOAD_NAMES)}
    dump(
        "RESULTS_MANIFEST.json",
        {"schema": "learning-from-prices-results-manifest-v1", "files": manifest},
    )
    print(
        json.dumps(
            {"status": "PASS", "counts": stability["counts"], "files": len(manifest)},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
