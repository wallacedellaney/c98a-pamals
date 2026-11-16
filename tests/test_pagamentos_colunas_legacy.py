"""Regressão para a base de pagamentos anterior às colunas de OB."""

from pathlib import Path
import sys
import unittest

import pandas as pd


DASHBOARD_ROOT = Path(__file__).resolve().parents[1] / "Contrato 005" / "Dashboard" / "03_Dashboard"
sys.path.insert(0, str(DASHBOARD_ROOT))

from contrato005.secoes import pagamentos  # noqa: E402


class PagamentosColunasLegacyTest(unittest.TestCase):
    def test_tabela_aceita_base_anterior_sem_ob_ou_data_pagamento(self):
        """A tela não pode quebrar enquanto o Excel tratado ainda é a versão anterior."""
        legado = pd.DataFrame({
            "modulo": [1],
            "referencia": ["OUT/26"],
            "numero_nota_fiscal": [78],
            "data": [pd.Timestamp("2026-11-12")],
            "valor_nfs": [1765575.55],
            "faturado": [1765575.55],
            "pendente": [None],
            "situacao": ["Faturado, aguardando liquidação"],
            "ordem_pagamento": [None],
            "observacao": ["NF enviada à COMREC"],
            "empenho": ["2026NE001237"],
            "empenho_responsavel": [None],
        })

        tabela = pagamentos.preparar_tabela_pagamentos(legado, modo_externo=False)

        self.assertEqual(list(tabela.columns), [
            "modulo", "referencia", "numero_nota_fiscal", "data", "valor_nfs",
            "faturado", "pendente", "situacao", "ordem_pagamento", "observacao",
            "empenho", "ordem_bancaria", "data_pagamento", "empenho_responsavel",
        ])
        self.assertTrue(pd.isna(tabela.at[0, "ordem_bancaria"]))
        self.assertTrue(pd.isna(tabela.at[0, "data_pagamento"]))


if __name__ == "__main__":
    unittest.main()
