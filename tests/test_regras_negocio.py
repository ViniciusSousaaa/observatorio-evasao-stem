"""Testes unitários das Regras de Negócio (ODS 5 & ODS 18) e parser IBGE."""

from __future__ import annotations

import unittest

import pandas as pd

from dashboard.metrics import agregar_por_dimensao, calcular_kpis, normalizar_colunas_analiticas
from etl.python.enriquecer_ibge import _extrair_campos_municipio


class TestRegrasNegocio(unittest.TestCase):
    def setUp(self) -> None:
        self.df = normalizar_colunas_analiticas(
            pd.DataFrame(
                [
                    {
                        "NU_ANO_CENSO": 2024,
                        "CO_IES": 1,
                        "TP_CATEGORIA_ADMINISTRATIVA": 1,
                        "TP_REDE": 1,
                        "SG_UF": "BA",
                        "CO_MUNICIPIO": 2927408,
                        "NO_REGIAO": "Nordeste",
                        "CO_CURSO": 100,
                        "NO_CURSO": "Ciência da Computação",
                        "NO_CINE_AREA_GERAL": "Computação e Tecnologias da Informação e Comunicação (TIC)",
                        "NO_CINE_AREA_ESPECIFICA": "Computação",
                        "TP_MODALIDADE_ENSINO": 1,
                        "QT_ING": 100,
                        "QT_MAT": 400,
                        "QT_CONC": 50,
                        "QT_SIT_DESVINCULADO": 100,
                        "QT_SIT_TRANCADA": 40,
                        "QT_SIT_TRANSFERIDO": 20,
                        "QT_ING_FEM": 30,
                        "QT_ING_MASC": 70,
                        "QT_MAT_FEM": 100,
                        "QT_MAT_MASC": 300,
                        "QT_CONC_FEM": 20,
                        "QT_CONC_MASC": 30,
                        "QT_ING_BRANCA": 40,
                        "QT_ING_PRETA": 15,
                        "QT_ING_PARDA": 30,
                        "QT_ING_AMARELA": 5,
                        "QT_ING_INDIGENA": 5,
                        "QT_ING_CORND": 5,
                        "QT_MAT_BRANCA": 160,
                        "QT_MAT_PRETA": 60,
                        "QT_MAT_PARDA": 120,
                        "QT_MAT_AMARELA": 10,
                        "QT_MAT_INDIGENA": 10,
                        "QT_MAT_CORND": 40,
                        "QT_CONC_BRANCA": 25,
                        "QT_CONC_PRETA": 5,
                        "QT_CONC_PARDA": 10,
                        "QT_CONC_AMARELA": 2,
                        "QT_CONC_INDIGENA": 3,
                        "QT_CONC_CORND": 5,
                    }
                ]
            )
        )

    def test_kpis_evasao_e_retencao(self) -> None:
        kpis = calcular_kpis(self.df)
        self.assertEqual(kpis["taxa_evasao_matriculas_pct"], 25.0)
        # 100 / (400 + 100 + 50) = 18.18%
        self.assertEqual(kpis["taxa_evasao_vinculos_pct"], 18.18)
        self.assertEqual(kpis["taxa_retencao_pct"], 81.82)
        self.assertEqual(kpis["taxa_trancamento_pct"], 10.0)
        self.assertEqual(kpis["taxa_transferencia_pct"], 5.0)
        self.assertEqual(kpis["razao_conclusao_ingresso_pct"], 50.0)

    def test_kpis_ods5_genero(self) -> None:
        kpis = calcular_kpis(self.df)
        self.assertEqual(kpis["pct_ing_fem"], 30.0)
        self.assertEqual(kpis["pct_mat_fem"], 25.0)
        self.assertEqual(kpis["pct_conc_fem"], 40.0)
        self.assertEqual(kpis["delta_funil_fem_pp"], 10.0)
        self.assertEqual(kpis["gap_paridade_fem_pp"], -25.0)
        self.assertEqual(kpis["ipg_matriculas"], 0.333)

    def test_kpis_ods18_raca_e_veracidade(self) -> None:
        kpis = calcular_kpis(self.df)
        # PPI mat = 60 + 120 + 10 = 190; declarados = 160 + 190 + 10 = 360 -> 52.78%
        self.assertEqual(kpis["pct_mat_ppi_declarado"], 52.78)
        # CORND = 40 / 400 = 10%
        self.assertEqual(kpis["taxa_subnotificacao_racial_pct"], 10.0)

    def test_agregacao_por_dimensao(self) -> None:
        agg = agregar_por_dimensao(self.df, "rede_desc")
        self.assertEqual(len(agg), 1)
        self.assertEqual(agg.loc[0, "rede_desc"], "Pública")
        self.assertEqual(agg.loc[0, "taxa_evasao_matriculas_pct"], 25.0)

    def test_parser_ibge_json(self) -> None:
        item = {
            "id": 2927408,
            "nome": "Salvador",
            "microrregiao": {
                "nome": "Salvador",
                "mesorregiao": {
                    "nome": "Metropolitana de Salvador",
                    "UF": {"sigla": "BA", "regiao": {"nome": "Nordeste"}},
                },
            },
        }
        res = _extrair_campos_municipio(item)
        self.assertIsNotNone(res)
        self.assertEqual(res["id_municipio"], 2927408)
        self.assertEqual(res["nome_municipio"], "Salvador")
        self.assertEqual(res["sigla_uf"], "BA")
        self.assertEqual(res["regiao"], "Nordeste")


if __name__ == "__main__":
    unittest.main()
