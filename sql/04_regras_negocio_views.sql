-- =============================================================================
-- 04_regras_negocio_views.sql
-- Regras de Negócio explícitas e Métricas Interseccionais (ODS 5 e ODS 18)
-- =============================================================================
BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Visão Base Analítica (tradução de códigos INEP + enriquecimento IBGE)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_base_analitica_stem AS
SELECT
    f.id_fato,
    f.ano_censo,
    f.id_ies,
    i.categoria_adm,
    CASE i.categoria_adm
        WHEN 1 THEN 'Pública Federal'
        WHEN 2 THEN 'Pública Estadual'
        WHEN 3 THEN 'Pública Municipal'
        WHEN 4 THEN 'Privada com fins lucrativos'
        WHEN 5 THEN 'Privada sem fins lucrativos'
        WHEN 6 THEN 'Privada - Particular em sentido estrito'
        WHEN 7 THEN 'Especial'
        WHEN 8 THEN 'Privada comunitária'
        WHEN 9 THEN 'Privada confessional'
        ELSE 'Não informado'
    END AS categoria_adm_desc,
    i.rede,
    CASE i.rede
        WHEN 1 THEN 'Pública'
        WHEN 2 THEN 'Privada'
        ELSE 'Não informado'
    END AS rede_desc,
    f.id_curso,
    c.nome_curso,
    c.area_geral,
    c.area_especifica,
    c.modalidade,
    CASE c.modalidade
        WHEN 1 THEN 'Presencial'
        WHEN 2 THEN 'EaD'
        ELSE 'Não informado'
    END AS modalidade_desc,
    f.id_municipio,
    COALESCE(l.nome_municipio, 'EaD sem polo / Não informado') AS nome_municipio,
    COALESCE(l.mesorregiao, 'Não informado')                   AS mesorregiao,
    COALESCE(l.sigla_uf, 'ND')                                 AS sigla_uf,
    COALESCE(l.regiao, 'Sem UF / EaD')                         AS regiao,
    f.qt_ingressantes,
    f.qt_matriculados,
    f.qt_concluintes,
    f.qt_desvinculados,
    f.qt_trancados,
    f.qt_transferidos,
    f.qt_ing_fem,
    f.qt_ing_masc,
    f.qt_ing_branca,
    f.qt_ing_preta,
    f.qt_ing_parda,
    f.qt_ing_amarela,
    f.qt_ing_indigena,
    f.qt_ing_cornd,
    (f.qt_ing_preta + f.qt_ing_parda + f.qt_ing_indigena)      AS qt_ing_ppi,
    f.qt_mat_fem,
    f.qt_mat_masc,
    f.qt_mat_branca,
    f.qt_mat_preta,
    f.qt_mat_parda,
    f.qt_mat_amarela,
    f.qt_mat_indigena,
    f.qt_mat_cornd,
    (f.qt_mat_preta + f.qt_mat_parda + f.qt_mat_indigena)      AS qt_mat_ppi,
    f.qt_conc_fem,
    f.qt_conc_masc,
    f.qt_conc_branca,
    f.qt_conc_preta,
    f.qt_conc_parda,
    f.qt_conc_amarela,
    f.qt_conc_indigena,
    f.qt_conc_cornd,
    (f.qt_conc_preta + f.qt_conc_parda + f.qt_conc_indigena)   AS qt_conc_ppi
FROM fato_metricas_evasao f
INNER JOIN dim_instituicao i ON i.id_ies = f.id_ies
INNER JOIN dim_curso       c ON c.id_curso = f.id_curso
LEFT  JOIN dim_localidade  l ON l.id_municipio = f.id_municipio;


