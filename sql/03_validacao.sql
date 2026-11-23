-- Contagem de registros por tabela do Star Schema
SELECT 'dim_instituicao'      AS tabela, COUNT(*) AS registros FROM dim_instituicao
UNION ALL
SELECT 'dim_curso',            COUNT(*) FROM dim_curso
UNION ALL
SELECT 'dim_localidade',       COUNT(*) FROM dim_localidade
UNION ALL
SELECT 'fato_metricas_evasao', COUNT(*) FROM fato_metricas_evasao;

-- Totais consolidados por ano do Censo
SELECT ano_censo,
       SUM(qt_ingressantes)  AS ingressantes,
       SUM(qt_matriculados)  AS matriculados,
       SUM(qt_concluintes)   AS concluintes,
       SUM(qt_desvinculados) AS desvinculados,
       SUM(qt_trancados)     AS trancados,
       SUM(qt_transferidos)  AS transferidos
FROM fato_metricas_evasao
GROUP BY ano_censo
ORDER BY ano_censo;

-- Veracidade: linhas de cursos EaD sem município e preenchimento do enriquecimento IBGE
SELECT COUNT(*) AS fato_sem_municipio
FROM fato_metricas_evasao
WHERE id_municipio IS NULL;

SELECT COUNT(*)                                        AS total_municipios,
       COUNT(nome_municipio)                           AS municipios_enriquecidos_ibge
FROM dim_localidade;

-- Resumo ODS 5 (Gênero) e ODS 18 (Raça/Cor) por Área STEM
SELECT area_geral,
       SUM(qt_matriculados)                                                                     AS matriculados,
       ROUND(100.0 * SUM(qt_desvinculados) / NULLIF(SUM(qt_matriculados), 0), 2)                AS evasao_pct,
       ROUND(100.0 * SUM(qt_mat_fem) / NULLIF(SUM(qt_mat_fem + qt_mat_masc), 0), 2)             AS pct_fem,
       ROUND(100.0 * SUM(qt_mat_ppi) / NULLIF(SUM(qt_mat_branca + qt_mat_ppi + qt_mat_amarela), 0), 2) AS pct_ppi_decl,
       ROUND(100.0 * SUM(qt_mat_cornd) / NULLIF(SUM(qt_matriculados), 0), 2)                    AS pct_cornd
FROM vw_base_analitica_stem
GROUP BY area_geral
ORDER BY evasao_pct DESC;
