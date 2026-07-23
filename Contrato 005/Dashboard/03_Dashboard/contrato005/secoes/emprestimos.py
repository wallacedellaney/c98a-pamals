"""Tela "Empréstimos" — material emprestado/retirado de estoque e o que
falta devolver, a partir da planilha "Devoluções". Ver
00_Instrucoes/emprestimos.md.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from contrato005.components import data_global
from contrato005.components.paleta import AMBER, CATEGORICA, STATUS, layout_grafico
from contrato005.components.utils import ordenar_unicos


def _datas_disponiveis(historico):
    if historico is None or historico.empty:
        return []
    return sorted(pd.to_datetime(historico["data_snapshot"]).dt.date.unique())


def _quantidade_efetiva_historico(df_dia):
    """Mesma regra da tela inteira: linha sem quantidade registrada conta
    como 1. Snapshots de antes de 2026-07-23 nem têm a coluna "quantidade"
    (acrescentada nessa data) — nesse caso todas contam como 1."""
    if "quantidade" not in df_dia.columns:
        return pd.Series(1.0, index=df_dia.index)
    return df_dia["quantidade"].fillna(1)


def _diff_dias(historico, data_anterior, data_atual):
    """Compara o snapshot de `data_anterior` com o de `data_atual` (ambos
    datetime.date), por numero_ordem: pedidos novos (apareceram) e
    devolvidos (status virou "OK" e antes não era). Outras mudanças de
    status (ex.: virou "Desconsiderado") entram num 3º grupo, só pra não
    sumir silenciosamente."""
    hist = historico.copy()
    hist["data_snapshot"] = pd.to_datetime(hist["data_snapshot"]).dt.date

    ant = hist[hist["data_snapshot"] == data_anterior].set_index("numero_ordem")
    atu = hist[hist["data_snapshot"] == data_atual].set_index("numero_ordem")
    chaves_ant, chaves_atu = set(ant.index), set(atu.index)

    novos_chaves = chaves_atu - chaves_ant
    devolvidos_chaves, outras_chaves = [], []
    for chave in chaves_ant & chaves_atu:
        s_ant, s_atu = ant.loc[chave, "status"], atu.loc[chave, "status"]
        if s_ant != s_atu:
            (devolvidos_chaves if s_atu == "OK" else outras_chaves).append(chave)

    def _subset(chaves):
        return atu.loc[sorted(chaves)].reset_index() if chaves else atu.iloc[0:0].reset_index()

    return {"novos": _subset(novos_chaves), "devolvidos": _subset(devolvidos_chaves), "outras": _subset(outras_chaves)}


def _secao_o_que_mudou(historico):
    st.markdown("##### O que mudou de um dia para o outro")
    datas = _datas_disponiveis(historico)
    if len(datas) < 2:
        st.caption("Ainda não há histórico suficiente pra comparar 2 dias.")
        return
    data_atual, data_anterior = datas[-1], datas[-2]
    st.caption(f"Comparando {data_anterior.strftime('%d/%m/%Y')} → {data_atual.strftime('%d/%m/%Y')}")

    diff = _diff_dias(historico, data_anterior, data_atual)
    novos, devolvidos = diff["novos"], diff["devolvidos"]
    qtd_novos = _quantidade_efetiva_historico(novos).sum()
    qtd_devolvidos = _quantidade_efetiva_historico(devolvidos).sum()

    c1, c2 = st.columns(2)
    c1.metric("Novos pedidos", len(novos), f"{qtd_novos:,.0f} unid.".replace(",", "."), delta_color="off")
    c2.metric("Devolvidos", len(devolvidos), f"{qtd_devolvidos:,.0f} unid.".replace(",", "."), delta_color="off")

    if not diff["outras"].empty:
        with st.expander(f"⚠️ {len(diff['outras'])} item(ns) com outra mudança de status (ex.: virou Desconsiderado)"):
            st.dataframe(diff["outras"][["numero_ordem", "part_number", "destino", "status"]],
                         hide_index=True, width="stretch")

    if not novos.empty or not devolvidos.empty:
        with st.expander("Ver os itens que mudaram"):
            if not novos.empty:
                st.caption("Novos pedidos")
                st.dataframe(novos[["numero_ordem", "part_number", "categoria", "destino", "anv"]],
                             hide_index=True, width="stretch")
            if not devolvidos.empty:
                st.caption("Devolvidos")
                st.dataframe(devolvidos[["numero_ordem", "part_number", "categoria", "destino", "anv"]],
                             hide_index=True, width="stretch")


def _semanas_disponiveis(datas):
    """Segundas-feiras de cada semana que tem pelo menos 1 snapshot —
    "semana" pro Wallace é sempre segunda a sexta (2026-07-23: "semana
    entenda de segunda a sexta")."""
    segundas = sorted({d - pd.Timedelta(days=d.weekday()) for d in datas})
    return segundas


def _secao_semana(historico):
    st.markdown("##### Histórico da semana (segunda a sexta)")
    datas = _datas_disponiveis(historico)
    if not datas:
        st.caption("Ainda não há histórico suficiente.")
        return
    semanas = _semanas_disponiveis(datas)

    semana_escolhida = st.selectbox(
        "Semana", semanas, index=len(semanas) - 1,
        format_func=lambda seg: f"Semana de {seg.strftime('%d/%m/%Y')} a {(seg + pd.Timedelta(days=4)).strftime('%d/%m/%Y')}",
        key="emp_semana",
    )

    hist = historico.copy()
    hist["data_snapshot"] = pd.to_datetime(hist["data_snapshot"]).dt.date
    dias_uteis = [semana_escolhida + pd.Timedelta(days=i) for i in range(5)]
    nomes_dia = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

    linhas = []
    dia_anterior_com_dado = None
    # Acha o último snapshot antes do início da semana, pra calcular o
    # "novos/devolvidos" do próprio segunda-feira também (comparado com a
    # sexta da semana anterior, não só a partir de terça).
    anteriores = [d for d in datas if d < semana_escolhida]
    if anteriores:
        dia_anterior_com_dado = anteriores[-1]

    for nome, dia in zip(nomes_dia, dias_uteis):
        if dia not in datas:
            linhas.append({"Dia": nome, "Data": dia.strftime("%d/%m"), "Pendentes": "—", "Devolvidos (OK)": "—",
                            "Total": "—", "Novos": "—", "Devolvidos no dia": "—"})
            continue
        df_dia = hist[hist["data_snapshot"] == dia]
        pendentes = int((df_dia["status"] == "Pendente").sum())
        ok = int((df_dia["status"] == "OK").sum())
        total = len(df_dia)
        if dia_anterior_com_dado is not None:
            diff = _diff_dias(historico, dia_anterior_com_dado, dia)
            novos, devolvidos_dia = str(len(diff["novos"])), str(len(diff["devolvidos"]))
        else:
            novos, devolvidos_dia = "—", "—"
        # Colunas viram texto de propósito (mesmo as numéricas) — misturar
        # número e "—" na mesma coluna quebra a conversão pra Arrow do
        # st.dataframe (bug real visto ao testar: ArrowInvalid "Could not
        # convert '—'... to int64").
        linhas.append({"Dia": nome, "Data": dia.strftime("%d/%m"), "Pendentes": str(pendentes),
                        "Devolvidos (OK)": str(ok), "Total": str(total), "Novos": novos,
                        "Devolvidos no dia": devolvidos_dia})
        dia_anterior_com_dado = dia

    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
    st.caption(
        "\"Novos\"/\"Devolvidos no dia\" comparam com o snapshot anterior disponível (o dia útil de "
        "antes, mesmo que seja da semana passada). \"—\" = sem relatório salvo naquele dia (raro num dia útil)."
    )


def _linha_mensal(df, coluna_data, cor):
    serie = df.dropna(subset=[coluna_data]).copy()
    if serie.empty:
        st.info("Sem datas registradas ainda.")
        return
    serie["mes"] = pd.to_datetime(serie[coluna_data]).dt.to_period("M").astype(str)
    contagem = serie.groupby("mes")["quantidade_efetiva"].sum().reset_index(name="quantidade").sort_values("mes")
    fig = px.line(contagem, x="mes", y="quantidade", markers=True, color_discrete_sequence=[cor])
    fig.update_layout(xaxis_title="", yaxis_title="Quantidade")
    layout_grafico(fig, altura=230)
    st.plotly_chart(fig, width="stretch")


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "devolucoes"):
        return

    st.title("Empréstimos")
    st.caption(
        "Material retirado do estoque/emprestado e pendente de devolução — fonte: planilha \"Devoluções\". "
        "Ver 00_Instrucoes/emprestimos.md."
    )

    df = dados.get("devolucoes")
    if df is None or df.empty:
        st.info("Ainda não foi carregado — ver 00_Instrucoes/emprestimos.md pra buscar do Drive.")
        return

    atualizado_em = dados.get("devolucoes_atualizado_em")
    if atualizado_em:
        st.caption(f"Última atualização: **{datetime.fromtimestamp(atualizado_em).strftime('%d/%m/%Y %H:%M')}**")

    # Uma linha de pedido pode ser de mais de 1 unidade (ex.: "10 EA" numa
    # linha só) — pra estatística de quantidade, pesamos pela coluna
    # "quantidade" (não só contamos linhas). Pedido do Wallace em
    # 2026-07-12 e reconfirmado em 2026-07-13 ("tem q multiplicar as
    # linhas pela quantidade, ai a gente consegue ver quantos itens foram
    # emprestados e quantos foram devolvidos"). Linha sem quantidade
    # registrada conta como 1 (mesma unidade mínima de antes).
    df = df.copy()
    df["quantidade_efetiva"] = df["quantidade"].fillna(1)

    total = len(df)
    total_qtd = df["quantidade_efetiva"].sum()
    pendentes = int((df["status"] == "Pendente").sum())
    ok = int((df["status"] == "OK").sum())
    pendentes_qtd = df.loc[df["status"] == "Pendente", "quantidade_efetiva"].sum()
    ok_qtd = df.loc[df["status"] == "OK", "quantidade_efetiva"].sum()
    pct_ok = round(100 * ok / total) if total else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de itens (linhas)", total)
    c2.metric("Total de quantidade", f"{total_qtd:,.0f}".replace(",", "."))
    c3.metric("Emprestados, pendentes (quantidade)", f"{pendentes_qtd:,.0f}".replace(",", "."), delta_color="inverse")
    c4.metric("Devolvidos, OK (quantidade)", f"{ok_qtd:,.0f}".replace(",", "."))
    c5.metric("% concluído", f"{pct_ok}%")
    st.caption(
        "\"Total de quantidade\" soma a coluna Quantidade de cada linha (não é a mesma unidade de "
        "medida sempre — EA, GM, LB etc. somados juntos), pra dar noção de volume além da contagem de "
        "linhas. \"Pendentes\"/\"OK\" em quantidade mostram quantos itens ainda faltam devolver x quantos "
        "já foram devolvidos, de verdade (não só quantas linhas de pedido)."
    )

    st.divider()
    historico = dados.get("historico_devolucoes")
    col_mudou, col_semana = st.columns(2)
    with col_mudou:
        _secao_o_que_mudou(historico)
    with col_semana:
        _secao_semana(historico)

    st.divider()
    st.write("")
    col_linha, col_qtd = st.columns(2)
    with col_linha:
        st.caption("Devolvido: por linha (itens/pedidos)")
        contagem_linha = df["status"].value_counts().reset_index()
        contagem_linha.columns = ["status", "linhas"]
        fig = px.pie(
            contagem_linha, names="status", values="linhas", hole=0.55,
            color="status", color_discrete_map={"Pendente": STATUS["critical"], "OK": STATUS["good"]},
        )
        fig.update_traces(textinfo="value+percent", textfont_size=11)
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    with col_qtd:
        st.caption("Devolvido: por quantidade (unidades)")
        contagem_qtd = df.groupby("status")["quantidade_efetiva"].sum().reset_index()
        contagem_qtd.columns = ["status", "quantidade"]
        fig = px.pie(
            contagem_qtd, names="status", values="quantidade", hole=0.55,
            color="status", color_discrete_map={"Pendente": STATUS["critical"], "OK": STATUS["good"]},
        )
        fig.update_traces(textinfo="value+percent", textfont_size=11)
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")
    st.caption(
        "Os dois gráficos mostram a mesma coisa (Pendente x OK), só que um conta linhas de pedido e o "
        "outro soma a quantidade real de itens — compare os dois pra não se enganar com uma linha de "
        "quantidade grande dando a impressão de mais coisa devolvida do que realmente foi."
    )

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Por categoria (C/T/R) — por quantidade")
        cat = df.groupby("categoria")["quantidade_efetiva"].sum().reset_index()
        cat.columns = ["categoria", "quantidade"]
        fig = px.bar(cat, x="categoria", y="quantidade", color_discrete_sequence=[CATEGORICA[0]])
        fig.update_layout(xaxis_title="", yaxis_title="")
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.caption("Top unidades (destino) — por quantidade")
        destino = df.groupby("destino")["quantidade_efetiva"].sum().sort_values(ascending=False).head(8).reset_index()
        destino.columns = ["destino", "quantidade"]
        fig = px.bar(destino, x="quantidade", y="destino", orientation="h", color_discrete_sequence=[CATEGORICA[1]])
        fig.update_layout(
            xaxis_title="", yaxis_title="",
            yaxis={"categoryorder": "total ascending", "type": "category"},
        )
        layout_grafico(fig, altura=230)
        st.plotly_chart(fig, width="stretch")

    st.divider()
    st.markdown("##### Evolução mensal")
    col_emp, col_dev = st.columns(2)
    with col_emp:
        st.caption("Empréstimos por mês (data do pedido de envio) — por quantidade")
        _linha_mensal(df, "pedido_envio", AMBER)
    with col_dev:
        st.caption("Devoluções por mês (data de devolução) — por quantidade")
        _linha_mensal(df, "data_devolucao", STATUS["good"])

    st.divider()
    st.markdown("##### Todos os itens")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
    with c1:
        status_f = st.selectbox("Status", ["Todos", "Pendente", "OK"], key="emp_f_status")
    with c2:
        categorias_f = st.multiselect("Categoria", ordenar_unicos(df["categoria"]), key="emp_f_categoria")
    with c3:
        destinos_f = st.multiselect("Destino", ordenar_unicos(df["destino"]), key="emp_f_destino")
    with c4:
        busca = st.text_input("🔎 Busca (PN, descrição, aeronave)", key="emp_f_busca")

    filtrado = df.copy()
    if status_f != "Todos":
        filtrado = filtrado[filtrado["status"] == status_f]
    if categorias_f:
        filtrado = filtrado[filtrado["categoria"].isin(categorias_f)]
    if destinos_f:
        filtrado = filtrado[filtrado["destino"].isin(destinos_f)]
    if busca:
        b = busca.strip().lower()
        filtrado = filtrado[
            filtrado["part_number"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["descricao"].astype(str).str.lower().str.contains(b, na=False)
            | filtrado["anv"].astype(str).str.lower().str.contains(b, na=False)
        ]

    colunas_tabela = [
        "numero_ordem", "part_number", "descricao", "categoria", "quantidade_texto",
        "pedido_emg", "motivo", "pedido_envio", "anv", "destino", "numero_rc",
        "nf_devolucao_vee_one", "data_devolucao", "observacao_fiscal", "observacao_empresa", "status",
    ]
    nomes_colunas = {
        "numero_ordem": "Nº Ordem", "part_number": "Part Number", "descricao": "Descrição",
        "categoria": "CAT", "quantidade_texto": "QTD", "pedido_emg": "Pedido/EMG",
        "motivo": "Motivo", "pedido_envio": "Pedido de envio", "anv": "ANV", "destino": "Destino",
        "numero_rc": "Nº RC", "nf_devolucao_vee_one": "NF devolução VEE ONE",
        "data_devolucao": "Data devolução", "observacao_fiscal": "Observação Fiscal",
        "observacao_empresa": "Observação Empresa", "status": "Status",
    }
    tabela = filtrado[colunas_tabela].rename(columns=nomes_colunas)
    st.caption(f"{len(tabela)} de {total} itens")
    st.dataframe(tabela, hide_index=True, width="stretch", height=460)

    csv = tabela.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar (CSV)", csv, file_name="emprestimos.csv", mime="text/csv")