-- -----------------------------------------------------------------------------
-- 2. Regras de Negócio: Evasão, Retenção, Trancamento e Eficiência Acadêmica
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpis_evasao_retencao AS
SELECT
    ano_censo,
    regiao,
    sigla_uf,
    area_geral,
    area_especifica,
    rede_desc,
    categoria_adm_desc,
    modalidade_desc,
    SUM(qt_ingressantes)                                                       AS total_ingressantes,
    SUM(qt_matriculados)                                                       AS total_matriculados,
    SUM(qt_concluintes)                                                        AS total_concluintes,
    SUM(qt_desvinculados)                                                      AS total_desvinculados,
    SUM(qt_trancados)                                                          AS total_trancados,
    SUM(qt_transferidos)                                                       AS total_transferidos,
    -- RN01: Taxa de Evasão sobre Matrículas (%) = Desvinculados / Matriculados
    ROUND(
        100.0 * SUM(qt_desvinculados) / NULLIF(SUM(qt_matriculados), 0),
        2
    )                                                                          AS taxa_evasao_matriculas_pct,
    -- RN02: Taxa de Evasão sobre Vínculos Totais (%) = Desvinculados / (Matriculados + Desvinculados + Concluintes)
    ROUND(
        100.0 * SUM(qt_desvinculados) / NULLIF(SUM(qt_matriculados + qt_desvinculados + qt_concluintes), 0),
        2
    )                                                                          AS taxa_evasao_vinculos_pct,
    -- RN03: Taxa de Retenção Estimada (%) = 100 - Taxa de Evasão sobre Vínculos Totais
    ROUND(
        100.0 - (100.0 * SUM(qt_desvinculados) / NULLIF(SUM(qt_matriculados + qt_desvinculados + qt_concluintes), 0)),
        2
    )                                                                          AS taxa_retencao_pct,
    -- RN04: Taxa de Trancamento / Risco de Evasão Futura (%) = Trancados / Matriculados
    ROUND(
        100.0 * SUM(qt_trancados) / NULLIF(SUM(qt_matriculados), 0),
        2
    )                                                                          AS taxa_trancamento_pct,
    -- RN05: Taxa de Transferência (%) = Transferidos / Matriculados
    ROUND(
        100.0 * SUM(qt_transferidos) / NULLIF(SUM(qt_matriculados), 0),
        2
    )                                                                          AS taxa_transferencia_pct,
    -- RN06: Taxa de Conclusão sobre Matrículas (%) = Concluintes / Matriculados
    ROUND(
        100.0 * SUM(qt_concluintes) / NULLIF(SUM(qt_matriculados), 0),
        2
    )                                                                          AS taxa_conclusao_pct,
    -- RN07: Razão Concluintes / Ingressantes (%) (Proxy de eficiência do funil)
    ROUND(
        100.0 * SUM(qt_concluintes) / NULLIF(SUM(qt_ingressantes), 0),
        2
    )                                                                          AS razao_conclusao_ingresso_pct
FROM vw_base_analitica_stem
GROUP BY
    ano_censo,
    regiao,
    sigla_uf,
    area_geral,
    area_especifica,
    rede_desc,
    categoria_adm_desc,
    modalidade_desc;


