# =====================================================================
# 1. CONFIGURAÇÕES E IMPORTAÇÕES
# =====================================================================
import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import os

try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    st.error("Biblioteca 'st-gsheets-connection' não encontrada. Instale via pip.")
    st.stop()

try:
    from streamlit_google_auth import Authenticate
except ImportError:
    st.error("Biblioteca 'streamlit-google-auth' não encontrada. Instale via pip.")
    st.stop()

# Configuração da página (DEVE SER O PRIMEIRO COMANDO ST)
st.set_page_config(page_title="Mercúrio - Time Tracker", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 2. ESTILO VISUAL (PADRÃO MERCÚRIO DINÂMICO)
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
        border-left: 5px solid; /* A cor é injetada via HTML inline no código */
        margin-bottom: 10px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 3. INFRAESTRUTURA: SECRETS E CONEXÕES
# =====================================================================
def gerar_json_oauth():
    """Gera o arquivo de credenciais OAuth dinamicamente para evitar exposição no GitHub."""
    caminho_arquivo = "google_credentials.json"
    
    try:
        if not os.path.exists(caminho_arquivo):
            oauth_dict = {
                "web": {
                    "client_id": st.secrets["google_oauth"]["client_id"],
                    "project_id": st.secrets["google_oauth"]["project_id"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": st.secrets["google_oauth"]["client_secret"],
                    "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]]
                }
            }
            with open(caminho_arquivo, "w") as f:
                json.dump(oauth_dict, f)
        return caminho_arquivo
    except KeyError:
        st.sidebar.error("⚠️ Configuração [google_oauth] faltando no secrets.toml.")
        st.stop()

def inicializar_conexao():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error("🚨 FALHA NA CONEXÃO COM O GOOGLE SHEETS")
        st.exception(e)
        st.stop()

conn = inicializar_conexao()

# =====================================================================
# 4. FUNÇÕES DE DADOS (BLINDADAS)
# =====================================================================
@st.cache_data(ttl=0)
def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df.fillna("")
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def registrar_log(email, nome, projeto, atividade, acao):
    try:
        url_planilha = "https://docs.google.com/spreadsheets/d/1mdsfbMh6rPUArPycuWqxm7vruUx5JRptP3Z0ufXelA0/edit"
        df_existente = get_data("time_logs")
        novo_registro = {
            "email": email, "nome": nome, "projeto": projeto,
            "atividade": atividade, "status": acao,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        df_atualizado = pd.concat([df_existente, pd.DataFrame([novo_registro])], ignore_index=True)
        conn.update(spreadsheet=url_planilha, worksheet="time_logs", data=df_atualizado)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro técnico no salvamento: {e}")
        return False

# =====================================================================
# 5. INTERFACE DE DIÁLOGO (POP-UP)
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
# 6. LÓGICA PRINCIPAL E AUTENTICAÇÃO
# =====================================================================
def main():
    st.title("🚀 Central de Controle de Atividades")

    df_users = get_data("users")
    caminho_json = gerar_json_oauth()

    # --- AUTENTICAÇÃO VIA GOOGLE (SIDEBAR) ---
    with st.sidebar:
        st.header("🔐 Acesso Seguro")
        
        authenticator = Authenticate(
            secret_credentials_path=caminho_json,
            cookie_name='mercurio_session',
            cookie_key='mercurio_tracker_secret_key_2026',
            redirect_uri=st.secrets["google_oauth"]["redirect_uri"],
        )
        
        authenticator.check_authentification()
        authenticator.login()
        
        email_usuario = None
        nome_usuario = "Usuário"

        if st.session_state.get('connected'):
            email_google = st.session_state['user_info'].get('email', '').strip().lower()
            nome_usuario = st.session_state['user_info'].get('name', 'Usuário')
            
            # Validação: O e-mail do Google precisa estar na nossa planilha 'users'
            if "email" in df_users.columns:
                lista_emails = [str(e).strip().lower() for e in df_users['email'].tolist()]
                
                if email_google in lista_emails:
                    email_usuario = email_google
                    st.success("✅ Acesso Liberado")
                    st.write(f"Operador: **{nome_usuario}**")
                    if st.button("Sair (Logout)"):
                        authenticator.logout()
                else:
                    st.error("❌ Acesso Negado. Seu e-mail não consta na base de permissões do sistema.")
                    if st.button("Tentar com outra conta"):
                        authenticator.logout()
            else:
                st.error("🚨 ERRO TÉCNICO: Coluna 'email' não encontrada na base de dados (aba users).")

    # --- BLOQUEIO DE TELA SE NÃO AUTENTICADO ---
    if not email_usuario:
        st.info("Por favor, faça login com sua conta Google no menu lateral para acessar o painel de missão.")
        return

    # --- NAVEGAÇÃO DO APP (TABS) ---
    tab_track, tab_dash = st.tabs(["🕒 Execução", "📊 Dashboard"])

    with tab_track:
        df_tasks = get_data("projects_tasks")
        
        if df_tasks.empty or "projeto" not in df_tasks.columns or "atividade" not in df_tasks.columns:
            st.warning("⚠️ Planilha de tarefas não configurada. Certifique-se de preencher a aba 'projects_tasks'.")
        else:
            projeto_sel = st.selectbox("Selecione o Projeto Ativo", df_tasks['projeto'].unique())
            atividades = df_tasks[df_tasks['projeto'] == projeto_sel]['atividade'].unique()
            st.divider()
            
            df_logs = get_data("time_logs")

            # --- MOTOR DE SEGREGAÇÃO DE TAREFAS ---
            tarefas_ativas = []
            tarefas_concluidas = []

            for task in atividades:
                status_atual = "PENDENTE"
                if not df_logs.empty and "email" in df_logs.columns and "atividade" in df_logs.columns:
                    # Filtra apenas os logs DESTE usuário e DESTA tarefa
                    user_task_logs = df_logs[(df_logs['email'] == email_usuario) & (df_logs['atividade'] == task)]
                    if not user_task_logs.empty:
                        status_atual = user_task_logs.iloc[-1].get('status', 'PENDENTE')
                
                if status_atual == "FINALIZAR":
                    tarefas_concluidas.append((task, status_atual))
                else:
                    tarefas_ativas.append((task, status_atual))

            # --- RENDER: TAREFAS ATIVAS ---
            st.subheader("⚙️ Em Andamento / Pendentes")
            if not tarefas_ativas:
                st.info("✅ Todas as tarefas listadas para este projeto foram concluídas!")

            for task, status_atual in tarefas_ativas:
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    
                    with col_info:
                        st.markdown(f'<div class="kpi-card" style="border-left-color: #FF4B4B;"><strong>{task}</strong><br><small>Status: {status_atual}</small></div>', unsafe_allow_html=True)
                    
                    with col_btn:
                        if status_atual in ["INICIAR", "RETOMAR"]:
                            c1, c2 = st.columns(2)
                            if c1.button("⏸️", key=f"p_{task}"): modal_confirmacao(email_usuario, nome_usuario, projeto_sel, task, "PAUSAR")
                            if c2.button("✅", key=f"f_{task}"): modal_confirmacao(email_usuario, nome_usuario, projeto_sel, task, "FINALIZAR")
                        else:
                            label = "🚀 INICIAR" if status_atual == "PENDENTE" else "▶️ RETOMAR"
                            if st.button(label, key=f"s_{task}"): modal_confirmacao(email_usuario, nome_usuario, projeto_sel, task, "INICIAR")

            # --- RENDER: TAREFAS CONCLUÍDAS ---
            if tarefas_concluidas:
                st.write("") 
                st.subheader("✅ Tarefas Concluídas")
                
                for task, status_atual in tarefas_concluidas:
                    with st.container():
                        col_info, col_btn = st.columns([3, 1])
                        
                        with col_info:
                            st.markdown(f'<div class="kpi-card" style="border-left-color: #2ECC71; opacity: 0.8;"><strong>{task}</strong><br><small>Status: CONCLUÍDO</small></div>', unsafe_allow_html=True)
                        
                        with col_btn:
                            if st.button("🔄 REABRIR", key=f"re_{task}"): 
                                modal_confirmacao(email_usuario, nome_usuario, projeto_sel, task, "RETOMAR")

    with tab_dash:
        st.subheader(f"Visão Geral do Projeto: {projeto_sel}")
        if not df_logs.empty and "projeto" in df_logs.columns:
            df_projeto = df_logs[df_logs['projeto'] == projeto_sel]
            st.dataframe(df_projeto, use_container_width=True)
        else:
            st.info("Nenhum log de tempo registrado para este projeto ainda.")

if __name__ == "__main__":
    main()
