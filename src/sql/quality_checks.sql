-- Profilage qualité de la couche bronze : nombre de lignes concernées par chaque problème.
-- Usage (depuis la racine du dépôt) :
--   duckdb -c ".read src/sql/quality_checks.sql"

.read src/sql/bronze_sources.sql

WITH checks AS (
    SELECT 'anime' AS fichier, 'A0' AS code, 'lignes totales' AS controle,
           count(*) AS lignes
    FROM anime_raw
    UNION ALL
    SELECT 'anime', 'A1', 'anime_id en double',
           count(*) - count(DISTINCT anime_id)
    FROM anime_raw
    UNION ALL
    SELECT 'anime', 'A2', 'nom contenant des entités HTML (&#039; &quot; &amp;...)',
           count(*) FILTER (WHERE regexp_matches(name, '&(#[0-9]+|[a-zA-Z]+);'))
    FROM anime_raw
    UNION ALL
    SELECT 'anime', 'A3', 'genre manquant',
           count(*) FILTER (WHERE genre IS NULL)
    FROM anime_raw
    UNION ALL
    SELECT 'anime', 'A4', 'type manquant',
           count(*) FILTER (WHERE type IS NULL)
    FROM anime_raw
    UNION ALL
    SELECT 'anime', 'A5', 'episodes = Unknown',
           count(*) FILTER (WHERE episodes = 'Unknown')
    FROM anime_raw
    UNION ALL
    SELECT 'anime', 'A6', 'note moyenne (rating) manquante',
           count(*) FILTER (WHERE rating IS NULL)
    FROM anime_raw
    UNION ALL
    SELECT 'rating', 'R0', 'lignes totales',
           count(*)
    FROM rating_raw
    UNION ALL
    SELECT 'rating', 'R1', 'note = -1 (vu mais pas noté)',
           count(*) FILTER (WHERE rating = '-1')
    FROM rating_raw
    UNION ALL
    SELECT 'rating', 'R2', 'note invalide (ni -1 ni entre 1 et 10)',
           count(*) FILTER (WHERE rating <> '-1'
                            AND coalesce(try_cast(rating AS INTEGER) NOT BETWEEN 1 AND 10, true))
    FROM rating_raw
    UNION ALL
    SELECT 'rating', 'R3', 'couple (user_id, anime_id) en double',
           count(*) - (SELECT count(*) FROM (SELECT DISTINCT user_id, anime_id FROM rating_raw))
    FROM rating_raw
    UNION ALL
    SELECT 'rating', 'R4', 'anime_id absent de anime.csv (orphelin)',
           count(*)
    FROM rating_raw r
    WHERE NOT EXISTS (SELECT 1 FROM anime_raw a WHERE a.anime_id = r.anime_id)
)
SELECT fichier, code, controle, lignes
FROM checks
ORDER BY code;
