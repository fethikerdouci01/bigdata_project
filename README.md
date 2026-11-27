# Projet Big Data — Pipeline de données sur les animés

Pipeline de bout en bout sur Onyxia : stockage S3, transformation DuckDB/dbt, exécution Kubernetes.

## Auteurs

- KERDOUCI Fethi
- OUCHRI Ines

## Prérequis

- Un compte [Onyxia](https://datalab.sspcloud.fr) avec un service **VSCode-python** lancé (accès S3 et Kubernetes inclus).
- Un bucket S3 personnel sur Onyxia (stockage objet MinIO).
- [uv](https://docs.astral.sh/uv/) pour l'environnement Python (Python ≥ 3.11).
- AWS CLI (`aws s3`) configurée avec les identifiants S3 fournis par Onyxia.
- DuckDB et dbt-duckdb (installés via `uv sync`).
- `kubectl` (préinstallé dans le service VSCode d'Onyxia).

## Dataset

- **Nom** : Anime Recommendations Database (données MyAnimeList, auteur Kaggle : CooperUnion)
- **URL** : https://www.kaggle.com/datasets/CooperUnion/anime-recommendations-database
- **Téléchargé depuis** : miroir Hugging Face [`jason1966/CooperUnion_anime-recommendations-database`](https://huggingface.co/datasets/jason1966/CooperUnion_anime-recommendations-database), révision figée `646e3aa`
- **Licence** : CC0 : Public Domain
- **Date de téléchargement** : 26/11/2026
- **Taille des données brutes** : 3 168 839 octets (3,17 Mo), stockées sur S3 avec un `manifest.json` (877 octets)
  - `anime.csv` : 936 463 octets, 12 294 animés (`anime_id`, `name`, `genre`, `type`, `episodes`, `rating`, `members`)
  - `rating_sample.csv` : 2 232 376 octets, 156 595 notes de 1 470 utilisateurs (`user_id`, `anime_id`, `rating`), extrait de `rating.csv` (111 Mo) : utilisateurs dont `user_id % 50 == 0`, lignes recopiées sans modification
  - `manifest.json` : source, révision, date, empreintes SHA-256 et règle d'échantillonnage

## Problématique

_à compléter_

## Chemins S3

_à compléter_

## Reproduction

_à compléter_
