"""Publication de la vidéo du jour.

Voie principale : Buffer, un service de planification audité par TikTok. Buffer ne reçoit
pas de fichier : il va chercher la vidéo à une adresse publique, ici une « release » GitHub.
Plan B : la vidéo, la couverture et la légende sont remises pour une publication à la main.
"""
from __future__ import annotations

import os
import subprocess
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API = "https://api.buffer.com"
MANUEL = "manuelle en attente"
BUFFER = "buffer"


class PublicationError(RuntimeError):
    pass


def _graphql(query: str, variables: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}", "Content-Type": "application/json"}
    delay, last = 2, ""
    for attempt in range(5):
        try:
            r = requests.post(API, json={"query": query, "variables": variables or {}}, headers=headers, timeout=60)
            if r.status_code == 200 and "errors" not in r.json():
                return r.json()["data"]
            last = f"HTTP {r.status_code} : {r.text[:300]}"
            if r.status_code in (400, 401, 403):
                break
        except requests.RequestException as exc:
            last = str(exc)
        if attempt < 4:
            time.sleep(delay)
            delay *= 2
    raise PublicationError(f"Buffer ne répond pas correctement ({last})")


def canal_tiktok() -> str:
    if os.environ.get("BUFFER_CHANNEL_ID"):
        return os.environ["BUFFER_CHANNEL_ID"]
    orgs = _graphql("query { account { organizations { id } } }")["account"]["organizations"]
    for org in orgs:
        data = _graphql("query($o: OrganizationId!) { channels(input: {organizationId: $o}) { id service } }",
                        {"o": org["id"]})
        for ch in data["channels"]:
            if ch["service"] == "tiktok":
                return ch["id"]
    raise PublicationError("Aucun compte TikTok connecté dans Buffer")


def heberger(video: Path, jour: date, cfg: dict) -> str:
    """Dépose la vidéo dans une release publique et renvoie son adresse."""
    depot = cfg["publication"].get("depot_videos") or os.environ.get("GITHUB_REPOSITORY", "")
    if not depot:
        raise PublicationError("Aucun dépôt public indiqué pour héberger la vidéo")
    nom = f"{jour.isoformat()}.mp4"
    copie = video.with_name(nom)
    copie.write_bytes(video.read_bytes())
    env = dict(os.environ)
    if os.environ.get("VIDEOS_TOKEN"):
        env["GH_TOKEN"] = os.environ["VIDEOS_TOKEN"]
    existe = subprocess.run(["gh", "release", "view", "videos", "-R", depot], env=env, capture_output=True)
    if existe.returncode != 0:
        subprocess.run(["gh", "release", "create", "videos", "-R", depot, "--title", "Vidéos",
                        "--notes", "Vidéos du jour, récupérées par Buffer."], env=env, check=True)
    subprocess.run(["gh", "release", "upload", "videos", str(copie), "-R", depot, "--clobber"], env=env, check=True)
    url = f"https://github.com/{depot}/releases/download/videos/{nom}"
    r = requests.head(url, allow_redirects=True, timeout=60)
    if r.status_code != 200:
        raise PublicationError(f"La vidéo hébergée n'est pas accessible publiquement (HTTP {r.status_code})")
    return url


def _echeance(jour: date, cfg: dict) -> datetime:
    h, m = (int(x) for x in cfg["publication"]["heure"].split(":"))
    prevu = datetime(jour.year, jour.month, jour.day, h, m, tzinfo=ZoneInfo("Europe/Paris"))
    return max(prevu, datetime.now(timezone.utc) + timedelta(minutes=5)).astimezone(timezone.utc)


def publier_buffer(res, cfg: dict, jour: date) -> str:
    url = heberger(res.video, jour, cfg)
    data = _graphql(
        """mutation($input: CreatePostInput!) {
             createPost(input: $input) {
               ... on PostActionSuccess { post { id dueAt } }
               ... on MutationError { message }
             }
           }""",
        {"input": {
            "text": res.legende,
            "channelId": canal_tiktok(),
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": _echeance(jour, cfg).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": 0}}}],
        }},
    )["createPost"]
    if "post" not in data:
        raise PublicationError(f"Buffer a refusé la publication : {data.get('message')}")
    return data["post"]["id"]


def publier(res, cfg: dict, jour: date) -> tuple[str, str]:
    """Renvoie (mode, identifiant). En cas d'échec de Buffer, bascule sur le plan B."""
    if not os.environ.get("BUFFER_API_KEY"):
        print("Aucune clé Buffer : la vidéo est remise pour publication manuelle (plan B).")
        return MANUEL, ""
    try:
        identifiant = publier_buffer(res, cfg, jour)
        print(f"Vidéo confiée à Buffer (publication {identifiant}).")
        return BUFFER, identifiant
    except (PublicationError, subprocess.CalledProcessError, KeyError) as exc:
        print(f"Publication automatique impossible, plan B : {exc}")
        return MANUEL, ""
