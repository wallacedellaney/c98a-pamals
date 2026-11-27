"""Impedimentos gerados para outra aeronave não penalizam a matrícula de origem."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Contrato 005/Dashboard/05_Scripts/python'))
import calcular_computo_mensal as computo


class DestinoEmergenciaTest(unittest.TestCase):
    def calcular(self, comentario):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pasta = Path(tmp.name)
        fonte = pasta / 'emergencias.xlsx'
        pd.DataFrame([{
            'numero_emergencia': '386260013673', 'matricula_aeronave': '2702',
            'tpemg': 'AIFP', 'data_abertura': '2026-11-24',
            'data_info': '2026-11-24', 'atendido_cancelado': None,
            'estoque': 'Não', 'obs_coordenadoria_fiscal': comentario,
        }]).to_excel(fonte, index=False)
        with patch.object(computo, 'CAMINHO_EMERGENCIAS_HISTORICO', fonte), \
             patch.object(computo, 'PASTA_COMPUTO', pasta), \
             patch.object(computo, '_classificar_aeronaves', return_value=(['2702', '2743'], [])):
            matriz, motivos, resumo = computo.calcular_mes(2026, 11, hoje=date(2026, 11, 26))
            diaria = computo.calcular_media_diaria_vee_one(2026, 11, hoje=date(2026, 11, 26))
        return matriz, motivos, resumo, diaria

    def test_destino_diferente_exclui_ocorrencia_sem_transferir_penalidade(self):
        matriz, motivos, resumo, diaria = self.calcular('AIFP gerado para atender a Anv 2743.')
        dia25 = matriz[matriz.dia == 25].set_index('matricula').montada
        self.assertEqual(dia25.to_dict(), {'2702': 1.0, '2743': 1.0})
        self.assertTrue(motivos.empty)
        self.assertEqual(resumo['aeronaves_pontuadas'], ['2702', '2743'])
        self.assertEqual(diaria.loc[diaria.dia == 25, 'montada'].item(), 100)

    def test_destino_igual_preserva_impedimento(self):
        matriz, motivos, _, diaria = self.calcular('AIFP gerado para atender a Anv 2702.')
        self.assertEqual(matriz.loc[(matriz.matricula == '2702') & (matriz.dia == 25), 'montada'].item(), 0)
        self.assertFalse(motivos.empty)
        self.assertEqual(diaria.loc[diaria.dia == 25, 'montada'].item(), 50)

    def test_mencao_generica_a_outra_aeronave_nao_isenta(self):
        matriz, _, _, _ = self.calcular('Comparar com a Anv 2743; emergência permanece para 2702.')
        self.assertEqual(matriz.loc[(matriz.matricula == '2702') & (matriz.dia == 25), 'montada'].item(), 0)

    def test_comentario_ausente_preserva_impedimento(self):
        matriz, _, _, _ = self.calcular(None)
        self.assertEqual(matriz.loc[(matriz.matricula == '2702') & (matriz.dia == 25), 'montada'].item(), 0)


if __name__ == '__main__':
    unittest.main()