-- -----------------------------------------------------------------------------
-- 3. Regras de Negócio — ODS 5 (Igualdade de Gênero em STEM)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_ods5_genero_stem AS
SELECT
    ano_censo,
    regiao,
    sigla_uf,
    area_geral,
    rede_desc,
    modalidade_desc,
    SUM(qt_ing_fem)                                                            AS ing_fem,
    SUM(qt_ing_masc)                                                           AS ing_masc,
    SUM(qt_mat_fem)                                                            AS mat_fem,
    SUM(qt_mat_masc)                                                           AS mat_masc,
    SUM(qt_conc_fem)                                                           AS conc_fem,
    SUM(qt_conc_masc)                                                          AS conc_masc,
    -- RN08: Participação Feminina no Ingresso (%)
    ROUND(100.0 * SUM(qt_ing_fem)  / NULLIF(SUM(qt_ing_fem + qt_ing_masc), 0), 2)   AS pct_ing_fem,
    -- RN09: Participação Feminina nas Matrículas (%)
    ROUND(100.0 * SUM(qt_mat_fem)  / NULLIF(SUM(qt_mat_fem + qt_mat_masc), 0), 2)   AS pct_mat_fem,
    -- RN10: Participação Feminina na Conclusão (%)
    ROUND(100.0 * SUM(qt_conc_fem) / NULLIF(SUM(qt_conc_fem + qt_conc_masc), 0), 2) AS pct_conc_fem,
    -- RN11: Índice de Paridade de Gênero nas Matrículas (IPG = Fem / Masc; 1,00 = paridade exata)
    ROUND(1.0 * SUM(qt_mat_fem) / NULLIF(SUM(qt_mat_masc), 0), 3)                   AS ipg_matriculas,
    -- RN12: Gap de Paridade Feminina (pontos percentuais em relação a 50%)
    ROUND(
        (100.0 * SUM(qt_mat_fem) / NULLIF(SUM(qt_mat_fem + qt_mat_masc), 0)) - 50.0,
        2
    )                                                                               AS gap_paridade_fem_pp,
    -- RN13: Delta no Funil Feminino (pp) = % Conclusão Fem - % Ingresso Fem
    ROUND(
        (100.0 * SUM(qt_conc_fem) / NULLIF(SUM(qt_conc_fem + qt_conc_masc), 0))
        - (100.0 * SUM(qt_ing_fem) / NULLIF(SUM(qt_ing_fem + qt_ing_masc), 0)),
        2
    )                                                                               AS delta_funil_fem_pp,
    -- RN14: Razão Conclusão / Ingresso por Gênero (%)
    ROUND(100.0 * SUM(qt_conc_fem)  / NULLIF(SUM(qt_ing_fem), 0), 2)                AS razao_conc_ing_fem_pct,
    ROUND(100.0 * SUM(qt_conc_masc) / NULLIF(SUM(qt_ing_masc), 0), 2)               AS razao_conc_ing_masc_pct
FROM vw_base_analitica_stem
GROUP BY
    ano_censo,
    regiao,
    sigla_uf,
    area_geral,
    rede_desc,
    modalidade_desc;


