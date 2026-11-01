import zipfile
import pandas as pd

AREAS_STEM = [
    'Computação e Tecnologias da Informação e Comunicação (TIC)',
    'Engenharia, produção e construção',
    'Ciências naturais, matemática e estatística',
]

COLUNAS_DESCRITIVAS = [
    'NU_ANO_CENSO', 'CO_IES', 'TP_CATEGORIA_ADMINISTRATIVA', 'TP_REDE',
    'SG_UF', 'CO_MUNICIPIO', 'NO_REGIAO', 'CO_CURSO', 'NO_CURSO',
    'NO_CINE_AREA_GERAL', 'NO_CINE_AREA_ESPECIFICA', 'TP_MODALIDADE_ENSINO',
]

METRICAS_FLUXO = ['QT_ING', 'QT_MAT', 'QT_CONC', 'QT_SIT_DESVINCULADO', 'QT_SIT_TRANCADA', 'QT_SIT_TRANSFERIDO']

PERFIS = ['FEM', 'MASC', 'BRANCA', 'PRETA', 'PARDA', 'AMARELA', 'INDIGENA', 'CORND']
METRICAS_PERFIL = [f'{etapa}_{perfil}' for etapa in ['QT_ING', 'QT_MAT', 'QT_CONC'] for perfil in PERFIS]

METRICAS = METRICAS_FLUXO + METRICAS_PERFIL

def localizar_csv_cursos(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return next(n for n in z.namelist() if n.upper().endswith('MICRODADOS_CADASTRO_CURSOS_2024.CSV'))

def tratar_base(zip_path, saida_path, tamanho_lote=50000):
    nome_csv = localizar_csv_cursos(zip_path)
    print(f"Lendo {nome_csv} em lotes de {tamanho_lote} linhas...")

    lotes = []
    total_lido = 0
    with zipfile.ZipFile(zip_path) as z, z.open(nome_csv) as arquivo:
        leitor = pd.read_csv(
            arquivo, sep=';', encoding='latin-1',
            usecols=COLUNAS_DESCRITIVAS + METRICAS, chunksize=tamanho_lote,
            dtype={'SG_UF': str, 'NO_REGIAO': str, 'NO_CURSO': str,
                   'NO_CINE_AREA_GERAL': str, 'NO_CINE_AREA_ESPECIFICA': str},
        )
        for lote in leitor:
            total_lido += len(lote)
            lotes.append(lote[lote['NO_CINE_AREA_GERAL'].isin(AREAS_STEM)])

    df = pd.concat(lotes, ignore_index=True)

    df[METRICAS] = df[METRICAS].fillna(0).astype(int)
    df['CO_MUNICIPIO'] = df['CO_MUNICIPIO'].astype('Int64')
    df = df.drop_duplicates()
    df = df[COLUNAS_DESCRITIVAS + METRICAS]

    df.to_csv(saida_path, sep=';', index=False, encoding='utf-8')

    print(f"Linhas lidas: {total_lido}")
    print(f"Linhas STEM:  {len(df)}")
    print(f"Base tratada salva em: {saida_path}")

if __name__ == '__main__':
    ARQUIVO_ZIP = 'data/raw/microdados_censo_da_educacao_superior_2024.zip'
    ARQUIVO_SAIDA = 'data/processed/base_tratada_stem.csv'

    tratar_base(ARQUIVO_ZIP, ARQUIVO_SAIDA)
