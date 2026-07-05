"""
Calcula os indicadores definidos em 00_Instrucoes/indicadores.md a partir dos
arquivos já tratados em 02_Dados_Tratados/. Serve para validar as fórmulas
com dados reais antes de ligar isso ao dashboard.
"""

import pandas as pd

from common import DADOS_TRATADOS


def indicadores_emergencias():
    df = pd.read_excel(DADOS_TRATADOS / "base_emergencias_tratada.xlsx")
    abertas = df[df["em_aberto"]]
    atrasadas = abertas[abertas["dias_atraso"] > 0]

    return {
        "Total em aberto": len(abertas),
        "Emergências atrasadas": len(atrasadas),
        "% atrasadas": round(100 * len(atrasadas) / len(abertas), 1) if len(abertas) else None,
        "Atraso médio (dias)": round(atrasadas["dias_atraso"].mean(), 1) if len(atrasadas) else None,
        "Idade média (dias)": round(abertas["dias_corridos"].mean(), 1) if len(abertas) else None,
        "Por provedor": abertas["provedor"].value_counts().to_dict(),
        "Por aeronave (MATR)": abertas["matricula_aeronave"].value_counts().to_dict(),
    }


def indicadores_reparaveis():
    df = pd.read_excel(DADOS_TRATADOS / "base_reparaveis_tratada.xlsx")
    abertas = df[df["em_aberto"]]
    condenados = abertas[abertas["condicao"].str.upper() == "CONDENADO"]

    return {
        "Total de OS em aberto": len(abertas),
        "Tempo médio em aberto (dias)": round(abertas["tat_siloms"].mean(), 1) if len(abertas) else None,
        "% condenados": round(100 * len(condenados) / len(abertas), 1) if len(abertas) else None,
        "Por condição": abertas["condicao"].value_counts().to_dict(),
        "Por localização": abertas["onde_se_encontra"].value_counts().to_dict(),
    }


def indicadores_pagamentos():
    df = pd.read_excel(DADOS_TRATADOS / "base_pagamentos_tratada.xlsx", sheet_name="Pagamentos")
    contrato = pd.read_excel(DADOS_TRATADOS / "base_pagamentos_tratada.xlsx", sheet_name="Contrato").iloc[0]

    total_pago = df.loc[df["ordem_pagamento"].notna(), "faturado"].sum()

    return {
        "Total faturado": round(df["faturado"].sum(), 2),
        "Total pendente": round(df["pendente"].sum(), 2),
        "Total pago": round(total_pago, 2),
        "Saldo do contrato": contrato["saldo_a_faturar"],
        "% executado do contrato": round(100 * contrato["valor_liquidado"] / contrato["valor_total_contrato"], 1),
        "Valor por módulo": df.groupby("modulo")["valor_nfs"].sum().round(2).to_dict(),
        "Evolução mensal": df[df["tipo_registro"] == "mensal"].groupby("referencia")["valor_nfs"].sum().round(2).to_dict(),
    }


def main():
    print("=== Emergências Abertas ===")
    for k, v in indicadores_emergencias().items():
        print(f"{k}: {v}")

    print("\n=== Reparáveis ===")
    for k, v in indicadores_reparaveis().items():
        print(f"{k}: {v}")

    print("\n=== Pagamentos ===")
    for k, v in indicadores_pagamentos().items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