-- -----------------------------------------------------------------------------
-- 4. Regras de Negócio — ODS 18 (Igualdade Étnico-Racial em STEM)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_ods18_raca_stem AS
SELECT
    ano_censo,
    regiao,
    sigla_uf,
    area_geral,
    rede_desc,
    modalidade_desc,
    SUM(qt_ing_ppi)                                                            AS ing_ppi,
    SUM(qt_ing_branca)                                                         AS ing_branca,
    SUM(qt_mat_ppi)                                                            AS mat_ppi,
    SUM(qt_mat_branca)                                                         AS mat_branca,
    SUM(qt_mat_preta)                                                          AS mat_preta,
    SUM(qt_mat_parda)                                                          AS mat_parda,
    SUM(qt_mat_amarela)                                                        AS mat_amarela,
    SUM(qt_mat_indigena)                                                       AS mat_indigena,
    SUM(qt_mat_cornd)                                                          AS mat_cornd,
    SUM(qt_conc_ppi)                                                           AS conc_ppi,
    SUM(qt_conc_branca)                                                        AS conc_branca,
    -- RN15: Participação PPI no Ingresso (% sobre total com raça declarada)
    ROUND(
        100.0 * SUM(qt_ing_ppi)
        / NULLIF(SUM(qt_ing_branca + qt_ing_ppi + qt_ing_amarela), 0),
        2
    )                                                                          AS pct_ing_ppi_declarado,
    -- RN16: Participação PPI nas Matrículas (% sobre total com raça declarada)
    ROUND(
        100.0 * SUM(qt_mat_ppi)
        / NULLIF(SUM(qt_mat_branca + qt_mat_ppi + qt_mat_amarela), 0),
        2
    )                                                                          AS pct_mat_ppi_declarado,
    -- RN17: Participação PPI na Conclusão (% sobre total com raça declarada)
    ROUND(
        100.0 * SUM(qt_conc_ppi)
        / NULLIF(SUM(qt_conc_branca + qt_conc_ppi + qt_conc_amarela), 0),
        2
    )                                                                          AS pct_conc_ppi_declarado,
    -- RN18: Delta no Funil PPI (pp) = % Conclusão PPI - % Ingresso PPI
    ROUND(
        (100.0 * SUM(qt_conc_ppi) / NULLIF(SUM(qt_conc_branca + qt_conc_ppi + qt_conc_amarela), 0))
        - (100.0 * SUM(qt_ing_ppi) / NULLIF(SUM(qt_ing_branca + qt_ing_ppi + qt_ing_amarela), 0)),
        2
    )                                                                          AS delta_funil_ppi_pp,
    -- RN19: Razão Conclusão / Ingresso PPI vs. Branca (%) e Gap Étnico-Racial (pp)
    ROUND(100.0 * SUM(qt_conc_ppi)    / NULLIF(SUM(qt_ing_ppi), 0), 2)         AS razao_conc_ing_ppi_pct,
    ROUND(100.0 * SUM(qt_conc_branca) / NULLIF(SUM(qt_ing_branca), 0), 2)      AS razao_conc_ing_branca_pct,
    ROUND(
        (100.0 * SUM(qt_conc_branca) / NULLIF(SUM(qt_ing_branca), 0))
        - (100.0 * SUM(qt_conc_ppi)  / NULLIF(SUM(qt_ing_ppi), 0)),
        2
    )                                                                          AS gap_conclusao_racial_pp,
    -- RN20: Indicador de Veracidade — Subnotificação Racial (% Cor/Raça Não Declarada nas Matrículas)
    ROUND(
        100.0 * SUM(qt_mat_cornd) / NULLIF(SUM(qt_matriculados), 0),
        2
    )                                                                          AS taxa_subnotificacao_racial_pct
FROM vw_base_analitica_stem
GROUP BY
    ano_censo,
    regiao,
    sigla_uf,
    area_geral,
    rede_desc,
    modalidade_desc;


-- -----------------------------------------------------------------------------
-- 5. Visão Consolidada Interseccional (Evasão + ODS 5 + ODS 18 por Curso/UF)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_interseccional_ods5_ods18_curso AS
SELECT
    ano_censo,
    regiao,
    sigla_uf,
    nome_municipio,
    area_geral,
    area_especifica,
    nome_curso,
    rede_desc,
    modalidade_desc,
    SUM(qt_ingressantes)                                                       AS total_ingressantes,
    SUM(qt_matriculados)                                                       AS total_matriculados,
    SUM(qt_concluintes)                                                        AS total_concluintes,
    SUM(qt_desvinculados)                                                      AS total_desvinculados,
    ROUND(100.0 * SUM(qt_desvinculados) / NULLIF(SUM(qt_matriculados), 0), 2)  AS taxa_evasao_pct,
    ROUND(100.0 * SUM(qt_mat_fem) / NULLIF(SUM(qt_mat_fem + qt_mat_masc), 0), 2) AS pct_mat_fem,
    ROUND(
        100.0 * SUM(qt_mat_ppi) / NULLIF(SUM(qt_mat_branca + qt_mat_ppi + qt_mat_amarela), 0),
        2
    )                                                                          AS pct_mat_ppi_declarado,
    ROUND(100.0 * SUM(qt_mat_cornd) / NULLIF(SUM(qt_matriculados), 0), 2)      AS pct_cornd
FROM vw_base_analitica_stem
GROUP BY
    ano_censo,
    regiao,
    sigla_uf,
    nome_municipio,
    area_geral,
    area_especifica,
    nome_curso,
    rede_desc,
    modalidade_desc;

COMMIT;
