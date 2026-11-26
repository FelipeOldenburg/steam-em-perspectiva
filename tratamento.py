"""Etapa 2: validação e preparação reproduzível da base de Nik Davis."""

from pathlib import Path
import json

import pandas as pd

PASTA = Path(__file__).resolve().parent
ARQUIVO = PASTA / "dados" / "steam.csv"
DATA_LIMITE = pd.Timestamp("2019-05-01")
COLUNAS = ["appid", "name", "release_date", "genres", "categories", "price",
           "developer", "publisher", "positive_ratings", "negative_ratings"]
MULTIPLAYER = {"Multi-player", "Online Multi-Player", "Local Multi-Player",
               "Cross-Platform Multiplayer", "Co-op", "Online Co-op",
               "Local Co-op", "Shared/Split Screen", "MMO"}


def tratar_dados(brutos):
    """Preserva preços extremos e não transforma valores ausentes em zero."""
    faltantes = set(COLUNAS) - set(brutos.columns)
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(faltantes)}")
    dados = brutos.copy()
    auditoria = {"linhas_originais": len(dados),
                 "colunas_originais": len(dados.columns),
                 "ausentes_originais": {c: int(v) for c, v in dados.isna().sum().items()}}
    dados = dados.drop_duplicates()
    auditoria["duplicatas_exatas_removidas"] = len(brutos) - len(dados)
    dados["appid"] = pd.to_numeric(dados["appid"], errors="coerce")
    dados["release_date"] = pd.to_datetime(dados["release_date"], format="%Y-%m-%d", errors="coerce")
    dados["name"] = dados["name"].astype("string").str.strip()
    validos = (dados["appid"].notna() & dados["appid"].gt(0)
               & dados["appid"].mod(1).eq(0) & dados["release_date"].notna()
               & dados["release_date"].le(DATA_LIMITE)
               & dados["name"].notna() & dados["name"].ne(""))
    auditoria["registros_invalidos_removidos"] = int((~validos).sum())
    dados = dados.loc[validos].copy()
    if dados["appid"].duplicated().any():
        raise ValueError("Há appids repetidos com informações diferentes; revise a origem.")
    dados["appid"] = dados["appid"].astype("int64")
    for coluna in ["developer", "publisher", "genres", "categories"]:
        dados[coluna] = dados[coluna].astype("string").str.strip().replace("", pd.NA).fillna("Não informado")
    for coluna in ["price", "positive_ratings", "negative_ratings"]:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce").astype(float)
        invalido = dados[coluna].lt(0) | ~dados[coluna].lt(float("inf"))
        if coluna != "price":
            invalido = invalido | dados[coluna].mod(1).ne(0)
        dados.loc[invalido, coluna] = float("nan")
    dados["ano"] = dados["release_date"].dt.year
    inicio = dados["ano"] // 5 * 5
    dados["periodo"] = inicio.astype(str) + "-" + (inicio + 4).astype(str)
    dados["generos_lista"] = dados["genres"].map(lambda texto: list(dict.fromkeys(g.strip() for g in texto.split(";") if g.strip())))
    dados["multiplayer"] = dados["categories"].map(lambda texto: bool(set(texto.split(";")) & MULTIPLAYER)).astype("boolean")
    dados.loc[dados["categories"].eq("Não informado"), "multiplayer"] = pd.NA
    dados["total_avaliacoes"] = dados[["positive_ratings", "negative_ratings"]].sum(axis=1, min_count=2)
    dados["aprovacao"] = 100 * dados["positive_ratings"] / dados["total_avaliacoes"].where(dados["total_avaliacoes"].gt(0))
    auditoria.update({"linhas_tratadas": len(dados),
                      "precos_ausentes_apos_validacao": int(dados["price"].isna().sum()),
                      "aprovacoes_indefinidas": int(dados["aprovacao"].isna().sum()),
                      "data_minima": str(dados["release_date"].min().date()),
                      "data_maxima": str(dados["release_date"].max().date())})
    return dados.sort_values(["release_date", "appid"]).reset_index(drop=True), auditoria


def carregar_dados(caminho=ARQUIVO):
    return tratar_dados(pd.read_csv(caminho))


def filtrar_dados(dados, anos, generos=(), preco="Todos", modo="Todos", incluir_2019=True):
    mascara = dados["ano"].between(*anos)
    if generos:
        mascara &= dados["generos_lista"].map(lambda valores: bool(set(valores) & set(generos)))
    if preco == "Gratuitos":
        mascara &= dados["price"].eq(0)
    elif preco == "Pagos":
        mascara &= dados["price"].gt(0)
    if modo == "Com multiplayer":
        mascara &= dados["multiplayer"].fillna(False)
    elif modo == "Sem multiplayer":
        mascara &= dados["multiplayer"].eq(False).fillna(False)
    if not incluir_2019:
        mascara &= dados["ano"].ne(2019)
    return dados.loc[mascara].copy()


def exportar_csv(dados):
    return dados.drop(columns="generos_lista").to_csv(index=False).encode("utf-8-sig")


if __name__ == "__main__":
    dados, auditoria = carregar_dados()
    (PASTA / "dados" / "steam_tratado.csv").write_bytes(exportar_csv(dados))
    (PASTA / "dados" / "auditoria.json").write_text(json.dumps(auditoria, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(auditoria, indent=2, ensure_ascii=False))
