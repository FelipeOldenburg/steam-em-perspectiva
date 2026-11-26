"""Etapa 3: oito gráficos Plotly e interpretações calculadas sobre o recorte."""

from pathlib import Path
import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.io import to_html

from tratamento import carregar_dados

AZUL = "#17618C"
LARANJA = "#A94E12"
CORES = [AZUL, "#A94E12", "#277A64", "#755292", "#9B3757", "#54741E", "#77643A", "#525D70"]


def numero(valor, casas=0):
    if pd.isna(valor):
        return "sem dados"
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def preparar_tabelas(dados, minimo_avaliacoes=10):
    anos = range(int(dados.ano.min()), int(dados.ano.max()) + 1)
    anual = dados.groupby("ano").agg(jogos=("appid", "size"),
                                    multiplayer=("multiplayer", "sum"),
                                    modo_conhecido=("multiplayer", "count"),
                                    preco_mediano=("price", "median")).reindex(anos)
    anual.index.name = "ano"
    anual["jogos"] = anual["jogos"].fillna(0).astype(int)
    anual["multiplayer_pct"] = 100 * anual["multiplayer"] / anual["modo_conhecido"].where(anual["modo_conhecido"].gt(0))
    anual = anual.reset_index()
    generos = dados.explode("generos_lista").rename(columns={"generos_lista": "genero"}).drop_duplicates(["appid", "genero"])
    ranking = generos.groupby("genero").appid.nunique().sort_values(ascending=False).head(10).rename("jogos").reset_index()
    ranking["participacao"] = 100 * ranking["jogos"] / len(dados)
    top = ranking.genero.head(6).tolist()
    contagens = generos[generos.genero.isin(top)].groupby(["genero", "ano"]).appid.nunique().unstack("ano").reindex(index=top, columns=anos).fillna(0)
    denominadores = anual.set_index("ano").jogos.replace(0, float("nan"))
    penetracao = contagens.div(denominadores, axis=1) * 100
    avaliacoes = generos[generos.total_avaliacoes.ge(minimo_avaliacoes) & generos.aprovacao.notna()]
    avaliacoes = avaliacoes[avaliacoes.genero.isin(ranking.genero.head(8))]
    return {"anual": anual, "generos": generos, "ranking": ranking,
            "penetracao": penetracao, "avaliacoes": avaliacoes}


