"""Tela de detalhe — Reparáveis.

**Reorganizada em 2026-08-24** (pedido do Wallace: "vamos melhorar o
controle de reparaveis, as informacoes deles, o layort, as cores os
filtros"). Antes era uma coluna única gigante (cards + 3 gráficos +
filtros + tabela de ~400 linhas + mais 2 seções embaixo) — virou 3 abas
("📊 Visão Geral", "📋 Tabela / Consulta", "📅 Histórico"), pra quem só quer
consultar uma OS não precisar rolar por tudo. Mudanças principais:

- Cores condicionais (antes tudo era âmbar, até números ruins como "fora
  do prazo"): cards e barras do gráfico "TAT médio por local" agora usam
  STATUS["critical"]/STATUS["good"] conforme o prazo contratual.
- Gráfico "TAT médio por local" ficou clicável (pedido: "quero que tudo
  seja clicavel nessa parte") — clicar numa barra já filtra a aba
  "Tabela / Consulta" por aquele local (via `st.session_state`, ver
  `_secao_tabela`).
- Ranking das 10 OS mais atrasadas (não existia — só tinha a média por
  local, não um raio-x das piores individualmente).
- Coluna "Dias até vencer o prazo" na tabela (110 − TAT, só pra quem ainda
  tá com a empresa/terceirizados).
- Busca por texto livre (nomenclatura/PN/SN/OS) + atalho "só fora do
  prazo" — antes só dava pra filtrar por valor exato via multiselect.
- Botão de exportar (XLSX) a tabela já filtrada — não existia.
- Linha da tabela pintada quando fora do prazo/condenado.
- Corrigido bug mudo (mesmo already achado no Cômputo Mensal, 2026-08-20):
  célula vazia aparecia como o texto literal "None" em vez de branco.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from shared import horario
from contrato005.components import data_global
from contrato005.components.paleta import AMBER, INK, LINE, PANEL, SECONDARY, STATUS, layout_grafico, metrica_html, titulo_bloco
from contrato005.components.utils import ordenar_unicos
from contrato005.components.exportar import gerar_xlsx_bytes

SCRIPTS_PYTHON = Path(__file__).resolve().parents[3] / "05_Scripts" / "python"
if str(SCRIPTS_PYTHON) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PYTHON))

# "Onde se encontra" que significa que o item JÁ foi entregue pelo
# fornecedor (VEE ONE) pra unidade/base — só falta encerrar a burocracia da
# OS, não é mais um atraso de reparo de verdade. Pedido do Wallace em
# 2026-07-18: "quando tiver com os eles ou com terceirizados, quando tiver
# escrito: BABE, BAMN,BABV,BAPV,BABR,BANT,PAMALS,BACO,BASM,BACG EEAR
# SIGNIFICA QUE ELE ja entregou SO ATE ABERTO A BUROCRACIA". "PAMA-LS" é o
# nome real na fonte (o que o Wallace escreveu como "PAMALS"). **"V1
# PAMA-LS" NÃO entra aqui** — é um valor diferente (ainda com o
# fornecedor), confirmado pelo Wallace: "obs: v1 pamals esta com eles
# ainda" — por isso o match é por igualdade exata, não por "contém".
LOCAIS_ENTREGUES = {
    "BABE", "BAMN", "BABV", "BAPV", "BABR", "BANT", "PAMA-LS", "BACO", "BASM", "BACG", "EEAR",
}

# Prazo contratual de TAT (Turn Around Time) — confirmado pelo Wallace em 2026-07-18.
PRAZO_CONTRATUAL_TAT_DIAS = 110

# Cobrança do prazo contratual só vale a partir de 01/07/2026 (pedido do
# Wallace, 2026-08-24: "eu estou cobrando TAT a partir de 01/07.2026 a
# partir da data de inicio, como podemos organizar isso" — depois,
# confirmando a regra: "vamos computar mas sem cobrar, ela nao ta
# errada"). Ou seja: **toda** OS continua tendo o TAT calculado e exibido
# normalmente (nada some da tabela/médias gerais) — só as métricas que
# representam "cobrança"/violação de prazo (fora do prazo, vence este
# mês, ranking de atrasadas, filtro "só fora do prazo", coluna "dias até
# vencer") passam a considerar só OS cuja "Data Início" seja em
# 01/07/2026 ou depois. OS mais antigas não entram nessas contas — não
# porque o TAT dela é "zero", mas porque a cobrança formal desse prazo só
# começou nessa data (a empresa não está errada pelo período anterior).
INICIO_COBRANCA_PRAZO = date(2026, 7, 1)

# "Onde se encontra" vazio não é "sem dado" — pedido do Wallace em
# 2026-07-18: "quando tiver vazio, a empresa ainda nao passou, esta em
# processo interno da empresa ou nao foi informado por ela". Preenchido
# logo na entrada de render() (não só na exibição) pra entrar certo em
# TODO lugar que usa essa coluna — filtro, tabela e "Estatísticas de TAT"
# (sem isso, o `groupby` do gráfico "TAT médio por local" descartava essas
# linhas por padrão, já que pandas ignora grupos NaN).
LOCAL_NAO_INFORMADO = "Em processo interno / não informado pela empresa"

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _mesclar_complemento_rma(df, complemento):
    """Mescla "Data de devolução empresa"/"Onde se encontra"/"Recibo" vindos
    da RMA em andamento do mês por cima da planilha geral, só pras OS que a
    RMA já confirma como devolvidas — pedido do Wallace, 2026-08-12: a
    burocracia da OS pode continuar aberta na planilha geral por um tempo
    mesmo depois da empresa já ter devolvido de verdade (ver RMA, aba 1.8 +
    1.10). Nunca inventa: só sobrescreve os 3 campos quando a RMA de fato
    trouxe um valor pra aquela OS; `situacao`/`em_aberto` continuam vindo só
    da planilha geral (não foi pedido mexer nisso). Cria a coluna `fonte`
    (ex.: "RMA Julho/2026") — vazia pra OS sem complemento, indicando que a
    informação é só da planilha geral mesmo.

    **TAT real calculado (2026-08-12)** — Wallace: "a empresa tem mais OS
    né, acho que ela computou desde o início [...] vamos pegar o que tá com
    OS concluída na nossa planilha e buscar os dados de entrega na deles,
    para irmos criando o TAT real se tiver data de entrega [...] ou
    completar com o que tiver". A 1.10 da RMA cobre bem mais OS do que a
    planilha geral já tem `tat_empresa` preenchido (o "TAT" que a própria
    empresa relata lá) — quando falta `tat_empresa` mas a gente tem
    `data_inicio` (planilha geral) e a data de devolução (RMA), calcula
    `tat_empresa = (data_devolução − data_início).dias` — não é inventar
    dado, é derivar de 2 datas reais. `tat_calculado=True` marca as linhas
    onde isso aconteceu (a "Fonte" ganha o sufixo "— TAT calculado")."""
    df = df.copy()
    df["fonte"] = ""
    df["tat_calculado"] = False
    if complemento is None or complemento.empty:
        return df

    # `data_entrega` é datetime64 na base tratada — pode receber tanto uma
    # data real (data_devolucao_empresa) quanto texto ambíguo não-parseável
    # (data_devolucao_empresa_texto, ex.: "14/5/2025 E 25/07/2025"), então
    # precisa virar coluna de objeto antes de misturar os dois tipos.
    df["data_entrega"] = df["data_entrega"].astype(object)

    mais_recente = (
        complemento.sort_values(["ano_referencia", "mes_referencia"])
        .drop_duplicates("os", keep="last")
        .set_index("os")
    )
    df["os"] = df["os"].astype(str)
    for numero_os, linha in mais_recente.iterrows():
        idx = df.index[df["os"] == numero_os]
        if idx.empty:
            continue
        if linha["onde_se_encontra"]:
            df.loc[idx, "onde_se_encontra"] = linha["onde_se_encontra"]
        if linha["recibo"]:
            df.loc[idx, "recibo"] = linha["recibo"]
        if pd.notna(linha["data_devolucao_empresa"]):
            df.loc[idx, "data_entrega"] = linha["data_devolucao_empresa"]
        elif linha["data_devolucao_empresa_texto"]:
            df.loc[idx, "data_entrega"] = linha["data_devolucao_empresa_texto"]
        # Condenado (aba 1.9 da RMA) — sobrescreve "Condição" mesmo que a
        # planilha geral ainda mostre "EM REPARO" (burocracia em aberto),
        # com o motivo de condenação junto.
        if bool(linha.get("condenado", False)):
            motivo = linha.get("motivo_condenacao")
            df.loc[idx, "condicao"] = f"CONDENADO — {motivo}" if motivo else "CONDENADO"

        fonte = linha["fonte"]
        # TAT real calculado — só quando falta tat_empresa E temos as 2
        # datas reais (data_inicio da planilha geral + devolução da RMA).
        tat_atual = df.loc[idx, "tat_empresa"]
        data_inicio = df.loc[idx, "data_inicio"]
        if tat_atual.isna().all() and pd.notna(linha["data_devolucao_empresa"]) and data_inicio.notna().all():
            dias = (pd.Timestamp(linha["data_devolucao_empresa"]) - data_inicio).dt.days
            df.loc[idx, "tat_empresa"] = dias
            df.loc[idx, "tat_calculado"] = True
            fonte = f"{fonte} — TAT calculado" if fonte else "TAT calculado (RMA)"
        df.loc[idx, "fonte"] = fonte

    # "Origem do registro" — marca quem confirmou cada linha, pedido do
    # Wallace 2026-08-24 (num campo à parte da coluna "Fonte" já existente,
    # que é mais um texto livre de proveniência do TAT): "aí um campo onde
    # conseguimos ver se a empresa informou". Toda OS que bateu com a
    # planilha da empresa nesse laço vira "confirmada pelas duas fontes";
    # o resto (abaixo) fica "só SILOMS" — ver `os_recuperadas_rma` pras que
    # são só da empresa.
    df["origem_registro"] = "SILOMS"
    os_com_complemento = set(mais_recente.index) & set(df["os"])
    df.loc[df["os"].isin(os_com_complemento), "origem_registro"] = "✅ SILOMS + confirmada pela empresa"

    # OS recuperadas (2026-08-24) — pedido do Wallace: "eu vou continuar
    # atualizando e baixando as OS do SILOMS, pega so as abertas, quando
    # fecha a gente sabe que fechou pq ela sai de la e fica no historico da
    # planilha controle dos reparaveis, mas como nao tinha controle antes
    # algumas OS ficaram para tras, cruza os dados e oq tiver faltando usa
    # os dados da empresa, para fins de OS totais" + confirmado depois:
    # "tudo vai ta com a empresa se estiver mesmo, ai c ela informou a
    # gente clica, todo mes vamos ler as planilhas de RMA, vai ser assim
    # agora". A aba 1.10 da RMA é o controle acumulado da EMPRESA (não só
    # do mês) — toda OS que está lá mas nunca apareceu na nossa planilha
    # geral (SILOMS "Divulgação") fechou antes de existirmos controle
    # próprio e ficou pra trás. Entram como linha nova, marcadas como já
    # ENTREGUES (a RMA só registra uma OS com data/recibo/destino quando a
    # empresa já devolveu de verdade) — decisão do Wallace: "somar só no
    # total geral" (não inventa TAT sem "Data Início", que essa planilha
    # não tem).
    ja_temos = set(df["os"])
    recuperar = mais_recente[~mais_recente.index.isin(ja_temos)]
    linhas_novas = []
    for numero_os, linha in recuperar.iterrows():
        condicao = None
        if bool(linha.get("condenado", False)):
            motivo = linha.get("motivo_condenacao")
            condicao = f"CONDENADO — {motivo}" if motivo else "CONDENADO"
        data_entrega = (
            linha["data_devolucao_empresa"] if pd.notna(linha["data_devolucao_empresa"])
            else (linha["data_devolucao_empresa_texto"] or None)
        )
        linhas_novas.append({
            "os": numero_os, "pn": linha.get("pn"), "cff": None,
            "nomenclatura": linha.get("nomenclatura"), "sn": linha.get("sn"),
            "data_inicio": pd.NaT, "unidade_solicitante": None, "situacao": None,
            "tat_siloms": float("nan"), "tat_empresa": float("nan"),
            "onde_se_encontra": linha["onde_se_encontra"] or LOCAL_NAO_INFORMADO,
            "recibo": linha["recibo"], "condicao": condicao, "data_entrega": data_entrega,
            "sn_trocado_exchange": None, "termo_recebimento": None, "em_aberto": False,
            "fonte": f"{linha['fonte']} — recuperada (não estava na planilha SILOMS)",
            "tat_calculado": False,
            "origem_registro": "🆕 Só na empresa (recuperada da RMA)",
        })
    if linhas_novas:
        df = pd.concat([df, pd.DataFrame(linhas_novas)], ignore_index=True)
    return df


def _secao_complemento_rma():
    """Botão pra repetir, em qualquer mês futuro, o cruzamento que o Wallace
    pediu manualmente em 2026-08-12 pra julho — sem precisar pedir de novo
    na conversa. Ver `extrair_reparaveis_rma.py`."""
    with st.expander("🔄 Complementar com a RMA em andamento do mês"):
        st.caption(
            "Busca no Drive a \"RMA em andamento\" (ou \"Pré RMA\") do mês escolhido e complementa \"ONDE SE "
            "ENCONTRA\"/\"Data de devolução empresa\"/\"RECIBO CASO TENHA\"/\"Condição\" na tabela acima, "
            "pras OS que a burocracia da planilha geral ainda não fechou — cruzando a aba 1.10 (todo o "
            "controle de OS, marcando quais a 1.8 confirma como entregues NESTE mês) e a 1.9 (condenados)."
        )
        hoje = horario.hoje_br()
        col_ano, col_mes, col_botao = st.columns([1, 2, 2])
        with col_ano:
            ano = st.number_input("Ano", min_value=2025, max_value=2035, value=hoje.year, step=1, key="rep_rma_ano")
        with col_mes:
            mes = st.selectbox(
                "Mês", options=list(range(1, 13)), index=hoje.month - 1,
                format_func=lambda m: MESES_PT[m - 1], key="rep_rma_mes",
            )
        with col_botao:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("Buscar e complementar", key="rep_rma_buscar", width="stretch"):
                with st.spinner("Buscando a RMA do mês no Drive..."):
                    try:
                        from shared import drive_sync
                        drive_sync.garantir_credencial_arquivo()
                        import extrair_reparaveis_rma
                        resultado = extrair_reparaveis_rma.atualizar_do_mes(int(ano), int(mes))
                        st.success(
                            f"Complementado a partir de \"{resultado['arquivo']}\": "
                            f"{resultado['os_complementadas_no_mes']} OS com dado (1.10 + 1.9) "
                            f"({resultado['os_entregues_no_mes']} entregues neste mês [aba 1.8] + "
                            f"{resultado['os_historico']} histórico de meses anteriores, "
                            f"{resultado['os_condenadas']} condenadas [aba 1.9]; "
                            f"{resultado['total_acumulado']} acumuladas no total, "
                            f"{resultado['inconsistencias']} inconsistência(s) — ver log em 06_Logs/)."
                        )
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Falha ao buscar/complementar: {e}")


def _dados_historico_mensal(df):
    """Contagem de OS abertas (Data Início) por mês — pedido do Wallace,
    2026-08-03: "coloca uma coluna tb do historico por mes de numero de
    aberturas". Usa TODAS as OS (abertas e concluídas, não só as em
    aberto hoje) — "abertura" é sobre quando a OS entrou, não sobre a
    situação atual dela. Extraído em 2026-08-24 (era só dentro de
    `_secao_historico_mensal`) pra ser reaproveitado também no painel
    compacto da Visão Geral — mesmo cálculo, sem duplicar regra nenhuma."""
    hist = df.copy()
    hist["mes"] = hist["data_inicio"].dt.to_period("M")
    contagem = hist.groupby("mes").size().reset_index(name="Aberturas").sort_values("mes")
    contagem["Mês"] = contagem["mes"].apply(lambda p: f"{MESES_PT[p.month - 1]}/{p.year}")
    return contagem


def _figura_historico_mensal(contagem, altura=320):
    # Laranja continua (identidade do sistema) — só um pouco mais de
    # respiro entre as barras/rótulos (pedido do Wallace no brief de
    # refinamento: "manter as barras laranjas... melhorar largura das
    # barras, espaçamento, rótulos, eixo X"). O mês de pico se destaca
    # sozinho por ser o maior valor, sem precisar mudar a cor dele.
    #
    # 2026-08-24, 3ª rodada ("aumentar espessura das barras/valores/
    # rótulos... reduzir a inclinação exagerada dos meses"): `bargap`
    # menor = barra mais grossa (0.3 → 0.2), texto maior (11 → 13),
    # rótulo do mês com inclinação mais suave (`tickangle`, Plotly deixava
    # rodar quase 90° sozinho por padrão quando não cabia — fixado em -35°,
    # "mais horizontal ou levemente inclinado").
    fig = px.bar(contagem, x="Mês", y="Aberturas", color_discrete_sequence=[AMBER])
    fig.update_traces(text=contagem["Aberturas"], textposition="outside", textfont_size=13)
    fig.update_layout(xaxis_title="", yaxis_title="Nº de aberturas", showlegend=False, bargap=0.2)
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=11))
    layout_grafico(fig, altura=altura)
    return fig


def _secao_historico_mensal(df):
    st.markdown("##### Histórico mensal — número de aberturas")
    st.caption("Quantidade de OS abertas (Data Início) por mês, independente da situação atual (em aberto ou já concluída).")
    contagem = _dados_historico_mensal(df)
    st.plotly_chart(_figura_historico_mensal(contagem), width="stretch", key="rep_hist_mensal_completo")
    st.dataframe(contagem[["Mês", "Aberturas"]], hide_index=True, width="stretch")


def _linha_kpis_html(grupos):
    """Uma única faixa horizontal de KPIs agrupados (Volume/Prazo/TAT/
    Entregues), com divisórias verticais discretas entre grupos — pedido
    do Wallace, 2026-08-24, a partir de uma imagem de referência de
    layout: "criar uma linha visual... separar os grupos com linhas
    verticais ou espaçamento sutil... não criar cards enormes". Substitui
    os blocos empilhados (titulo_bloco + st.columns, um bloco embaixo do
    outro) por uma faixa só, mais densa — mesmos números/cálculos de
    sempre, só a apresentação muda. `grupos`: lista de (titulo_do_grupo,
    [(label, valor, cor_ou_None, icone_ou_None), ...])."""
    # 2026-08-24 (ajuste após ver no site publicado): label sem quebra
    # (`white-space:nowrap`) forçava cada grupo a ficar bem mais largo do
    # que cabia, mesmo em tela grande — o grupo "Entregues" (4º) acabava
    # "sobrando" e quebrando pra uma linha nova sozinho, longe dos outros
    # 3. Trocado por `max-width` com quebra de linha normal — cada
    # métrica ocupa uma largura previsível (~8.5rem), o rótulo quebra
    # embaixo se precisar, a linha toda fica mais compacta e previsível.
    # 2026-08-24, 3ª rodada de ajuste ("melhorar os KPIs... aumentar
    # numeros/espacamento interno/separacao entre grupos, diminuir
    # textos secundarios"): valor principal maior (1.55rem → 1.85rem),
    # rótulo secundário menor (.66rem → .62rem), mais respiro entre
    # grupos (1.5rem → 1.9rem de padding). Continua branco/INK por
    # padrão — só Prazo usa STATUS["good"/"critical"], nunca AMBER como
    # cor de status.
    # 2026-08-24, 5ª rodada ("dificil de entender ne kkkk" — rótulo
    # quebrando NO MEIO da palavra, ex.: "TERCE"/"IRIZADOS"): `max-width`
    # curto de mais forçava isso. Trocado por `min-width` (não limita o
    # rótulo, só garante uma largura mínima previsível) +
    # `word-break:normal`/`overflow-wrap:normal` explícitos (só quebra
    # em espaço, nunca no meio da palavra) — combinado com rótulos mais
    # curtos (ver `_secao_estatisticas_tat`), a maioria fica numa linha
    # só agora.
    blocos = []
    for i, (titulo_grupo, itens) in enumerate(grupos):
        campos = "".join(
            f'<div style="margin-right:1.2rem;min-width:6.5rem;max-width:11rem;">'
            f'<div style="font-size:.62rem;color:{SECONDARY};text-transform:uppercase;'
            f'letter-spacing:.05em;margin-bottom:.25rem;line-height:1.25;white-space:nowrap;'
            f'word-break:normal;overflow-wrap:normal;">{label}</div>'
            f'<div style="font-size:1.85rem;font-weight:700;color:{cor or INK};line-height:1.15;'
            f'white-space:nowrap;">{(icone + " ") if icone else ""}{valor}</div>'
            f'</div>'
            for label, valor, cor, icone in itens
        )
        borda = f"border-right:1px solid {LINE};" if i < len(grupos) - 1 else ""
        blocos.append(
            f'<div style="display:flex;flex-direction:column;padding:0 1.4rem;{borda}'
            f'{" padding-left:0;" if i == 0 else ""}">'
            f'<div style="font-size:.65rem;color:{AMBER};text-transform:uppercase;'
            f'letter-spacing:.08em;font-weight:600;margin-bottom:.6rem;">{titulo_grupo}</div>'
            f'<div style="display:flex;flex-wrap:wrap;">{campos}</div>'
            f'</div>'
        )
    return f'<div style="display:flex;flex-wrap:wrap;align-items:flex-start;padding:.4rem 0 .6rem 0;">{"".join(blocos)}</div>'


def _fluxo_conexoes_html(total, abertas, fechadas, com_empresa, entregue):
    """"Como os números se conectam" — refeito em 2026-08-24 a partir de
    uma imagem de referência de layout do Wallace (fluxo horizontal de
    caixas ligadas por setas, no lugar da árvore clicável `<details>`
    montada mais cedo no mesmo dia — "gostei desse esquema... indo
    clicando e espandindo" foi a versão anterior; agora o pedido explícito
    é aproximar do layout da imagem). Sempre calculado sobre TODAS as OS
    (recebe `df` inteiro do chamador, não `escopo_df`) — o objetivo é
    explicar como o universo INTEIRO se conecta, não só o recorte do
    radio "Abertas no SILOMS/Fechadas/Todas" escolhido acima na tela."""
    # 2026-08-24, 3ª rodada ("melhorar alinhamento/largura/altura/
    # espaçamento/setas/bordas/tamanho dos números... cards mais
    # homogêneos"): caixa maior e com altura mínima igual pra todas
    # (`min-height`, antes cada uma tinha a altura que o conteúdo dela
    # pedisse — a com `sub` ficava mais alta que "OS totais"/"OS
    # fechadas", que não têm). Cores continuam as mesmas de sempre:
    # laranja só em "com empresa" (identidade), verde só em "entregue"
    # (positivo), branco/cinza (LINE, sem cor especial) pros totais/
    # fechadas — nenhuma regra de cor mudou, só o tamanho.
    def _caixa(icone, valor, label, sub=None, cor=None):
        sub_html = f'<div style="font-size:.72rem;color:{SECONDARY};margin-top:.25rem;">{sub}</div>' if sub else ""
        return (
            f'<div style="background:{PANEL};border:1px solid {cor or LINE};border-radius:10px;'
            f'padding:1.1rem 1.4rem;min-width:10.5rem;min-height:7.2rem;display:flex;'
            f'flex-direction:column;justify-content:center;gap:.2rem;">'
            f'<div style="font-size:1.4rem;">{icone}</div>'
            f'<div style="font-size:1.9rem;font-weight:700;color:{INK};line-height:1.1;">{valor}</div>'
            f'<div style="font-size:.76rem;color:{SECONDARY};">{label}</div>'
            f'{sub_html}'
            f'</div>'
        )

    seta = f'<div style="align-self:center;color:{SECONDARY};font-size:1.6rem;padding:0 .35rem;">→</div>'
    pct_abertas = f"{abertas / total * 100:.1f}%" if total else "—"
    pct_fechadas = f"{fechadas / total * 100:.1f}%" if total else "—"
    pct_empresa = f"{com_empresa / abertas * 100:.1f}% das abertas" if abertas else "—"
    pct_entregue = f"{entregue / abertas * 100:.1f}% das abertas" if abertas else "—"

    partes = [
        _caixa("📦", total, "OS totais"),
        seta,
        _caixa("📂", abertas, "OS abertas no SILOMS", pct_abertas),
        seta,
        _caixa("🟠", com_empresa, "Com a empresa e terceirizados", pct_empresa, cor=AMBER),
        seta,
        _caixa("🟢", entregue, "Entregue — falta só fechar no SILOMS", pct_entregue, cor=STATUS["good"]),
        f'<div style="align-self:center;border-left:1px dashed {LINE};height:3rem;margin:0 .8rem;"></div>',
        _caixa("🗂️", fechadas, "OS fechadas", pct_fechadas),
        f'<div style="align-self:center;background:{PANEL};border:1px solid {LINE};border-radius:10px;'
        f'padding:.8rem 1.1rem;font-size:.74rem;color:{SECONDARY};max-width:13.5rem;min-height:7.2rem;'
        f'display:flex;align-items:center;">ℹ️ Percentuais calculados sobre o total de OS abertas (exceto '
        f'"OS totais"/"OS fechadas", que são sobre o total geral).</div>',
    ]
    return f'<div style="display:flex;flex-wrap:wrap;align-items:stretch;gap:.7rem;padding:.5rem 0;">{"".join(partes)}</div>'


def _secao_estatisticas_tat(df):
    st.markdown("##### Estatísticas de TAT")

    # Filtro de escopo (pedido do Wallace, 2026-08-12: "coloca as OS
    # fechadas lá tb e todas, dar por filtrar OS aberta no SILOMS e OS já
    # fechada e todas, aí as estatística giram em todos de conforme eu
    # selecionar e geral") — antes essa seção só olhava OS em aberto; agora
    # todas as contas abaixo recalculam de acordo com a escolha.
    # Radio + selos na mesma linha (não mais empilhados) — pedido do
    # Wallace, 2026-08-24, a partir de imagem de referência de layout:
    # "topo... manter... seleção... indicador laranja... indicador verde"
    # lado a lado, não um embaixo do outro.
    col_escopo, col_selos = st.columns([2, 3])
    with col_escopo:
        escopo = st.radio(
            "OS consideradas nas estatísticas abaixo",
            ["Abertas no SILOMS", "Fechadas", "Todas"],
            horizontal=True, key="rep_tat_escopo",
        )
    if escopo == "Abertas no SILOMS":
        escopo_df = df[df["em_aberto"]].copy()
    elif escopo == "Fechadas":
        escopo_df = df[~df["em_aberto"]].copy()
    else:
        escopo_df = df.copy()

    if escopo_df.empty:
        st.info(f"Nenhuma OS em \"{escopo}\".")
        return

    # Legenda visual (selos coloridos), não só texto — pedido do Wallace,
    # 2026-08-24: "queria que deixasse mais claro" (a distinção "com
    # empresa" x "entregue, falta burocracia" só em texto corrido não
    # ficava óbvia). As mesmas 2 cores aparecem nos cards de "Prazo" acima,
    # nos donuts e nas barras abaixo — esse selo é a "legenda mestra" delas.
    with col_selos:
        st.markdown("<div style='height:1.7rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="text-align:right;">'
            f'<span style="background:{AMBER}22;color:{AMBER};border:1px solid {AMBER}55;'
            f'border-radius:4px;padding:.15rem .5rem;font-size:.78rem;font-weight:600;">'
            f'🟠 Com a empresa e terceirizados — ainda não voltou</span>'
            f'&nbsp;&nbsp;'
            f'<span style="background:{STATUS["good"]}22;color:{STATUS["good"]};border:1px solid {STATUS["good"]}55;'
            f'border-radius:4px;padding:.15rem .5rem;font-size:.78rem;font-weight:600;">'
            f'🟢 Entregue — já voltou, falta só fechar a OS no SILOMS</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with st.expander("ℹ️ Entenda os critérios dos indicadores"):
        st.markdown(
            "**Com a empresa e terceirizados x Entregue (falta burocracia)** — quando \"Onde se "
            "encontra\" é BABE/BAMN/BABV/BAPV/BABR/BANT/PAMA-LS/BACO/BASM/BACG/EEAR, o item já foi "
            "entregue pelo fornecedor — só falta encerrar a burocracia da OS no SILOMS, não é mais "
            "atraso de reparo de verdade. **\"V1 PAMA-LS\" não conta como entregue** (é outra etapa, "
            f"ainda com a empresa). Vazio = \"{LOCAL_NAO_INFORMADO}\".\n\n"
            f"**Prazo contratual** — {PRAZO_CONTRATUAL_TAT_DIAS} dias, só conta pra quem ainda está "
            "\"com a empresa e terceirizados\" (item já entregue não pesa mais contra o prazo, mesmo "
            "que o TAT dele já passe disso). **E só pra OS abertas a partir de "
            f"{INICIO_COBRANCA_PRAZO.strftime('%d/%m/%Y')}** — a cobrança formal desse prazo começou "
            "nessa data; uma OS mais antiga continua tendo o TAT calculado e exibido normalmente, só "
            "não entra nas contas de \"fora do prazo\"/\"vence este mês\"/ranking de atrasadas (a "
            "empresa não está errada pelo período anterior a essa data).\n\n"
            "**TAT real da empresa** — coluna reportada pela própria VEE ONE (só existe depois que o "
            "item já foi entregue); quando falta esse dado na planilha geral mas temos a data de "
            "devolução pela RMA em andamento, calculamos nós (devolução − início) — marcado como "
            "\"TAT calculado\" na coluna \"Fonte\" da tabela."
        )

    # Bug achado pelo Wallace, 2026-08-24 ("essa situacao ai, c ta fechada
    # ja ta em algum lugar ne, n ta com a empresa"): "onde_se_encontra" só
    # é confiável pra item AINDA EM ABERTO — pra OS já fechada (concluída
    # no SILOMS, ou recuperada via RMA sem esse campo preenchido), esse
    # valor pode estar vazio/desatualizado (ex.: colunas internas "CLA"/
    # "LEAP"/"VEE ONE" que o Wallace avisou que tendem a parar de ser
    # atualizadas) sem que isso signifique que o item "ainda não voltou"
    # — a OS já foi resolvida, só o campo de localização ficou pra trás.
    # Toda OS fechada entra em "Entregue" de propósito, não importa o que
    # tiver em "onde_se_encontra" — por definição ela não pode estar
    # "com a empresa e terceirizados — ainda não voltou" (rótulo da
    # legenda) se já está fechada. Achado real: 86 das 276 OS fechadas
    # (escopo "Fechadas") caíam erradas em "com a empresa" antes desse
    # ajuste, a maioria (77) só por "onde_se_encontra" vazio.
    escopo_df["grupo"] = (
        escopo_df["onde_se_encontra"].isin(LOCAIS_ENTREGUES) | ~escopo_df["em_aberto"]
    ).map({True: "Entregue (falta burocracia)", False: "Com a empresa e terceirizados"})
    empresa = escopo_df[escopo_df["grupo"] == "Com a empresa e terceirizados"]

    def _media_tat(sub):
        return f"{sub['tat_siloms'].mean():.0f} dias" if sub["tat_siloms"].notna().any() else "—"

    # Prazo contratual (dentro/fora, vence este mês) só faz sentido pra quem
    # ainda está com a empresa/terceirizados — item já entregue (só falta
    # burocracia) não conta mais contra o prazo. Pedido do Wallace em
    # 2026-07-18: "o prazo dentro e fora do prazo so os que estao com a
    # empresa".
    #
    # Cobrança do prazo só entra em vigor a partir de 01/07/2026 (ver
    # INICIO_COBRANCA_PRAZO) — pedido do Wallace, 2026-08-24: "vamos
    # computar mas sem cobrar, ela nao ta errada". OS com "Data Início"
    # sem data (NaT) também não entram na cobrança (não dá pra confirmar
    # que é elegível, então não cobra — mesma lógica de "não inventar
    # dado"). O TAT em si (médias, tabela) continua vindo de `empresa`
    # inteira, sem esse corte — só a contagem de violação de prazo usa
    # `empresa_cobravel`.
    empresa_cobravel = empresa[
        pd.to_datetime(empresa["data_inicio"], errors="coerce") >= pd.Timestamp(INICIO_COBRANCA_PRAZO)
    ]

    hoje = pd.Timestamp(horario.hoje_br())
    fora_prazo = empresa_cobravel[empresa_cobravel["tat_siloms"] > PRAZO_CONTRATUAL_TAT_DIAS]
    dentro_prazo = empresa_cobravel[empresa_cobravel["tat_siloms"] <= PRAZO_CONTRATUAL_TAT_DIAS]

    com_data = empresa_cobravel.dropna(subset=["data_inicio"]).copy()
    com_data["data_limite"] = pd.to_datetime(com_data["data_inicio"]) + pd.Timedelta(days=PRAZO_CONTRATUAL_TAT_DIAS)
    vence_mes = com_data[
        (com_data["data_limite"].dt.year == hoje.year)
        & (com_data["data_limite"].dt.month == hoje.month)
        & (com_data["tat_siloms"] <= PRAZO_CONTRATUAL_TAT_DIAS)
    ]

    com_tat_empresa = escopo_df[escopo_df["tat_empresa"].notna()]
    calculados = int(com_tat_empresa["tat_calculado"].sum()) if not com_tat_empresa.empty else 0

    # Faixa única de KPIs (Volume/Prazo/TAT/Entregues) — pedido do Wallace,
    # 2026-08-24, primeiro em texto ("permitir que alguém olhe o dashboard
    # por poucos segundos e entenda...") e depois via imagem de referência
    # de layout ("criar uma linha visual... separar os grupos com linhas
    # verticais... não criar cards enormes"). Substituiu os blocos
    # empilhados (um `titulo_bloco` embaixo do outro) por uma faixa só —
    # mesmos números, cálculos e cores de sempre, só a apresentação mudou.
    # Rótulos encurtados — pedido do Wallace, 2026-08-24, 5ª rodada
    # ("dificil de entender ne kkkk", vendo os rótulos quebrando NO MEIO
    # da palavra, ex.: "TERCE"/"IRIZADOS" cortado). O texto completo
    # continua disponível no expander "Entenda os critérios dos
    # indicadores" logo acima — aqui só o essencial pra escanear rápido.
    recuperadas_no_escopo = int((escopo_df["origem_registro"] == "🆕 Só na empresa (recuperada da RMA)").sum())
    grupos_kpi = [
        ("Volume", [
            (f"OS — {escopo}", len(escopo_df), None, "📄"),
            ("Com a empresa", len(empresa), None, "👤"),
        ]),
        ("Prazo contratual", [
            (
                f"Fora do prazo (>{PRAZO_CONTRATUAL_TAT_DIAS}d)", len(fora_prazo),
                STATUS["critical"] if len(fora_prazo) else STATUS["good"], "🕐",
            ),
            (
                "Vencem este mês", len(vence_mes),
                STATUS["critical"] if len(vence_mes) else STATUS["good"], "📅",
            ),
        ]),
        ("TAT (dias)", [
            ("TAT médio geral", _media_tat(escopo_df), None, None),
            ("TAT médio — empresa", _media_tat(empresa), None, None),
        ] + ([("TAT real — empresa", f"{com_tat_empresa['tat_empresa'].mean():.0f} dias", None, None)]
             if not com_tat_empresa.empty else [])),
    ]
    if not com_tat_empresa.empty:
        grupos_kpi.append(("Entregues", [
            ("Itens c/ TAT real", len(com_tat_empresa), None, "📦"),
        ]))
    st.markdown(_linha_kpis_html(grupos_kpi), unsafe_allow_html=True)

    # Texto curto de 1 linha (era um parágrafo grande) + expander pro
    # resto — pedido do Wallace, 2026-08-24, 2ª rodada de layout: "a
    # frase longa abaixo dos KPIs ainda ocupa muito espaço horizontal...
    # transformar em uma frase curta... mover o restante para um
    # expander 'Entenda a regra contratual'... libera espaço pros
    # gráficos subirem". Mesmo conteúdo de sempre, só reorganizado —
    # nada foi removido, só escondido até alguém clicar.
    st.caption(
        f"⚖️ Regra contratual: prazo de {PRAZO_CONTRATUAL_TAT_DIAS} dias aplicável às OS abertas a "
        f"partir de {INICIO_COBRANCA_PRAZO.strftime('%d/%m/%Y')}."
    )
    detalhes_regra = [
        f"OS abertas antes de {INICIO_COBRANCA_PRAZO.strftime('%d/%m/%Y')} continuam com o TAT calculado "
        "e exibido normalmente (tabela, médias) — só não pesam como violação de prazo (fora do prazo/"
        "vence este mês/ranking/coluna \"dias até vencer\")."
    ]
    if recuperadas_no_escopo:
        detalhes_regra.append(
            f"🆕 {recuperadas_no_escopo} OS desse escopo não estavam na nossa planilha geral (fecharam antes "
            "de existir nosso controle) — recuperadas cruzando com a RMA da empresa."
        )
    if calculados:
        detalhes_regra.append(
            f"Dos {len(com_tat_empresa)} itens com TAT real, {calculados} foram calculados por nós "
            "(devolução da RMA − início), não reportados pela empresa — ver coluna \"Fonte\" na tabela."
        )
    with st.expander("Entenda a regra contratual"):
        for texto in detalhes_regra:
            st.caption(texto)

    # Donuts + TAT por local direto na tela (não mais dentro de expander)
    # — pedido do Wallace via imagem de referência: "reintroduzir dois
    # gráficos lado a lado... posição dos gráficos" logo abaixo dos KPIs.
    #
    # Ajuste 2026-08-24, 1ª rodada (depois de ver no site publicado,
    # feedback do Wallace: "tem muita coisa preta, os graficos maiores"):
    # cada gráfico ganhou `st.container(border=True)` (painel de verdade,
    # não "flutuando" no fundo escuro) — isso ficou. "TAT médio por
    # local" tinha ido pra linha própria, largura cheia — isso foi
    # **revertido na 2ª rodada** (ver comentário abaixo), o Wallace
    # achou que empilhar demais foi na direção errada.
    #
    # Ajuste 2026-08-24, 2ª rodada: "nao ficou bom, vc desceu, queria
    # tudo em uma pagina, mesmo arrendo para esquerda" — a linha própria
    # da rodada 1 tornou a página MAIS alta (rolagem vertical), o
    # oposto do que "mesmo que nao caiba tudo na pagina eu arredo com o
    # mouse para direita" pedia (prioridade é NÃO rolar pra baixo,
    # rolagem horizontal tudo bem). Os 3 gráficos voltam pra 1 linha só
    # — "TAT médio por local" com mais espaço relativo (1.6 dos 3.6
    # totais, contra 1 dos 2 donuts) pra caber os nomes de local mais
    # compridos sem cortar.
    # 2026-08-24, 3ª rodada ("aumentar bastante os donuts... 65-75% da
    # altura útil... TAT por local um dos principais gráficos"): altura
    # 260 → 320, furo 0.55 → 0.5 (donut mais "cheio"), texto/legenda
    # maiores. Proporção da linha ~28/28/44 (pedido do Wallace), aqui
    # como st.columns([28, 28, 44]).
    _ALTURA_DONUT = 320
    _LEGENDA_DONUT = dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5, font=dict(size=12))
    g1, g2, g3 = st.columns([28, 28, 44])
    with g1, st.container(border=True):
        st.caption("Com empresa x entregue")
        contagem_grupo = escopo_df["grupo"].value_counts().reset_index()
        contagem_grupo.columns = ["grupo", "quantidade"]
        fig_grupo = px.pie(
            contagem_grupo, names="grupo", values="quantidade", hole=0.5,
            color="grupo",
            color_discrete_map={"Com a empresa e terceirizados": AMBER, "Entregue (falta burocracia)": STATUS["good"]},
        )
        fig_grupo.update_traces(textinfo="value+percent", textfont_size=14)
        fig_grupo.update_layout(legend=_LEGENDA_DONUT)
        layout_grafico(fig_grupo, altura=_ALTURA_DONUT)
        fig_grupo.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_grupo, width="stretch", key="rep_donut_grupo")

    with g2, st.container(border=True):
        st.caption(f"Dentro x fora do prazo (> {PRAZO_CONTRATUAL_TAT_DIAS}d)")
        contagem_prazo = pd.DataFrame({
            "situacao": ["Dentro do prazo", "Fora do prazo"],
            "quantidade": [len(dentro_prazo), len(fora_prazo)],
        })
        fig_prazo = px.pie(
            contagem_prazo, names="situacao", values="quantidade", hole=0.5,
            color="situacao",
            color_discrete_map={"Dentro do prazo": STATUS["good"], "Fora do prazo": STATUS["critical"]},
        )
        fig_prazo.update_traces(textinfo="value+percent", textfont_size=14)
        fig_prazo.update_layout(legend=_LEGENDA_DONUT)
        layout_grafico(fig_prazo, altura=_ALTURA_DONUT)
        fig_prazo.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_prazo, width="stretch", key="rep_donut_prazo")

    with g3, st.container(border=True):
        st.caption("TAT médio por local — clique numa barra pra filtrar a Tabela/Consulta")
        media_local = (
            escopo_df.dropna(subset=["tat_siloms"])
            .groupby("onde_se_encontra")["tat_siloms"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(columns={"onde_se_encontra": "Onde se encontra", "mean": "TAT médio (dias)", "count": "Quantidade"})
            .sort_values("TAT médio (dias)", ascending=False)
        )
        if media_local.empty:
            # "tat_siloms" (TAT corrente do SILOMS) normalmente só existe pra OS
            # ainda em aberto — em "Fechadas" costuma vir tudo vazio, não é bug.
            st.caption("Sem \"TAT SILOMS\" preenchido nesse escopo — normal em \"Fechadas\".")
        else:
            media_local["TAT médio (dias)"] = media_local["TAT médio (dias)"].round(0).astype(int)
            # Cor condicional por barra — pedido do Wallace: "tem um negocio de
            # cor la de onde ta, ta um laranjao" (antes toda barra era âmbar
            # vívido, mesmo passando MUITO dos 110 dias — parecia que TODO
            # local estava crítico). Refinado no brief de design: só quem
            # passa do prazo fica vermelho (problema real); quem está dentro
            # fica num âmbar discreto/translúcido (identidade, não alarme).
            #
            # 2026-08-24, 3ª rodada ("hoje praticamente todas as barras
            # estao vermelhas... isso deixa o grafico pesado... vermelho so
            # como alerta"): o laranja `{AMBER}66` (40% opacidade) ficava
            # visualmente MUITO fraco perto do vermelho sólido — mesmo
            # tendo poucos locais fora do prazo, o gráfico "parecia" quase
            # todo vermelho por contraste. Trocado pro AMBER sólido (mesma
            # regra de sempre: > limite = vermelho, senão laranja — só a
            # opacidade mudou, a REGRA não).
            cores_barras = [
                STATUS["critical"] if v > PRAZO_CONTRATUAL_TAT_DIAS else AMBER
                for v in media_local["TAT médio (dias)"]
            ]
            fig_local = go.Figure(go.Bar(
                x=media_local["TAT médio (dias)"], y=media_local["Onde se encontra"],
                orientation="h", marker_color=cores_barras,
                text=media_local["TAT médio (dias)"], textposition="outside", textfont_size=13,
                customdata=media_local["Quantidade"],
                hovertemplate="%{y}<br>TAT médio: %{x} dias<br>Quantidade: %{customdata}<extra></extra>",
            ))
            # Linha do prazo contratual em laranja/âmbar (pedido do Wallace no
            # brief: "usar laranja/amarelo para essa referência") — antes
            # estava vermelha, o que confundia com "problema" (a linha em si
            # não é um problema, é só a referência de onde o prazo vence).
            fig_local.add_vline(x=PRAZO_CONTRATUAL_TAT_DIAS, line_dash="dash", line_color=AMBER,
                                 annotation_text=f"Limite — {PRAZO_CONTRATUAL_TAT_DIAS}d",
                                 annotation_font_color=AMBER, annotation_font_size=12)
            fig_local.update_layout(yaxis_title="", xaxis_title="", bargap=0.18)
            fig_local.update_yaxes(tickfont=dict(size=12))
            # Altura maior (26px/linha, era 24) e piso mais alto (360, era
            # igual ao donut de 260) — pedido: "gráfico deve ser um dos
            # principais da tela".
            layout_grafico(fig_local, altura=max(360, 26 * len(media_local)))
            # `automargin` DEPOIS de `layout_grafico()` (que fixa margin.l=10
            # por padrão pros outros gráficos) — nomes de local como "Em
            # processo interno / não informado pela empresa" são bem
            # compridos; sem isso o Plotly cortava o rótulo ou espremia as
            # barras contra a borda. `automargin` deixa o Plotly calcular a
            # margem certa pro rótulo mais comprido, sem chute fixo.
            fig_local.update_yaxes(automargin=True)
            fig_local.update_layout(margin=dict(l=10, r=40, t=10, b=10))
            evento_bar = st.plotly_chart(
                fig_local, width="stretch", on_select="rerun", selection_mode="points", key="rep_bar_local_clique",
            )
            pontos = evento_bar.selection.get("points", []) if evento_bar else []
            locais_clicados = sorted({p["y"] for p in pontos if "y" in p})
            if locais_clicados:
                st.session_state["rep_filtro_local_pendente"] = locais_clicados
                st.success(f"🖱️ Clicado: **{', '.join(locais_clicados)}** — já filtrado na Tabela/Consulta.")
            with st.expander("Ver tabela — TAT médio por local"):
                st.dataframe(media_local, hide_index=True, width="stretch")

    # Ranking + histórico mensal lado a lado — pedido do Wallace via
    # imagem de referência: "adicionar abaixo dos gráficos uma tabela
    # compacta... ao lado da tabela de atrasos, incluir um gráfico de
    # barras". Mesmos dados/cálculos de sempre (ranking já existia dentro
    # do expander; histórico reaproveita `_dados_historico_mensal`, a
    # mesma função usada na aba "Histórico" — nada duplicado).
    t1, t2 = st.columns([1.1, 1])
    with t1, st.container(border=True):
        st.caption(
            "Top 10 OS mais atrasadas — com a empresa/terceirizados, abertas a partir de "
            f"{INICIO_COBRANCA_PRAZO.strftime('%d/%m/%Y')}"
        )
        piores = (
            empresa_cobravel.dropna(subset=["tat_siloms"])
            .sort_values("tat_siloms", ascending=False)
            .head(10)[["tat_siloms", "os", "pn", "nomenclatura", "unidade_solicitante", "onde_se_encontra"]]
            .rename(columns={
                "tat_siloms": "TAT (dias)", "os": "OS", "pn": "PN", "nomenclatura": "Nomenclatura",
                "unidade_solicitante": "Unidade", "onde_se_encontra": "Onde se encontra",
            })
        )
        if piores.empty:
            st.caption("Sem OS com TAT SILOMS preenchido nesse escopo.")
        else:
            piores["TAT (dias)"] = piores["TAT (dias)"].round(0).astype(int)
            # Cor com significado, não decoração (pedido do Wallace): número em
            # vermelho pra qualquer um fora do prazo (esperado, já que é a lista
            # das piores); fundo vermelho BEM suave só pro extremo (> 2x o
            # prazo contratual) — não pinta a linha inteira de vermelho forte
            # só porque está nessa tabela.
            limite_extremo = PRAZO_CONTRATUAL_TAT_DIAS * 2
            styler_piores = (
                piores.style
                .map(lambda v: f"color: {STATUS['critical']}; font-weight: 700;", subset=["TAT (dias)"])
                .apply(
                    lambda row: [f"background-color: {STATUS['critical']}14"] * len(row)
                    if row["TAT (dias)"] > limite_extremo else [""] * len(row),
                    axis=1,
                )
            )
            # Altura maior + linhas mais altas (`row_height`, 2026-08-24, 3ª
            # rodada: "aumentar a altura do container... nao deixar a
            # tabela espremida") — 10 linhas + cabeçalho cabem confortável
            # em ~420px com row_height=36 (era height=340 sem row_height,
            # ficava com as 10 linhas espremidas).
            st.dataframe(styler_piores, hide_index=True, width="stretch", height=420, row_height=36)

    with t2, st.container(border=True):
        st.caption("Histórico mensal de aberturas (OS)")
        contagem_hist = _dados_historico_mensal(df).tail(12)
        st.plotly_chart(
            _figura_historico_mensal(contagem_hist, altura=420), width="stretch",
            key="rep_hist_mensal_compacto",
        )

    # "Como os números se conectam" — fluxo horizontal (pedido do Wallace
    # via imagem de referência, substitui a árvore clicável de mais cedo
    # no mesmo dia), sempre sobre TODAS as OS (`df`, não `escopo_df` — o
    # radio de escopo lá em cima não muda esse fluxo, que explica o
    # universo inteiro: abertas E fechadas ao mesmo tempo).
    titulo_bloco("Como os números se conectam")
    abertas_geral = df[df["em_aberto"]]
    fechadas_geral = df[~df["em_aberto"]]
    entregue_geral = abertas_geral[abertas_geral["onde_se_encontra"].isin(LOCAIS_ENTREGUES)]
    com_empresa_geral = abertas_geral[~abertas_geral["onde_se_encontra"].isin(LOCAIS_ENTREGUES)]
    st.markdown(
        _fluxo_conexoes_html(
            total=len(df), abertas=len(abertas_geral), fechadas=len(fechadas_geral),
            com_empresa=len(com_empresa_geral), entregue=len(entregue_geral),
        ),
        unsafe_allow_html=True,
    )

    st.divider()


def _tabela_para_texto(tabela):
    """Converte TODAS as colunas pra string de exibição, com célula vazia
    virando "" — não só uma lista fixa de colunas como antes. Bug mudo
    achado em 2026-08-24 (mesmo já corrigido no Cômputo Mensal,
    2026-08-20): célula vazia (None/NaN/NaT) aparecia como o texto literal
    "None" na tabela em vez de branco — o Streamlit ignora o na_rep do
    pandas nessa versão quando a coluna ainda tem valor nulo de verdade."""
    tabela = tabela.copy()
    for coluna in tabela.columns:
        tabela[coluna] = tabela[coluna].astype(str).replace({"None": "", "nan": "", "NaT": "", "<NA>": ""})
    return tabela


def _secao_tabela(df):
    # Consome o clique feito no gráfico "TAT médio por local" (aba "Visão
    # Geral") — precisa ser ANTES do multiselect "Onde se encontra" ser
    # instanciado, pra virar o valor inicial dele nesse mesmo rerun.
    if "rep_filtro_local_pendente" in st.session_state:
        st.session_state["rep_filtro_locais"] = st.session_state.pop("rep_filtro_local_pendente")

    busca = st.text_input(
        "🔍 Buscar (nomenclatura, PN, SN ou OS)", key="rep_busca_texto",
        placeholder="Ex.: fuel control, C662041-0102, 3040265533...",
    )

    col_f0, col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(6)
    with col_f0:
        pns = st.multiselect("PN", ordenar_unicos(df["pn"]), key="rep_filtro_pns")
    with col_f1:
        situacoes = st.multiselect(
            "Situação (ST_OS)", ordenar_unicos(df["situacao"]), key="rep_filtro_situacoes",
            help="Por padrão mostra só as OS em aberto. Selecione 'OS concluída' aqui para vê-las também.",
        )
    with col_f2:
        condicoes = st.multiselect("Condição", ordenar_unicos(df["condicao"]), key="rep_filtro_condicoes")
    with col_f3:
        locais = st.multiselect("Onde se encontra", ordenar_unicos(df["onde_se_encontra"]), key="rep_filtro_locais")
    with col_f4:
        unidades = st.multiselect("Unidade solicitante", ordenar_unicos(df["unidade_solicitante"]), key="rep_filtro_unidades")
    with col_f5:
        # Filtro novo (2026-08-24) — pedido do Wallace: "todo mes vamos ler
        # as planilhas de RMA... cruza os dados". Isola as OS que só existem
        # graças ao cruzamento com a planilha da empresa (não têm Situação
        # nem Data Início, ficam escondidas do "só em aberto" padrão — ver
        # `filtrado` abaixo).
        origens = st.multiselect("Origem", ordenar_unicos(df["origem_registro"]), key="rep_filtro_origens")

    col_chk1, col_chk2 = st.columns(2)
    with col_chk1:
        # Pedido do Wallace, 2026-08-24: "a tabela geral de todas as OS n
        # tem nao ne, fechadas, abertas, condenad, tudo" — antes só dava
        # pra ver tudo junto escolhendo valor num filtro (nada óbvio);
        # agora é um checkbox direto.
        mostrar_tudo = st.checkbox(
            "📋 Mostrar todas as OS (abertas + fechadas + condenadas)", key="rep_mostrar_tudo",
        )
    with col_chk2:
        so_fora_prazo = st.checkbox(
            f"⚠️ Mostrar só \"fora do prazo contratual\" (> {PRAZO_CONTRATUAL_TAT_DIAS} dias, com a "
            f"empresa/terceirizados, aberta a partir de {INICIO_COBRANCA_PRAZO.strftime('%d/%m/%Y')})",
            key="rep_so_fora_prazo",
        )

    # Situação/Origem escolhidas manualmente (ou o checkbox "mostrar
    # tudo") mandam mais que o padrão "só em aberto" — assim dá pra
    # escolher "OS concluída" (ou uma origem, ex.: "🆕 Só na empresa") e
    # ver as que já foram fechadas (as OS recuperadas da RMA nunca têm
    # Situação preenchida, então ficariam escondidas pra sempre se o
    # filtro dependesse só de "situacoes").
    filtrado = df.copy() if (mostrar_tudo or situacoes or origens) else df[df["em_aberto"]].copy()
    if busca:
        termo = busca.strip().lower()
        alvo = (
            filtrado["nomenclatura"].astype(str).str.lower()
            + " " + filtrado["pn"].astype(str).str.lower()
            + " " + filtrado["sn"].astype(str).str.lower()
            + " " + filtrado["os"].astype(str).str.lower()
        )
        filtrado = filtrado[alvo.str.contains(termo, na=False)]
    if pns:
        filtrado = filtrado[filtrado["pn"].isin(pns)]
    if situacoes:
        filtrado = filtrado[filtrado["situacao"].isin(situacoes)]
    if condicoes:
        filtrado = filtrado[filtrado["condicao"].isin(condicoes)]
    if locais:
        filtrado = filtrado[filtrado["onde_se_encontra"].isin(locais)]
    if unidades:
        filtrado = filtrado[filtrado["unidade_solicitante"].isin(unidades)]
    if origens:
        filtrado = filtrado[filtrado["origem_registro"].isin(origens)]
    if so_fora_prazo:
        entregue = filtrado["onde_se_encontra"].isin(LOCAIS_ENTREGUES)
        cobravel = pd.to_datetime(filtrado["data_inicio"], errors="coerce") >= pd.Timestamp(INICIO_COBRANCA_PRAZO)
        filtrado = filtrado[(~entregue) & cobravel & (filtrado["tat_siloms"] > PRAZO_CONTRATUAL_TAT_DIAS)]

    filtrado = filtrado.reset_index(drop=True)

    c_qtd, c_export = st.columns([3, 1])
    metrica_html(c_qtd, "OS (após filtro)", len(filtrado))
    with c_export:
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        if not filtrado.empty:
            st.download_button(
                "⬇️ Exportar (XLSX)",
                gerar_xlsx_bytes(filtrado.drop(columns=["tat_calculado"], errors="ignore"), "Reparaveis"),
                file_name="reparaveis_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )

    # "Dias até vencer o prazo" — pedido do Wallace, 2026-08-24: coluna
    # nova, não existia (só tinha o TAT bruto). Só faz sentido pra quem
    # ainda está com a empresa/terceirizados E entrou na cobrança do prazo
    # (aberta a partir de INICIO_COBRANCA_PRAZO — "vamos computar mas sem
    # cobrar, ela nao ta errada"); pra quem já foi entregue ou abriu antes
    # do corte, fica em branco (não é "sem prazo", é "não cobrado").
    entregue_mask = filtrado["onde_se_encontra"].isin(LOCAIS_ENTREGUES)
    cobravel_mask = pd.to_datetime(filtrado["data_inicio"], errors="coerce") >= pd.Timestamp(INICIO_COBRANCA_PRAZO)
    filtrado["dias_ate_vencer"] = pd.NA
    elegivel = ~entregue_mask & cobravel_mask & filtrado["tat_siloms"].notna()
    filtrado.loc[elegivel, "dias_ate_vencer"] = PRAZO_CONTRATUAL_TAT_DIAS - filtrado.loc[elegivel, "tat_siloms"]

    tabela = filtrado[[
        "os", "pn", "cff", "nomenclatura", "sn", "unidade_solicitante", "situacao",
        "condicao", "onde_se_encontra", "origem_registro", "data_inicio", "tat_siloms", "dias_ate_vencer",
        "tat_empresa", "data_entrega", "recibo", "sn_trocado_exchange", "termo_recebimento", "fonte",
    ]].copy()
    for coluna in ("data_inicio", "data_entrega"):
        tabela[coluna] = pd.to_datetime(tabela[coluna], errors="coerce").dt.strftime("%d/%m/%Y")

    # Guarda os valores numéricos ANTES de virar texto — usado só pra
    # decidir a cor da linha (`_cor_linha`), a mesma técnica do Cômputo
    # Mensal (2026-08-20): não dá pra colorir em cima da versão já em texto.
    tat_numerico = filtrado["tat_siloms"].reset_index(drop=True)
    condicao_numerica = filtrado["condicao"].reset_index(drop=True)
    cobravel_numerico = cobravel_mask.reset_index(drop=True)

    tabela = tabela.rename(columns={
        "os": "OS", "pn": "PN", "cff": "CFF", "nomenclatura": "Nomenclatura", "sn": "SN",
        "unidade_solicitante": "Unidade solicitante", "situacao": "Situação", "condicao": "Condição",
        "onde_se_encontra": "Onde se encontra", "origem_registro": "Origem / cruzamento empresa",
        "data_inicio": "Data início", "tat_siloms": "TAT SILOMS (dias)",
        "dias_ate_vencer": "Dias até vencer o prazo", "tat_empresa": "TAT empresa (dias)",
        "data_entrega": "Data de devolução empresa", "recibo": "Recibo",
        "sn_trocado_exchange": "SN trocado (exchange)", "termo_recebimento": "Termo de recebimento",
        "fonte": "Fonte (onde/devolução/recibo)",
    })
    tabela_texto = _tabela_para_texto(tabela)

    # Cor com significado, não decoração (pedido do Wallace no brief de
    # refinamento) — "fora do prazo" pinta a linha inteira num vermelho MUITO
    # suave (só sinaliza, não grita); "condenado" é um destaque DIFERENTE
    # (só a célula "Condição", texto vermelho forte) — antes os 2 casos
    # usavam o mesmo tom, misturando 2 significados diferentes numa cor só.
    idx_condicao = list(tabela_texto.columns).index("Condição")

    def _cor_linha(row):
        i = row.name
        tat = tat_numerico.iloc[i]
        condenado = isinstance(condicao_numerica.iloc[i], str) and "CONDENADO" in condicao_numerica.iloc[i].upper()
        estilos = [""] * len(row)
        # Só pinta de "fora do prazo" quem entrou na cobrança (aberta a
        # partir de INICIO_COBRANCA_PRAZO) — pedido do Wallace, 2026-08-24:
        # "vamos computar mas sem cobrar, ela nao ta errada". O TAT
        # continua aparecendo no número normalmente, só o destaque visual
        # de "isso é uma violação" que respeita o corte.
        if pd.notna(tat) and tat > PRAZO_CONTRATUAL_TAT_DIAS and cobravel_numerico.iloc[i]:
            estilos = [f"background-color: {STATUS['critical']}10"] * len(row)
        if condenado:
            estilos[idx_condicao] = f"color: {STATUS['critical']}; font-weight: 700;"
        return estilos

    styler = tabela_texto.style.apply(_cor_linha, axis=1)
    # OS/PN/Nomenclatura fixas na rolagem horizontal (pedido do Wallace:
    # "congelar, se possível: OS; PN; nomenclatura") — Streamlit 1.58
    # suporta `pinned` no column_config; seguro aqui porque `tabela_texto`
    # já não tem NaN nenhum sobrando (ver `_tabela_para_texto`) — declarar
    # column_config com NaN de verdade foi o que causou o bug do "None"
    # (ver Cômputo Mensal, 2026-08-20).
    colunas_fixas = {
        c: st.column_config.Column(pinned=True) for c in ("OS", "PN", "Nomenclatura") if c in tabela_texto.columns
    }
    st.dataframe(styler, width="stretch", hide_index=True, height=420, column_config=colunas_fixas)

    # Legenda condensada num expander (pedido do Wallace: "o texto atual
    # possui muitas informações importantes, porém ocupa bastante espaço...
    # transformar em 'ℹ️ Como interpretar esta tabela' dentro de um
    # expander, organizado em tópicos") — nada foi removido, só reorganizado.
    st.caption("🔴 Linha = fora do prazo contratual · Condição em vermelho = condenado")
    with st.expander("ℹ️ Como interpretar esta tabela"):
        st.markdown(
            "- **Linha com fundo vermelho suave** — TAT SILOMS > 110 dias (fora do prazo contratual), "
            "só pra quem ainda está com a empresa/terceirizados **e** abriu a partir de "
            f"{INICIO_COBRANCA_PRAZO.strftime('%d/%m/%Y')} (data em que a cobrança do prazo começou — "
            "OS mais antiga tem o TAT normal na coluna, só não fica destacada).\n"
            "- **\"Condição\" em vermelho** — a aba 1.9 da RMA marca esse item como condenado (o motivo "
            "vem junto no texto da célula).\n"
            "- **\"Onde se encontra\" / \"Data de devolução empresa\" / \"Recibo\"** — vêm da planilha "
            "geral (Controle de Reparáveis) por padrão.\n"
            "- **\"Origem / cruzamento empresa\"** — `SILOMS`: só está na nossa planilha geral, a "
            "empresa ainda não confirmou nada sobre essa OS especificamente. `✅ SILOMS + confirmada "
            "pela empresa`: está nas duas, e a RMA (aba 1.10) trouxe onde está/recibo/data de devolução "
            "pra ela. `🆕 Só na empresa (recuperada da RMA)`: **não estava** na nossa planilha geral (a "
            "OS fechou antes de existir nosso controle próprio, desde 2026-08-24 usamos a RMA da empresa "
            "pra recuperar essas) — sem \"Data Início\" a empresa não informa, então não calculamos TAT "
            "pra essas (ficam em branco de propósito, não é 0).\n"
            "- **Coluna \"Fonte\"** — quando mostra \"RMA {Mês}/{Ano} (entregue no mês)\", a aba 1.8 da "
            "RMA confirma que a empresa devolveu esse item NESSE mês; \"RMA {Mês}/{Ano} (histórico)\" é "
            "uma OS mais antiga que a aba 1.10 (controle acumulado) já tinha o dado, mas não é do mês em "
            "referência.\n"
            "- **\"— TAT calculado\"** (no final da \"Fonte\") — o TAT real (aba \"Visão Geral\") não veio "
            "reportado pela empresa; calculamos nós (data de devolução da RMA − data início) porque "
            "faltava na planilha geral.\n\n"
            "Em todos os casos, situação/em aberto continuam vindo só da planilha geral (não mudam por "
            "isso) — só os campos citados acima são complementados pela RMA."
        )

    with st.expander("📊 Distribuição por condição"):
        contagem = filtrado["condicao"].value_counts().reset_index()
        contagem.columns = ["condicao", "quantidade"]
        contagem = contagem.sort_values("quantidade", ascending=True)
        fig = px.bar(contagem, x="quantidade", y="condicao", orientation="h",
                     color_discrete_sequence=[AMBER])
        fig.update_traces(text=contagem["quantidade"], textposition="outside")
        fig.update_layout(yaxis_title="", xaxis_title="Quantidade", showlegend=False)
        layout_grafico(fig, altura=max(200, 26 * len(contagem)))
        st.plotly_chart(fig, width="stretch")

    st.divider()
    _secao_complemento_rma()


def render(dados):
    if data_global.mostrar_snapshot_se_necessario(dados, "reparaveis"):
        return

    st.title("Reparáveis")

    df = _mesclar_complemento_rma(dados["reparaveis"], dados.get("reparaveis_complemento_rma"))
    df["onde_se_encontra"] = df["onde_se_encontra"].fillna(LOCAL_NAO_INFORMADO)

    aba_geral, aba_tabela, aba_historico = st.tabs(["📊 Visão Geral", "📋 Tabela / Consulta", "📅 Histórico"])

    with aba_geral:
        _secao_estatisticas_tat(df)

    with aba_tabela:
        _secao_tabela(df)

    with aba_historico:
        _secao_historico_mensal(df)
