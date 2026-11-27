-- Accès S3 (Onyxia Adaltas) et vues sur les fichiers bruts de la couche bronze.
-- Prérequis : profil AWS « default » à jour (script « AWS CLI / shared profile » d'Onyxia)
--             et variable d'environnement S3_BUCKET (ex. user-f-kerdouci-ece).
-- Les colonnes sont lues en texte brut (all_varchar) pour voir les valeurs telles qu'elles sont.

CREATE OR REPLACE SECRET s3_project (
    TYPE s3,
    PROVIDER credential_chain,
    CHAIN 'config',
    PROFILE 'default',
    ENDPOINT 's3.seaweedfs.adm.adaltas.cloud',
    URL_STYLE 'path',
    REGION 'us-east-1'
);

SET VARIABLE bronze = 's3://' || getenv('S3_BUCKET') || '/bigdata_project/bronze';

CREATE OR REPLACE VIEW anime_raw AS
SELECT * FROM read_csv(getvariable('bronze') || '/anime.csv', all_varchar = true);

CREATE OR REPLACE VIEW rating_raw AS
SELECT * FROM read_csv(getvariable('bronze') || '/rating_sample.csv', all_varchar = true);
