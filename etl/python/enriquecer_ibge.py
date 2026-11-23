"""Ingestão de dados semi-estruturados (JSON) da API de Localidades do IBGE.

Enriquece a dimensão de localidades (`dim_localidade`) com nome oficial do
município, microrregião e mesorregião, atendendo ao V de Variedade (dados
semi-estruturados via API pública governamental).
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IBGE_MUNICIPIOS_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
)


def _extrair_campos_municipio(item: dict[str, Any]) -> dict[str, Any] | None:
    """Normaliza um registro JSON aninhado da API do IBGE."""
    codigo = item.get("id")
    if codigo is None:
        return None

    microrregiao_obj = item.get("microrregiao") or {}
    mesorregiao_obj = microrregiao_obj.get("mesorregiao") or {}
    uf_obj = mesorregiao_obj.get("UF") or {}
    regiao_obj = uf_obj.get("regiao") or {}

    # Fallback para estrutura regiao-imediata/regiao-intermediaria (casos sem microrregiao)
    if not uf_obj:
        imediata = item.get("regiao-imediata") or {}
        intermediaria = imediata.get("regiao-intermediaria") or {}
        uf_obj = intermediaria.get("UF") or {}
        regiao_obj = uf_obj.get("regiao") or {}
        if not mesorregiao_obj:
            mesorregiao_obj = intermediaria

    return {
        "id_municipio": int(codigo),
        "nome_municipio": item.get("nome"),
        "microrregiao": microrregiao_obj.get("nome"),
        "mesorregiao": mesorregiao_obj.get("nome"),
        "sigla_uf": uf_obj.get("sigla"),
        "regiao": regiao_obj.get("nome"),
    }


def buscar_municipios_ibge(
    saida_mapa: str | Path = "data/processed/dim_municipios_ibge.json",
    saida_bruto: str | Path = "data/processed/ibge_municipios_raw.json",
    timeout: int = 30,
) -> dict[str, dict[str, Any]]:
    """Consulta a API pública do IBGE e persiste JSON bruto + mapa normalizado."""
    req = urllib.request.Request(
        IBGE_MUNICIPIOS_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "observatorio-evasao-stem/1.0 (BigData-UCSAL)",
        },
    )

    print(f"Consultando API de Localidades do IBGE: {IBGE_MUNICIPIOS_URL}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Falha ao consultar a API do IBGE ({IBGE_MUNICIPIOS_URL}): {exc}"
        ) from exc

    mapa: dict[str, dict[str, Any]] = {}
    for item in payload:
        normalizado = _extrair_campos_municipio(item)
        if normalizado:
            mapa[str(normalizado["id_municipio"])] = normalizado

    metadados_brutos = {
        "fonte": "IBGE - API de Localidades (Dados Abertos)",
        "url": IBGE_MUNICIPIOS_URL,
        "formato": "JSON (semi-estruturado)",
        "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
        "total_municipios": len(mapa),
        "amostra_registros": payload[:5],
    }

    saida_mapa_path = Path(saida_mapa)
    saida_bruto_path = Path(saida_bruto)
    saida_mapa_path.parent.mkdir(parents=True, exist_ok=True)
    saida_bruto_path.parent.mkdir(parents=True, exist_ok=True)

    saida_bruto_path.write_text(
        json.dumps(metadados_brutos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    saida_mapa_path.write_text(
        json.dumps(mapa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Sucesso! {len(mapa)} municípios indexados em: {saida_mapa_path}")
    print(f"Metadados semi-estruturados salvos em: {saida_bruto_path}")
    return mapa


def carregar_mapa_ibge(
    caminho: str | Path = "data/processed/dim_municipios_ibge.json",
) -> dict[int, dict[str, Any]]:
    """Carrega o mapa de municípios IBGE se o arquivo existir."""
    path = Path(caminho)
    if not path.exists():
        return {}
    dados = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): v for k, v in dados.items()}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consome a API de Localidades do IBGE (JSON semi-estruturado)."
    )
    parser.add_argument(
        "--saida-mapa",
        default="data/processed/dim_municipios_ibge.json",
        help="Caminho do JSON normalizado por código IBGE do município.",
    )
    parser.add_argument(
        "--saida-bruto",
        default="data/processed/ibge_municipios_raw.json",
        help="Caminho do JSON de metadados e amostra da resposta da API.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout da requisição HTTP em segundos.",
    )
    args = parser.parse_args()
    buscar_municipios_ibge(args.saida_mapa, args.saida_bruto, args.timeout)


if __name__ == "__main__":
    main()
