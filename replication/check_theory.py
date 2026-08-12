#!/usr/bin/env python3
"""Independent symbolic and exact-rational checks for manuscript propositions."""

from __future__ import annotations

import json
import sympy as s


def zero_matrix(matrix: s.Matrix) -> bool:
    return all(s.factor(value) == 0 for value in matrix)


def main() -> None:
    a, b, c, A, h = s.symbols("a b c A h", positive=True)
    p0, ps, q, pz = s.symbols("p0 ps q pz")

    # Partially revealing source map and its explicit projector factorization.
    beta = a / (a + b)
    qden = ps**2 * (a + b) + c * pz**2
    gain = a * ps**2 / qden
    cden = h * (1 - gain) + (1 - h) * (1 - beta) * (1 - gain / ps)
    partial = s.Matrix(
        [
            (h * (1 - gain) * (1 - beta) + (1 - h) * (1 - beta) * (1 - gain / ps))
            / cden,
            h * (1 - gain) * beta / cden,
            -(1 - h) * (1 - beta) * gain * (q + pz) / (ps * cden),
            -A * a * (1 - beta) * (1 - gain) / cden,
        ]
    )
    E = h**2 + A**2 * b * c
    Hb = h + A**2 * b * c
    P = b * E + a * h * Hb
    partial_root = {
        p0: b * E / P,
        ps: a * h * Hb / P,
        q: A * a * b * h * (1 - h) / P,
        pz: -A * a * b * Hb / P,
    }
    jacobian = s.simplify(partial.jacobian([p0, ps, q, pz]).subs(partial_root))
    eps = h * (1 - h) / E
    L = (a + b) * h**2 + A**2 * b * c * (a * h + b)
    U = (a + b) * h**2 + A**2 * b * c * (a * h - b)
    V = A**2 * b * c * (a * h + b) - (a + b) * h**2
    projector = s.Matrix(
        [
            [0, -U / L, 0, 2 * A * b * c * h / L],
            [0, U / L, 0, -2 * A * b * c * h / L],
            [0, -A * b * V / (h * L), 1, -V / L],
            [0, -A * b * U / (h * L), 0, 2 * A**2 * b**2 * c / L],
        ]
    )
    assert zero_matrix(s.simplify(jacobian + eps * projector))
    assert zero_matrix(s.simplify(projector * projector - projector))
    assert s.factor(s.trace(projector) - 2) == 0

    # Private roots for both denominators and the scalar conjugacy.
    v, z = s.symbols("v z")
    t = A**2 * b * c
    K = a + t * (a + b)
    core = {
        p0: t * b / K,
        v: a * (1 + t) / K,
        z: -A * b * a * (1 + t) / K,
    }
    D = a * b * v**2 + c * (a + b) * z**2
    H = D - a * b * v
    private_common = s.Matrix(
        [
            (b * c * z**2 - a * b * v * p0) / H,
            a * c * z**2 / H,
            -A * a * b * c * z**2 / H,
        ]
    )
    common_star = s.Matrix([core[p0], core[v], core[z]])
    assert zero_matrix(s.simplify(private_common.subs(core) - common_star))
    q_h = A * a * b / K
    q_d = A * a * b * (1 + t) / (K * (2 + t))
    article_updater_q = -a * b * v * (q + z) / H
    deposited_residual_q = -a * b * v * (q + z) / D
    assert s.factor(article_updater_q.subs(core | {q: q_h}) - q_h) == 0
    assert s.factor(deposited_residual_q.subs(core | {q: q_d}) - q_d) == 0
    y = s.symbols("y", nonzero=True)
    v_from_y = a * y / K
    v_next = a * t * v / (K * v - a)
    y_next = s.factor((K / a * v_next).subs(v, v_from_y))
    w = 1 - (1 + t) / y
    w_next = s.factor(1 - (1 + t) / y_next)
    assert s.factor(w_next + w / t) == 0

    # Anchor projection and clearing arithmetic.
    aa, bb, cc, AA = map(s.Rational, (4, 8, 19, 2))
    aa /= 25
    bb /= 25
    cc /= 20
    anchor = [
        s.Rational(304, 581),
        s.Rational(277, 581),
        s.Rational(80, 581),
        -s.Rational(4432, 14525),
    ]
    ap0, av, aq, az = anchor
    anchor_D = aa * bb * av**2 + cc * (aa + bb) * az**2
    alpha = aa * cc * az**2 / anchor_D
    ell = aa * bb * av / anchor_D
    sigma = aa * bb * cc * az**2 / anchor_D
    normal = s.Matrix(
        [
            alpha * (aa + bb) + ell * aa * av - aa,
            alpha * aa * av + ell * (aa * av**2 + cc * az**2) - aa * av,
        ]
    )
    clearing = s.Matrix(
        [
            1 - alpha - ell * av - ap0,
            alpha + ell * av - av,
            -ell * az - aq,
            ell * az - az - AA * sigma,
        ]
    )
    assert zero_matrix(normal) and zero_matrix(clearing)
    deposited_residual = s.factor(-ell * az - s.Rational(11080, 116781))
    assert deposited_residual == s.Rational(5000, 116781)
    assert s.factor(deposited_residual / (AA * sigma)) == s.Rational(15625, 61104)

    print(
        json.dumps(
            {
                "status": "PASS",
                "checks": [
                    "private_roots",
                    "clearing",
                    "projector",
                    "scalar_conjugacy",
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
