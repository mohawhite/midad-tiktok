"""Publication de la vidéo du jour.

Voie principale : Buffer (service audité par TikTok), dès qu'une clé est fournie.
Plan B : la vidéo, la couverture et la légende sont remises pour une publication à la main.
"""
from __future__ import annotations

import os
from datetime import date

MANUEL = "manuelle en attente"


def publier(res, cfg: dict, jour: date) -> tuple[str, str]:
    """Renvoie (mode, identifiant). Ne lève jamais d'erreur : en cas d'échec, plan B."""
    if not os.environ.get("BUFFER_API_KEY"):
        print("Aucune clé Buffer : la vidéo est remise pour publication manuelle (plan B).")
        return MANUEL, ""
    # La publication par Buffer sera branchée et testée quand le compte existera.
    print("Publication par Buffer pas encore branchée : plan B.")
    return MANUEL, ""
