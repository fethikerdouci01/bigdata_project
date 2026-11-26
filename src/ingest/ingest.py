"""Ingestion des données brutes (couche bronze).

1. Télécharge anime.csv et rating.csv depuis le miroir Hugging Face du dataset Kaggle
   « Anime Recommendations Database » (CooperUnion), à une révision figée.
2. Vérifie l'intégrité des téléchargements (empreintes connues).
3. Extrait un échantillon reproductible de rating.csv : toutes les notes des utilisateurs
   dont user_id est un multiple de --modulo. Les lignes sont recopiées telles quelles.
4. Écrit un manifest.json (source, révision, empreintes, tailles, règle d'échantillonnage).
5. Envoie anime.csv, rating_sample.csv et manifest.json sur S3 (Onyxia).

Usage (dans un service VSCode Onyxia) :
    uv run python src/ingest/ingest.py --bucket "$S3_BUCKET"
    uv run python src/ingest/ingest.py --skip-upload        # local, sans S3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HF_REPO = "jason1966/CooperUnion_anime-recommendations-database"
HF_REVISION = "646e3aa9a6623593057297ca47af1442fc27e13c"
KAGGLE_SOURCE = "https://www.kaggle.com/datasets/CooperUnion/anime-recommendations-database"
BASE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}"

# Empreintes publiées par Hugging Face pour cette révision.
EXPECTED = {
    "anime.csv": {"git_blob_sha1": "8c0e6ab7876beeb40ac52faef5d350db5a6e61a3", "size": 936463},
    "rating.csv": {
        "sha256": "f2cf790539cff9c7ac462d546381493a5748fc22bedaaf3fbf32d2e10294ab62",
        "size": 111404899,
    },
}

DEFAULT_MODULO = 50
DEFAULT_PREFIX = "bigdata_project/bronze"


def log(msg: str) -> None:
    print(f"[ingest] {msg}", flush=True)


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid(name: str, path: Path) -> bool:
    exp = EXPECTED[name]
    if not path.exists() or path.stat().st_size != exp["size"]:
        return False
    if "sha256" in exp:
        return sha256(path) == exp["sha256"]
    return git_blob_sha1(path) == exp["git_blob_sha1"]


def download(name: str, cache_dir: Path) -> Path:
    path = cache_dir / name
    if is_valid(name, path):
        log(f"{name} déjà présent et intègre, téléchargement ignoré")
        return path
    url = f"{BASE_URL}/{name}"
    log(f"téléchargement de {url}")
    tmp = path.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": "bigdata-project-ingest"})
    with urllib.request.urlopen(req) as resp, tmp.open("wb") as out:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            out.write(chunk)
    tmp.replace(path)
    if not is_valid(name, path):
        sys.exit(f"[ingest] ERREUR : empreinte inattendue pour {name}")
    log(f"{name} : {path.stat().st_size} octets, intégrité vérifiée")
    return path


def extract_ratings(src: Path, dest: Path, modulo: int) -> dict:
    """Recopie l'en-tête et les lignes dont user_id % modulo == 0, sans les modifier."""
    rows_in = rows_out = 0
    users = set()
    with src.open("rb") as fin, dest.open("wb") as fout:
        header = fin.readline()
        if not header.startswith(b"user_id,"):
            sys.exit(f"[ingest] ERREUR : en-tête inattendu {header!r}")
        fout.write(header)
        for line in fin:
            rows_in += 1
            user_id = int(line.split(b",", 1)[0])
            if user_id % modulo == 0:
                fout.write(line)
                rows_out += 1
                users.add(user_id)
    log(f"extrait : {rows_out} notes sur {rows_in}, {len(users)} utilisateurs")
    return {"rows_source": rows_in, "rows_sample": rows_out, "users_sample": len(users)}


def upload(files: list[Path], bucket: str, prefix: str) -> None:
    import boto3  # importé ici pour permettre --skip-upload sans boto3

    endpoint = os.environ.get("AWS_S3_ENDPOINT", "")
    if endpoint and not endpoint.startswith("http"):
        endpoint = f"https://{endpoint}"
    s3 = boto3.client("s3", endpoint_url=endpoint or None)
    for f in files:
        key = f"{prefix.strip('/')}/{f.name}"
        s3.upload_file(str(f), bucket, key)
        log(f"envoyé : s3://{bucket}/{key}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bucket", default=os.environ.get("S3_BUCKET"), help="bucket S3 (défaut : $S3_BUCKET)")
    p.add_argument("--prefix", default=DEFAULT_PREFIX, help=f"préfixe S3 (défaut : {DEFAULT_PREFIX})")
    p.add_argument("--modulo", type=int, default=DEFAULT_MODULO, help="garde les user_id multiples de N")
    p.add_argument("--cache-dir", type=Path, default=Path("data/cache"), help="téléchargements sources")
    p.add_argument("--out-dir", type=Path, default=Path("data/bronze"), help="fichiers bronze locaux")
    p.add_argument("--skip-upload", action="store_true", help="ne pas envoyer sur S3")
    a = p.parse_args()

    if not a.skip_upload and not a.bucket:
        sys.exit("[ingest] ERREUR : indiquer --bucket ou définir S3_BUCKET (ou utiliser --skip-upload)")

    a.cache_dir.mkdir(parents=True, exist_ok=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)

    anime_src = download("anime.csv", a.cache_dir)
    rating_src = download("rating.csv", a.cache_dir)

    anime_out = a.out_dir / "anime.csv"
    anime_out.write_bytes(anime_src.read_bytes())
    sample_out = a.out_dir / "rating_sample.csv"
    stats = extract_ratings(rating_src, sample_out, a.modulo)

    total = anime_out.stat().st_size + sample_out.stat().st_size
    manifest = {
        "dataset": "Anime Recommendations Database (MyAnimeList)",
        "source_kaggle": KAGGLE_SOURCE,
        "source_download": f"https://huggingface.co/datasets/{HF_REPO}",
        "hf_revision": HF_REVISION,
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sampling_rule": f"rating.csv lines where user_id % {a.modulo} == 0 (lines copied unchanged)",
        "files": {
            "anime.csv": {"bytes": anime_out.stat().st_size, "sha256": sha256(anime_out)},
            "rating_sample.csv": {"bytes": sample_out.stat().st_size, "sha256": sha256(sample_out), **stats},
        },
        "raw_total_bytes": total,
    }
    manifest_out = a.out_dir / "manifest.json"
    manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"taille brute totale : {total} octets ({total / 1e6:.2f} Mo)")
    if not 1_000_000 <= total <= 5_000_000:
        log("ATTENTION : la taille brute sort de l'intervalle 1-5 Mo exigé, ajuster --modulo")

    if a.skip_upload:
        log("envoi S3 ignoré (--skip-upload)")
    else:
        upload([anime_out, sample_out, manifest_out], a.bucket, a.prefix)
    log("terminé")


if __name__ == "__main__":
    main()
