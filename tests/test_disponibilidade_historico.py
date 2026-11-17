"""Regressões da série histórica de Disponibilidade Diária."""

from datetime import date
from pathlib import Path
import sys
import unittest

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "Coordenadoria" / "05_Scripts" / "python"
DASHBOARD = RAIZ / "Coordenadoria" / "03_Dashboard"
sys.path[:0] = [str(RAIZ), str(SCRIPTS), str(DASHBOARD)]

import extrair_disponibilidade_diaria as extrator  # noqa: E402


ARQUIVO_1711 = (
    RAIZ / "Coordenadoria" / "01_Bases_Originais" / "Disponibilidade_Diaria"
    / "Disponibilidade_17_11_2026.txt"
)


class DisponibilidadeHistoricoTest(unittest.TestCase):
    def test_nome_do_documento_corrige_data_interna_repetida(self):
        """Relatório nomeado 17/11 não pode virar um segundo ponto de 16/11."""
        resumo, _ = extrator.parse_relatorio(ARQUIVO_1711)

        data, aviso = extrator.resolver_data_referencia(ARQUIVO_1711, resumo["data_referencia"])

        self.assertEqual(data, date(2026, 11, 17))
        self.assertIn("16/11/2026", aviso)
        self.assertIn("17/11/2026", aviso)

    def test_relatorio_atual_preserva_status_ad(self):
        """AD (aeronave em desativação) precisa entrar no resumo diário."""
        resumo, aeronaves = extrator.parse_relatorio(ARQUIVO_1711)

        self.assertEqual(resumo["ad"], 1)
        self.assertEqual(sum(a["situacao"] == "AD" for a in aeronaves), 1)

    def test_total_indisponivel_aceita_historico_anterior_sem_ad(self):
        """Dias anteriores ao código AD não podem falhar por trazerem NaN."""
        from coordenadoria.secoes import disponibilidade_diaria

        relatorio_antigo = pd.Series({
            "ii": 3, "in_": 2, "itr": 1, "it": 0, "is_": 7, "ip": 1, "ad": float("nan"),
        })

        self.assertEqual(disponibilidade_diaria.total_indisponiveis(relatorio_antigo), 14)


if __name__ == "__main__":
    unittest.main()
