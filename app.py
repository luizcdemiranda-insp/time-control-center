# =====================================================================
# 1. CONFIGURAÇÕES, IMPORTAÇÕES E CSS
# =====================================================================
import streamlit as st  # <--- ESSENCIAL: O import deve vir primeiro!
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# Configuração da página (Deve ser o primeiro comando Streamlit)
st.set_page_config(page_title="Mercúrio - Time Tracker", layout="wide")

# =====================================================================
# 2. CONEXÃO E TESTE DE SECRETS (BLINDADO)
# =====================================================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Teste rápido de leitura para validar o Secrets
    test_check = conn.read(worksheet="users", ttl=0)
    st.sidebar.success("✅ Conexão com Sheets: OK")
except Exception as e:
    st.sidebar.error("❌ Falha no Secrets/Planilha")
    st.sidebar.info("Verifique se as credenciais no .streamlit/secrets.toml estão corretas e se a API está ativa.")
    st.stop() # Interrompe a execução para não gerar mais erros

# ... (restante do código: funções e main)
