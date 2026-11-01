BEGIN;

CREATE TABLE IF NOT EXISTS dim_instituicao (
    id_ies          INTEGER      PRIMARY KEY,
    categoria_adm   SMALLINT     NOT NULL,
    rede            SMALLINT     NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_curso (
    id_curso        INTEGER      PRIMARY KEY,
    nome_curso      VARCHAR(255) NOT NULL,
    area_geral      VARCHAR(120) NOT NULL,
    area_especifica VARCHAR(120) NOT NULL,
    modalidade      SMALLINT     NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_localidade (
    id_municipio    INTEGER      PRIMARY KEY,
    sigla_uf        CHAR(2)      NOT NULL,
    regiao          VARCHAR(20)  NOT NULL
);

CREATE TABLE IF NOT EXISTS fato_metricas_evasao (
    id_fato          BIGSERIAL   PRIMARY KEY,
    id_ies           INTEGER     NOT NULL REFERENCES dim_instituicao (id_ies),
    id_curso         INTEGER     NOT NULL REFERENCES dim_curso (id_curso),
    id_municipio     INTEGER     REFERENCES dim_localidade (id_municipio),
    ano_censo        SMALLINT    NOT NULL,
    qt_ingressantes  INTEGER     NOT NULL DEFAULT 0,
    qt_matriculados  INTEGER     NOT NULL DEFAULT 0,
    qt_concluintes   INTEGER     NOT NULL DEFAULT 0,
    qt_desvinculados INTEGER     NOT NULL DEFAULT 0,
    qt_trancados     INTEGER     NOT NULL DEFAULT 0,
    qt_transferidos  INTEGER     NOT NULL DEFAULT 0,
    qt_ing_fem       INTEGER     NOT NULL DEFAULT 0,
    qt_ing_masc      INTEGER     NOT NULL DEFAULT 0,
    qt_ing_branca    INTEGER     NOT NULL DEFAULT 0,
    qt_ing_preta     INTEGER     NOT NULL DEFAULT 0,
    qt_ing_parda     INTEGER     NOT NULL DEFAULT 0,
    qt_ing_amarela   INTEGER     NOT NULL DEFAULT 0,
    qt_ing_indigena  INTEGER     NOT NULL DEFAULT 0,
    qt_ing_cornd     INTEGER     NOT NULL DEFAULT 0,
    qt_mat_fem       INTEGER     NOT NULL DEFAULT 0,
    qt_mat_masc      INTEGER     NOT NULL DEFAULT 0,
    qt_mat_branca    INTEGER     NOT NULL DEFAULT 0,
    qt_mat_preta     INTEGER     NOT NULL DEFAULT 0,
    qt_mat_parda     INTEGER     NOT NULL DEFAULT 0,
    qt_mat_amarela   INTEGER     NOT NULL DEFAULT 0,
    qt_mat_indigena  INTEGER     NOT NULL DEFAULT 0,
    qt_mat_cornd     INTEGER     NOT NULL DEFAULT 0,
    qt_conc_fem      INTEGER     NOT NULL DEFAULT 0,
    qt_conc_masc     INTEGER     NOT NULL DEFAULT 0,
    qt_conc_branca   INTEGER     NOT NULL DEFAULT 0,
    qt_conc_preta    INTEGER     NOT NULL DEFAULT 0,
    qt_conc_parda    INTEGER     NOT NULL DEFAULT 0,
    qt_conc_amarela  INTEGER     NOT NULL DEFAULT 0,
    qt_conc_indigena INTEGER     NOT NULL DEFAULT 0,
    qt_conc_cornd    INTEGER     NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_fato_ies       ON fato_metricas_evasao (id_ies);
CREATE INDEX IF NOT EXISTS ix_fato_curso     ON fato_metricas_evasao (id_curso);
CREATE INDEX IF NOT EXISTS ix_fato_municipio ON fato_metricas_evasao (id_municipio);
CREATE INDEX IF NOT EXISTS ix_fato_ano       ON fato_metricas_evasao (ano_censo);

COMMIT;
