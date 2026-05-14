# =====================================================================
# 1. CONFIGURAÇÕES E IMPORTAÇÕES
# =====================================================================
import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Tenta importar a conexão
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    st.error("Biblioteca 'st-gsheets-connection' não encontrada.")
    st.stop()

# Configuração da página (DEVE SER O PRIMEIRO COMANDO ST)
st.set_page_config(page_title="Mercúrio - Time Tracker", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 2. ESTILO VISUAL (PADRÃO MERCÚRIO)
# =====================================================================
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #F1C40F; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; height: 3em; }
    .kpi-card {
        background-color: #161B22;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 3. CONEXÃO E FUNÇÕES DE DADOS (BLINDAGEM)
# =====================================================================
def inicializar_conexao():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error("🚨 FALHA NA CONEXÃO")
        st.exception(e)
        st.stop()

conn = inicializar_conexao()

@st.cache_data(ttl=0) # Cache curto para testes
def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df.fillna("")
    except Exception as e:
        return pd.DataFrame()

def registrar_log(email, nome, projeto, atividade, acao):
    try:
        df_existente = conn.read(worksheet="time_logs")
        novo_registro = {
            "email": email, "nome": nome, "projeto": projeto,
            "atividade": atividade, "status": acao,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        df_atualizado = pd.concat([df_existente, pd.DataFrame([novo_registro])], ignore_index=True)
        conn.update(worksheet="time_logs", data=df_atualizado)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# =====================================================================
# 4. INTERFACE DE DIÁLOGO (POP-UP)
# =====================================================================
@st.dialog("Confirmação de Ação")
def modal_confirmacao(email, nome, projeto, atividade, acao):
    st.markdown(f"### Deseja **{acao}** agora?")
    st.write(f"**Atividade:** {atividade}")
    if st.button(f"Confirmar {acao}", type="primary"):
        if registrar_log(email, nome, projeto, atividade, acao):
            st.success("Ação registrada!")
            time.sleep(1)
            st.rerun()

# =====================================================================
# 5. LOGICA PRINCIPAL
# =====================================================================
def main():
    st.title("🚀 Central de Controle de Atividades")

    # Carregamento de usuários
    df_users = get_data("users")

    with st.sidebar:
        st.header("🔐 Acesso")
        email_input = st.text_input("Gmail cadastrado:").strip().lower()
        
        if email_input and not df_users.empty:
            lista_emails = [str(e).strip().lower() for e in df_users['email'].tolist()]
            if email_input in lista_emails:
                st.success("✅ Usuário Identificado")
            else:
                st.error("❌ Usuário não cadastrado")

    if not email_input:
        st.info("Aguardando login na barra lateral...")
        return
        
st.write("--- DEBUG DE ACESSO ---")
st.write(f"Você digitou: '{email_input}'")
st.write(f"Emails lidos da planilha: {df_users['email'].tolist()}")

    if df_users.empty or email_input not in [str(e).strip().lower() for e in df_users['email'].tolist()]:
        st.error("Acesso negado.")
        return

    user_row = df_users[df_users['email'].str.lower() == email_input].iloc[0]
    nome_usuario = user_row['nome']

    tab_track, tab_dash = st.tabs(["🕒 Execução", "📊 Dashboard"])

    with tab_track:
        df_tasks = get_data("projects_tasks")
        if df_tasks.empty:
            st.warning("Cadastre projetos e tarefas na planilha.")
        else:
            projeto_sel = st.selectbox("Selecione o Projeto", df_tasks['projeto'].unique())
            atividades = df_tasks[df_tasks['projeto'] == projeto_sel]['atividade'].unique()
            df_logs = get_data("time_logs")

            for task in atividades:
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    user_task_logs = df_logs[(df_logs['email'] == email_input) & (df_logs['atividade'] == task)]
                    status_atual = user_task_logs.iloc[-1]['status'] if not user_task_logs.empty else "PENDENTE"

                    with col_info:
                        st.markdown(f'<div class="kpi-card"><strong>{task}</strong><br><small>Status: {status_atual}</small></div>', unsafe_allow_html=True)
                    
                    with col_btn:
                        if status_atual in ["INICIAR", "RETOMAR"]:
                            c1, c2 = st.columns(2)
                            if c1.button("⏸️", key=f"p_{task}"): modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "PAUSAR")
                            if c2.button("✅", key=f"f_{task}"): modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "FINALIZAR")
                        else:
                            label = "🚀 INICIAR" if status_atual == "PENDENTE" else "▶️ RETOMAR"
                            if st.button(label, key=f"s_{task}"): modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "INICIAR")

    with tab_dash:
        st.dataframe(df_logs)

if __name__ == "__main__":
    main()
