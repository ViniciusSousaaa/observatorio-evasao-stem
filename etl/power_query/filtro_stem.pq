let
    Fonte = Csv.Document(
        File.Contents("C:\Caminho_Para_O_Seu_Arquivo\MICRODADOS_CADASTRO_CURSOS_2024.CSV"),
        [Delimiter = ";", Encoding = 1252, QuoteStyle = QuoteStyle.None]
    ),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),

    ColunasSelecionadas = Table.SelectColumns(Cabecalhos, {
        "NU_ANO_CENSO", "CO_IES", "TP_CATEGORIA_ADMINISTRATIVA", "TP_REDE",
        "SG_UF", "CO_MUNICIPIO", "NO_REGIAO", "CO_CURSO", "NO_CURSO",
        "NO_CINE_AREA_GERAL", "NO_CINE_AREA_ESPECIFICA", "TP_MODALIDADE_ENSINO",
        "QT_ING", "QT_MAT", "QT_CONC",
        "QT_SIT_DESVINCULADO", "QT_SIT_TRANCADA", "QT_SIT_TRANSFERIDO"
    }),

    FiltroSTEM = Table.SelectRows(ColunasSelecionadas, each List.Contains({
        "Computação e Tecnologias da Informação e Comunicação (TIC)",
        "Engenharia, produção e construção",
        "Ciências naturais, matemática e estatística"
    }, [NO_CINE_AREA_GERAL])),

    Metricas = {
        "QT_ING", "QT_MAT", "QT_CONC",
        "QT_SIT_DESVINCULADO", "QT_SIT_TRANCADA", "QT_SIT_TRANSFERIDO"
    },

    SemVazios = Table.ReplaceValue(FiltroSTEM, "", "0", Replacer.ReplaceValue, Metricas),
    Tipos = Table.TransformColumnTypes(SemVazios, List.Transform(Metricas, each {_, Int64.Type})),
    SemNulos = Table.ReplaceValue(Tipos, null, 0, Replacer.ReplaceValue, Metricas)
in
    SemNulos
