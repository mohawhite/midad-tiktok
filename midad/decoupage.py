"""Découpage d'une sourate longue en parties, toujours sur une frontière de verset."""
from __future__ import annotations

import math

# Nombre de versets de chaque sourate : table de référence pour les contrôles.
VERSETS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85,
    54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
    14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
    11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
]


def decouper(durees: list[float], mini: float = 60, maxi: float = 180) -> list[list[int]]:
    """Renvoie des plages [premier verset, dernier verset], numérotées à partir de 1.

    `durees[i]` est la durée du verset i+1 (basmala comprise pour le verset 1).
    Une partie ne dépasse `maxi` que si un verset seul est plus long.
    """
    total = sum(durees)
    n = len(durees)
    if total <= maxi:
        return [[1, n]]
    cible = total / math.ceil(total / (maxi * 0.8))
    parts: list[list[int]] = []
    start, acc = 0, 0.0
    for i, d in enumerate(durees):
        if i > start and (acc + d > maxi or (acc >= mini and acc + d / 2 > cible)):
            parts.append([start + 1, i])
            start, acc = i, 0.0
        acc += d
    parts.append([start + 1, n])
    # Une dernière partie trop courte rejoint la précédente si la limite le permet.
    if len(parts) > 1:
        a, b = parts[-2], parts[-1]
        last = sum(durees[b[0] - 1:b[1]])
        if last < mini and sum(durees[a[0] - 1:a[1]]) + last <= maxi:
            parts[-2:] = [[a[0], b[1]]]
    return parts
