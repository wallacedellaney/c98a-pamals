"""Acabamento comum dos gráficos de consulta do portal."""

FONTE = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def acabamento(fig):
    fig.update_layout(
        font_family=FONTE, font_size=14, separators=fig.layout.separators or ",.",
        hoverlabel=dict(bgcolor="#18232E", bordercolor="#526678",
                        font=dict(family=FONTE, color="#F3F6F9", size=13)),
    )
    for eixo in (*fig.select_xaxes(), *fig.select_yaxes()):
        eixo.update(automargin=True, tickfont_family=FONTE, title_font_family=FONTE)
    # Em barras simples a grade serve para ler a medida. Em gráficos mistos,
    # eixos secundários e mapas de calor, o módulo escolhe a sua própria grade.
    if fig.data and all(s.type == "bar" and s.xaxis in (None, "x") and s.yaxis in (None, "y") for s in fig.data):
        orientacoes = {s.orientation or "v" for s in fig.data}
        if orientacoes == {"h"}:
            fig.update_yaxes(showgrid=False)
        elif orientacoes == {"v"}:
            fig.update_xaxes(showgrid=False)
    return fig