def criar_graficos(dados, minimo_avaliacoes=10):
    if dados.empty:
        return []
    t = preparar_tabelas(dados, minimo_avaliacoes)
    anual, ranking = t["anual"], t["ranking"]
    completos = anual[anual.ano.lt(2019)]
    registros = []

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=completos.ano, y=completos.jogos, mode="lines+markers", name="Anos até 2018", line_color=AZUL))
    parcial = anual[anual.ano.eq(2019)]
    fig.add_trace(go.Scatter(x=parcial.ano, y=parcial.jogos, mode="markers", marker={"color": LARANJA, "size": 11, "symbol": "diamond"}, name="2019: até 01/05"))
    fig.update_layout(title="1. Registros por ano de lançamento", xaxis_title="Ano de lançamento informado", yaxis_title="Jogos na base", legend_title="Cobertura")
    if not completos.empty:
        pico = completos.loc[completos.jogos.idxmax()]
        texto = f"Entre os anos até 2018 deste recorte, {int(pico.ano)} reúne mais registros: {numero(pico.jogos)}. O ponto de 2019 é parcial e não indica, por si só, uma queda anual."
    else:
        texto = "O recorte contém apenas 2019, coberto até 1º de maio; não é possível comparar anos completos."
    registros.append(("lancamentos", fig, "A quantidade de jogos cresceu ao longo dos anos?", texto))

    fig = px.bar(ranking.sort_values("jogos"), x="jogos", y="genero", orientation="h", color_discrete_sequence=[AZUL], hover_data={"participacao": ":.1f"}, labels={"jogos": "Jogos com o rótulo", "genero": "Gênero / rótulo original", "participacao": "Participação (%)"}, title="2. Rótulos de gênero mais frequentes")
    lider = ranking.iloc[0]
    texto = f"{lider.genero} aparece em {numero(lider.jogos)} jogos ({numero(lider.participacao, 1)}% do recorte). Um jogo pode ter vários rótulos; as participações não devem somar 100%."
    registros.append(("generos", fig, "Quais gêneros são mais frequentes?", texto))

    fig = px.imshow(t["penetracao"], aspect="auto", color_continuous_scale="Blues", zmin=0, zmax=100, labels={"x": "Ano de lançamento informado", "y": "Rótulo de gênero", "color": "% dos jogos"}, title="3. Participação dos gêneros por ano")
    fig.update_xaxes(type="category")
    texto = "Cada célula mostra a porcentagem de jogos daquele ano com o rótulo, e não o total de lançamentos. Anos com poucos jogos são instáveis; células sem registros ficam vazias. 2019 tem cobertura parcial."
    registros.append(("generos_tempo", fig, "A composição dos gêneros mudou entre os anos?", texto))

    precos = dados[dados.price.notna()]
    fig = px.histogram(precos, x="price", nbins=50, color_discrete_sequence=[AZUL], labels={"price": "Preço na coleta de 2019 (GBP)"}, title="4. Distribuição dos preços registrados")
    fig.update_layout(yaxis_title="Quantidade de jogos", bargap=0.06)
    limite = max(1, float(precos.price.quantile(0.99))) if not precos.empty else 1
    fig.update_traces(xbins={"start": 0, "end": float(precos.price.max()) + 1 if not precos.empty else 1, "size": max(0.5, limite / 30)})
    fig.update_xaxes(range=[0, limite])
    texto = f"A mediana é £{numero(precos.price.median(), 2)} e a média é £{numero(precos.price.mean(), 2)}. Há {numero(precos.price.eq(0).sum())} jogos com preço zero. A vista inicial vai até o percentil 99 (£{numero(limite, 2)}); {numero(precos.price.gt(limite).sum())} preços acima dele permanecem nos dados. Use Autoscale para ver toda a faixa."
    registros.append(("precos", fig, "Os preços se concentram em qual faixa?", texto))

    pagos = dados[dados.price.gt(0)]
    fig = px.box(pagos, x="periodo", y="price", category_orders={"periodo": sorted(dados.periodo.unique())}, points=False, log_y=True, color_discrete_sequence=[AZUL], labels={"periodo": "Período do lançamento", "price": "Preço (GBP; escala logarítmica)"}, title="5. Preços dos pagos por período")
    texto = "A linha central é a mediana; a caixa contém os 50% centrais e as hastes seguem a regra de 1,5 intervalo interquartil. O eixo de preço é logarítmico para facilitar a leitura. Pontos extremos ficam ocultos só neste gráfico, sem excluir linhas dos cálculos. São preços de uma única coleta."
    if pagos.empty:
        fig.add_annotation(text="Não há jogos pagos neste recorte.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    registros.append(("precos_periodo", fig, "Jogos lançados em períodos diferentes têm preços diferentes na coleta?", texto))

    fig = px.line(anual, x="ano", y="multiplayer_pct", markers=True, color_discrete_sequence=[AZUL], hover_data=["jogos", "multiplayer", "modo_conhecido"], labels={"ano": "Ano de lançamento informado", "multiplayer_pct": "Jogos com multiplayer (%)", "jogos": "Total no ano", "multiplayer": "Com multiplayer", "modo_conhecido": "Categoria conhecida"}, title="6. Participação de multiplayer por ano")
    fig.update_yaxes(range=[0, 105])
    texto = f"{numero(100 * dados.multiplayer.mean(), 1)}% dos jogos com categoria conhecida neste recorte têm multiplayer ou modo cooperativo. O percentual permite comparar a composição dos anos; contagem absoluta maior não implica participação maior."
    registros.append(("multiplayer", fig, "O multiplayer passou a aparecer com mais frequência relativa?", texto))

    fig = px.box(t["avaliacoes"], x="genero", y="aprovacao", points=False, color_discrete_sequence=[AZUL], labels={"genero": "Gênero / rótulo", "aprovacao": "Avaliações positivas por jogo (%)"}, title=f"7. Aprovação por gênero<br><sup>Mínimo de {minimo_avaliacoes} avaliações por jogo</sup>")
    fig.update_yaxes(range=[0, 105])
    texto = f"São considerados jogos com pelo menos {minimo_avaliacoes} avaliações. Cada jogo tem o mesmo peso na distribuição; jogos com vários gêneros aparecem em mais de uma caixa. O filtro reduz, mas não elimina, a instabilidade de amostras pequenas."
    if t["avaliacoes"].empty:
        fig.add_annotation(text="Nenhum jogo atende ao mínimo de avaliações.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    registros.append(("avaliacoes_genero", fig, "Como as avaliações variam entre gêneros?", texto))

    dispersao = dados[dados.total_avaliacoes.ge(minimo_avaliacoes) & dados.price.notna() & dados.aprovacao.notna()].copy()
    dispersao["modo"] = dispersao.multiplayer.map({True: "Com multiplayer", False: "Sem multiplayer"}).fillna("Não informado")
    fig = px.scatter(dispersao, x="price", y="aprovacao", color="modo", hover_name="name", hover_data={"total_avaliacoes": ":,.0f", "ano": True}, opacity=0.45, color_discrete_map={"Com multiplayer": LARANJA, "Sem multiplayer": AZUL, "Não informado": "#555555"}, labels={"price": "Preço na coleta de 2019 (GBP)", "aprovacao": "Avaliações positivas (%)", "modo": "Modo de jogo", "total_avaliacoes": "Avaliações", "ano": "Ano"}, title=f"8. Preço e aprovação<br><sup>Mínimo de {minimo_avaliacoes} avaliações por jogo</sup>")
    fig.update_yaxes(range=[0, 105])
    correlacao = dispersao[["price", "aprovacao"]].rank().corr().iloc[0, 1]
    texto = f"A correlação de Spearman entre preço e aprovação é {numero(correlacao, 3)} em {numero(len(dispersao))} jogos elegíveis. Associação não demonstra que o preço cause a aprovação; gênero, qualidade e tempo de exposição também podem influenciar."
    if dispersao.empty:
        fig.add_annotation(text="Nenhum jogo atende aos critérios.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    registros.append(("preco_aprovacao", fig, "Jogos mais caros recebem avaliações melhores?", texto))

    for _, figura, _, _ in registros:
        figura.update_layout(template="plotly_white", font={"family": "Arial, sans-serif", "size": 13, "color": "#243747"}, height=420, margin={"l": 45, "r": 25, "t": 65, "b": 65}, title_font_size=18, legend={"orientation": "h", "y": -0.3}, paper_bgcolor="white", plot_bgcolor="white")
        figura.update_xaxes(automargin=True)
        figura.update_yaxes(automargin=True)
    return registros


if __name__ == "__main__":
    dados, _ = carregar_dados()
    partes = ["<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Análise da Steam</title><style>body{font:16px/1.6 Arial;color:#243747;max-width:1100px;margin:40px auto;padding:0 20px}section{margin:48px 0}h1,h2{line-height:1.2}small{color:#475569}</style><h1>Como os jogos mudaram ao longo dos anos?</h1><p>Felipe Oldenburg da Silva · Alicia Cariny Borges</p><p>27.075 registros, de 1997 até 01/05/2019. Preços em GBP na coleta. 2019 é parcial. Use o cursor, a legenda, o zoom e a barra de ferramentas dos gráficos.</p>"]
    for i, (chave, figura, pergunta, texto) in enumerate(criar_graficos(dados)):
        partes.append(f"<section><h2>{html.escape(pergunta)}</h2>" + to_html(figura, full_html=False, include_plotlyjs=True if i == 0 else False) + f"<p>{html.escape(texto)}</p></section>")
    partes.append("<footer>Fonte: <a href='https://www.kaggle.com/datasets/nikdavis/steam-store-games'>Nik Davis / Kaggle</a>, CC BY 4.0. Steam Store e SteamSpy. Este arquivo permite explorar cada gráfico; os filtros compartilhados estão no aplicativo Streamlit.</footer></html>")
    destino = Path(__file__).resolve().parent / "analise_interativa.html"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"Análise interativa salva em {destino.name}")
