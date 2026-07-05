"""
Runner standalone do dashboard do Contrato 005 (sem o menu principal).
Uso normal é através de C-98A PAMALS/app.py — este arquivo existe só para
poder rodar `streamlit run app.py` direto desta pasta, se precisar.
"""

import streamlit as st

from contrato_app import render

st.set_page_config(page_title="C-98 / OPS — Contrato 005", layout="wide")
render()
