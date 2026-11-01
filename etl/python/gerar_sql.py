import pandas as pd

TAMANHO_LOTE = 1000

PERFIS = ['fem', 'masc', 'branca', 'preta', 'parda', 'amarela', 'indigena', 'cornd']

COLUNAS_FATO = {
    'CO_IES': 'id_ies',
    'CO_CURSO': 'id_curso',
    'CO_MUNICIPIO': 'id_municipio',
    'NU_ANO_CENSO': 'ano_censo',
    'QT_ING': 'qt_ingressantes',
    'QT_MAT': 'qt_matriculados',
    'QT_CONC': 'qt_concluintes',
    'QT_SIT_DESVINCULADO': 'qt_desvinculados',
    'QT_SIT_TRANCADA': 'qt_trancados',
    'QT_SIT_TRANSFERIDO': 'qt_transferidos',
}
for etapa in ['ing', 'mat', 'conc']:
    for perfil in PERFIS:
        COLUNAS_FATO[f'QT_{etapa.upper()}_{perfil.upper()}'] = f'qt_{etapa}_{perfil}'

def valor_sql(valor):
    if pd.isna(valor):
        return "NULL"
    if isinstance(valor, str):
        return "'" + valor.replace("'", "''") + "'"
    return str(int(valor))

def escrever_inserts(f, tabela, colunas_banco, linhas, conflito=None):
    sufixo = f" ON CONFLICT ({conflito}) DO NOTHING" if conflito else ""
    for inicio in range(0, len(linhas), TAMANHO_LOTE):
        lote = linhas[inicio:inicio + TAMANHO_LOTE]
        valores = ",\n".join("(" + ", ".join(valor_sql(v) for v in linha) + ")" for linha in lote)
        f.write(f"INSERT INTO {tabela} ({', '.join(colunas_banco)}) VALUES\n{valores}{sufixo};\n\n")

def csv_para_sql(csv_path, sql_output_path):
    print(f"Lendo o arquivo: {csv_path}...")

    df = pd.read_csv(csv_path, sep=';', dtype={'CO_MUNICIPIO': 'Int64'})

    dim_ies = df[['CO_IES', 'TP_CATEGORIA_ADMINISTRATIVA', 'TP_REDE']].drop_duplicates('CO_IES')
    dim_curso = df[['CO_CURSO', 'NO_CURSO', 'NO_CINE_AREA_GERAL', 'NO_CINE_AREA_ESPECIFICA', 'TP_MODALIDADE_ENSINO']].drop_duplicates('CO_CURSO')
    dim_loc = df[['CO_MUNICIPIO', 'SG_UF', 'NO_REGIAO']].dropna(subset=['CO_MUNICIPIO']).drop_duplicates('CO_MUNICIPIO')
    fato = df[list(COLUNAS_FATO)]

    with open(sql_output_path, 'w', encoding='utf-8') as f:
        print("Gerando INSERTS para Dimensões e Fato...")

        f.write("TRUNCATE fato_metricas_evasao, dim_instituicao, dim_curso, dim_localidade RESTART IDENTITY;\n\n")

        escrever_inserts(f, 'dim_instituicao', ['id_ies', 'categoria_adm', 'rede'],
                         dim_ies.values.tolist(), 'id_ies')
        escrever_inserts(f, 'dim_curso', ['id_curso', 'nome_curso', 'area_geral', 'area_especifica', 'modalidade'],
                         dim_curso.values.tolist(), 'id_curso')
        escrever_inserts(f, 'dim_localidade', ['id_municipio', 'sigla_uf', 'regiao'],
                         dim_loc.values.tolist(), 'id_municipio')
        escrever_inserts(f, 'fato_metricas_evasao', list(COLUNAS_FATO.values()),
                         fato.values.tolist())

    print(f"\nSucesso! Script SQL gerado em: {sql_output_path}")
    print(f"  dim_instituicao:      {len(dim_ies):>7}")
    print(f"  dim_curso:            {len(dim_curso):>7}")
    print(f"  dim_localidade:       {len(dim_loc):>7}")
    print(f"  fato_metricas_evasao: {len(fato):>7}")

if __name__ == '__main__':
    ARQUIVO_CSV_ENTRADA = 'data/processed/base_tratada_stem.csv'
    ARQUIVO_SQL_SAIDA = 'sql/02_carga_dados.sql'

    csv_para_sql(ARQUIVO_CSV_ENTRADA, ARQUIVO_SQL_SAIDA)
