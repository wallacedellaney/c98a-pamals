"""Protege o carregamento enxuto da área Projetos."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd

DASHBOARD_ROOT = Path(__file__).resolve().parents[1] / "Projetos" / "03_Dashboard"
sys.path.insert(0, str(DASHBOARD_ROOT))

from projetos.data import carregar_dados  # noqa: E402


class CarregamentoPorPaginaTest(unittest.TestCase):
    def test_normaliza_valores_monetarios_e_descarta_placeholder(self):
        """Valores de empenho em texto não podem interromper a tela MTA."""
        bruto = pd.Series([1000, "52250.04", "R$ 2.391.157,41", "/ /", None])

        normalizado = carregar_dados.normalizar_valor_monetario(bruto)

        self.assertAlmostEqual(normalizado.iloc[0], 1000.0)
        self.assertAlmostEqual(normalizado.iloc[1], 52250.04)
        self.assertAlmostEqual(normalizado.iloc[2], 2391157.41)
        self.assertTrue(pd.isna(normalizado.iloc[3]))
        self.assertTrue(pd.isna(normalizado.iloc[4]))

    def test_mta_nao_le_fontes_do_tpjl(self):
        """Abertura do MTA deve ficar independente dos arquivos TPJL pesados."""
        mta = object()
        historico = object()
        empenhos = object()
        esforco = object()

        with (
            patch.object(carregar_dados, "carregar_mta", return_value=(mta, 123.0)),
            patch.object(carregar_dados, "carregar_historico_mta", return_value=historico),
            patch.object(carregar_dados, "carregar_empenhos_contrato005", return_value=empenhos),
            patch.object(carregar_dados, "carregar_esforco_anual", return_value=esforco),
            patch.object(carregar_dados, "carregar_tpjl", side_effect=AssertionError("TPJL nao deve ser lido no MTA")),
            patch.object(carregar_dados, "carregar_tpjl_extras", side_effect=AssertionError("extras TPJL nao devem ser lidos no MTA")),
            patch.object(carregar_dados, "carregar_historico_tpjl", side_effect=AssertionError("historico TPJL nao deve ser lido no MTA")),
            patch.object(carregar_dados, "carregar_historico_tpjl_solicitacoes", side_effect=AssertionError("historico de solicitacoes TPJL nao deve ser lido no MTA")),
            patch.object(carregar_dados.estado, "obter_entrada", return_value={"status": "ok"}),
        ):
            dados = carregar_dados.carregar_para_pagina("MTA")

        self.assertIs(dados["mta"], mta)
        self.assertEqual(dados["mta_atualizado_em"], 123.0)
        self.assertIs(dados["mta_historico"], historico)
        self.assertIs(dados["empenhos_contrato005"], empenhos)
        self.assertIs(dados["esforco_anual"], esforco)
        self.assertNotIn("tpjl", dados)


if __name__ == "__main__":
    unittest.main()
