"""Verificações da limpeza, dos filtros e dos estados reais do dashboard."""

from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest

from tratamento import carregar_dados, tratar_dados, filtrar_dados
from analise import criar_graficos


def verificar():
    base, auditoria = carregar_dados()
    assert len(base) == 27075 and base.appid.is_unique
    assert auditoria["data_maxima"] == "2019-05-01"
    assert base.price.min() == 0 and base.price.max() == 421.99
    assert base.aprovacao.between(0, 100).all()
    assert len(criar_graficos(base)) == 8
    assert len(filtrar_dados(base, (2018, 2018))) == 8160
    gratuitos = filtrar_dados(base, (1997, 2019), preco="Gratuitos")
    assert gratuitos.price.eq(0).all()
    indie = filtrar_dados(base, (1997, 2019), generos=["Indie"])
    assert len(indie) == 19421
    contabilidade = filtrar_dados(base, (1997, 2019), generos=["Accounting"])
    lancamentos = criar_graficos(contabilidade)[0][1].data[0]
    assert list(lancamentos.x) == [2016, 2017, 2018]
    assert list(lancamentos.y) == [2, 0, 4]
    assert not filtrar_dados(base, (1997, 2019), incluir_2019=False).ano.eq(2019).any()
    assert filtrar_dados(base, (1997, 1997), generos=["Accounting"]).empty
    caso = base.iloc[[0]].drop(columns=["ano", "periodo", "generos_lista", "multiplayer", "total_avaliacoes", "aprovacao"]).copy()
    caso["positive_ratings"] = 0
    caso["negative_ratings"] = 0
    caso["price"] = -1
    tratado, _ = tratar_dados(caso)
    assert pd.isna(tratado.iloc[0].aprovacao) and pd.isna(tratado.iloc[0].price)
    caso["release_date"] = "data inválida"
    assert tratar_dados(caso)[0].empty
    original = pd.read_csv(Path(__file__).with_name("dados") / "steam.csv").iloc[[0]]
    duplicados = pd.concat([original, original.assign(price=999)], ignore_index=True)
    try:
        tratar_dados(duplicados)
    except ValueError:
        pass
    else:
        raise AssertionError("Identificadores conflitantes não foram rejeitados")

    app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=90).run()
    assert not app.exception, str(app.exception)
    assert len(app.get("plotly_chart")) == 8
    assert app.metric[0].value == "27.075"
    app.checkbox[0].set_value(False).run()
    assert not app.exception and app.metric[0].value == "24.862"
    app.checkbox[0].set_value(True).run()
    app.select_slider[0].set_value(100).run()
    assert not app.exception and app.metric[0].value == "27.075" and len(app.get("plotly_chart")) == 8
    app.select_slider[0].set_value(10).run()
    app.slider[0].set_value((2018, 2018)).run()
    assert not app.exception and app.metric[0].value == "8.160"
    app.radio[0].set_value("Gratuitos").run()
    assert not app.exception and app.metric[1].value == "£0,00"
    assert app.metric[2].value == "100,0%"
    app.selectbox[0].set_value("Com multiplayer").run()
    assert not app.exception and app.metric[3].value == "100,0%"
    app.multiselect[0].set_value(["Accounting"]).run()
    assert not app.exception and len(app.warning) == 1 and len(app.get("plotly_chart")) == 0
    print("OK: base, oito gráficos, dados inválidos, filtros combinados e estado vazio.")


if __name__ == "__main__":
    verificar()
