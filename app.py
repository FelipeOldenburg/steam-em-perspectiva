"""Etapa 4: execute com python -m streamlit run app.py."""

import pandas as pd
import streamlit as st

from tratamento import carregar_dados, filtrar_dados, exportar_csv
from analise import criar_graficos, numero

st.set_page_config(page_title="Steam em perspectiva", page_icon="📊", layout="wide")


@st.cache_data
def obter_base():
    return carregar_dados()


st.title("Steam em perspectiva")
st.markdown("### Como os jogos mudaram ao longo dos anos?")
st.write("Explore lançamentos, gêneros, preços e avaliações de 27.075 registros da Steam. Uma fotografia do catálogo coletada em 2019, com datas de lançamento de 1997 a 1º de maio de 2019.")
st.caption("Felipe Oldenburg da Silva · Alicia Cariny Borges | Trabalho prático de Análise de Dados | Etapas 2, 3 e 4")

try:
    base, auditoria = obter_base()
except (OSError, ValueError, pd.errors.ParserError) as erro:
    st.error(f"Não foi possível carregar a base: {erro}. Confira dados/steam.csv.")
    st.stop()

with st.sidebar:
    st.header("Explore o catálogo")
    st.caption("Os filtros atualizam todos os indicadores, gráficos e a tabela.")
    anos = st.slider("Ano de lançamento", int(base.ano.min()), int(base.ano.max()), (int(base.ano.min()), int(base.ano.max())))
    generos = st.multiselect("Gêneros / rótulos", sorted(base.generos_lista.explode().unique()), help="Sem seleção = todos. Com vários rótulos, basta que o jogo tenha um deles.")
    preco = st.radio("Preço registrado", ["Todos", "Gratuitos", "Pagos"])
    modo = st.selectbox("Modo de jogo", ["Todos", "Com multiplayer", "Sem multiplayer"])
    incluir_2019 = st.checkbox("Incluir 2019 (ano parcial)", value=True)
    minimo = st.select_slider("Mínimo de avaliações (gráficos 7 e 8)", options=[1, 10, 50, 100, 500, 1000], value=10)
    st.caption("Multiplayer inclui modalidades online, locais e cooperativas. Um jogo pode também ser single-player.")

dados = filtrar_dados(base, anos, generos, preco, modo, incluir_2019)
st.caption(f"Recorte ativo: {numero(len(dados))} de {numero(len(base))} jogos | {anos[0]}–{anos[1]} | Preço: {preco.lower()} | Modo: {modo.lower()}")
if dados.empty:
    st.warning("Nenhum jogo corresponde aos filtros. Amplie o período ou retire uma seleção na barra lateral.")
    st.stop()

colunas = st.columns(4)
colunas[0].metric("Jogos no recorte", numero(len(dados)))
colunas[1].metric("Preço mediano na coleta", "£" + numero(dados.price.median(), 2))
colunas[2].metric("Jogos com preço zero", numero(100 * dados.price.eq(0).sum() / dados.price.notna().sum(), 1) + "%" if dados.price.notna().any() else "sem dados")
colunas[3].metric("Com multiplayer", numero(100 * dados.multiplayer.mean(), 1) + "%")
st.info("Leitura correta: 2019 termina em 1º de maio. Os preços são de uma única coleta em GBP, não preços históricos de lançamento. As datas antigas podem anteceder a entrada dos jogos na Steam.")

graficos = criar_graficos(dados, minimo)
for titulo, inicio in [("Lançamentos e composição do catálogo", 0), ("Gêneros no tempo e distribuição de preços", 2), ("Períodos de lançamento e modos de jogo", 4), ("Avaliações dos jogadores", 6)]:
    st.header(titulo)
    colunas = st.columns(2)
    for coluna, (chave, figura, pergunta, texto) in zip(colunas, graficos[inicio:inicio + 2]):
        with coluna:
            st.plotly_chart(figura, width="stretch", key=chave, config={"displaylogo": False})
            st.markdown(f"**Pergunta:** {pergunta}")
            st.write(texto)

with st.expander("Dados do recorte e download"):
    tabela = dados[["appid", "name", "release_date", "genres", "price", "multiplayer", "total_avaliacoes", "aprovacao"]]
    st.dataframe(tabela.rename(columns={"appid": "ID", "name": "Jogo", "release_date": "Lançamento", "genres": "Rótulos", "price": "Preço (GBP)", "multiplayer": "Multiplayer", "total_avaliacoes": "Avaliações", "aprovacao": "Aprovação (%)"}), hide_index=True, width="stretch")
    st.download_button("Baixar dados filtrados (CSV)", exportar_csv(dados), file_name="steam_filtrado.csv", mime="text/csv")

with st.expander("Como os dados foram tratados e como ler os resultados"):
    st.write("A base distribuída pelo autor já passou por limpeza. Aqui foram conferidos tipos, datas, identificadores únicos, preços e avaliações; textos foram padronizados e campos derivados foram calculados. Nenhum preço extremo foi removido.")
    st.write("Aprovação por jogo = positivas / (positivas + negativas) × 100. A distribuição por gênero dá o mesmo peso a cada jogo. Zero avaliações significa aprovação indefinida, nunca 0%. O mínimo de avaliações modifica somente os gráficos 7 e 8.")
    st.write("Os rótulos do campo genres são os originais: incluem gêneros e metadados como Indie, Early Access e Free to Play. Cada jogo pode pertencer a vários grupos. A base pode conter alguns aplicativos que não são jogos e não representa todo o mercado.")
    st.write("Multiplayer é a presença de ao menos uma categoria de jogo em grupo, incluindo cooperação e tela compartilhada. A ausência de categoria conhecida fica sem classificação.")
    st.json(auditoria, expanded=False)

st.divider()
st.markdown("**Fonte dos dados:** [Steam Store Games — Nik Davis, Kaggle](https://www.kaggle.com/datasets/nikdavis/steam-store-games), licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Dados provenientes da Steam Store e SteamSpy. Cópia e alterações documentadas em `FONTES.txt`.")
st.caption("Referência de organização: ciencia-dados.streamlit.app. A análise descreve esta amostra histórica e não estabelece relações de causa e efeito.")
