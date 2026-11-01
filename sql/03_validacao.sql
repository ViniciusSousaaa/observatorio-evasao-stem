SELECT 'dim_instituicao'      AS tabela, COUNT(*) AS registros FROM dim_instituicao
UNION ALL
SELECT 'dim_curso',            COUNT(*) FROM dim_curso
UNION ALL
SELECT 'dim_localidade',       COUNT(*) FROM dim_localidade
UNION ALL
SELECT 'fato_metricas_evasao', COUNT(*) FROM fato_metricas_evasao;

SELECT SUM(qt_ingressantes)  AS ingressantes,
       SUM(qt_matriculados)  AS matriculados,
       SUM(qt_concluintes)   AS concluintes,
       SUM(qt_desvinculados) AS desvinculados,
       SUM(qt_trancados)     AS trancados,
       SUM(qt_transferidos)  AS transferidos
FROM fato_metricas_evasao;

SELECT COUNT(*) AS fato_sem_municipio
FROM fato_metricas_evasao
WHERE id_municipio IS NULL;

SELECT SUM(qt_mat_fem)                        AS mat_fem,
       SUM(qt_mat_masc)                       AS mat_masc,
       SUM(qt_mat_branca)                     AS mat_branca,
       SUM(qt_mat_preta + qt_mat_parda)       AS mat_preta_parda,
       SUM(qt_mat_amarela + qt_mat_indigena)  AS mat_amarela_indigena,
       SUM(qt_mat_cornd)                      AS mat_cor_nao_declarada
FROM fato_metricas_evasao;
