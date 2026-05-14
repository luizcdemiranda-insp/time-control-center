# =====================================================================
# 1. CONFIGURAÇÕES E IMPORTAÇÕES
# =====================================================================
import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Tenta importar a conexão, se falhar avisa o usuário
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    st.error("Biblioteca 'st-gsheets-connection' não encontrada. Instale via: pip install st-gsheets-connection")
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
        st.error("❌ Erro na configuração do Secrets.")
        st.info("Certifique-se de que o arquivo .streamlit/secrets.toml existe e está formatado corretamente.")
        st.stop()

conn = inicializar_conexao()

# Bloco de diagnóstico temporário
try:
    abas_disponiveis = conn.list_sheets()
    st.sidebar.write("Abas encontradas:", abas_disponiveis)
except Exception as e:
    st.sidebar.error("Não foi possível listar as abas.")

@st.cache_data(ttl=60)
def get_data(worksheet_name):
    try:
        # Blindagem contra planilhas vazias ou inexistentes
        df = conn.read(worksheet=worksheet_name)
        return df.fillna("")
    except Exception as e:
        st.sidebar.warning(f"Aba '{worksheet_name}' não encontrada ou vazia.")
        return pd.DataFrame()

def registrar_log(email, nome, projeto, atividade, acao):
    try:
        df_existente = conn.read(worksheet="time_logs")
        novo_registro = {
            "email": email,
            "nome": nome,
            "projeto": projeto,
            "atividade": atividade,
            "status": acao,
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
    st.caption(f"Projeto: {projeto}")
    
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

    # Login na Sidebar
    with st.sidebar:
        st.header("🔐 Acesso")
        email_input = st.text_input("Gmail cadastrado:").strip().lower()

    if not email_input:
        st.info("Digite seu e-mail na barra lateral para acessar o painel.")
        return

    # Validação de Usuário
    df_users = get_data("users")
    if df_users.empty or email_input not in df_users['email'].str.lower().values:
        st.error("Usuário não autorizado ou aba 'users' não configurada.")
        return

    user_row = df_users[df_users['email'].str.lower() == email_input].iloc[0]
    nome_usuario = user_row['nome']
    st.sidebar.success(f"Bem-vindo, {nome_usuario}")

    # Tabs
    tab_track, tab_dash = st.tabs(["🕒 Execução", "📊 Dashboard"])

    with tab_track:
        df_tasks = get_data("projects_tasks")
        if df_tasks.empty:
            st.warning("Nenhuma tarefa cadastrada em 'projects_tasks'.")
        else:
            projeto_sel = st.selectbox("Selecione o Projeto", df_tasks['projeto'].unique())
            atividades = df_tasks[df_tasks['projeto'] == projeto_sel]['atividade'].unique()

            st.divider()

            # Histórico para verificar status atual
            df_logs = get_data("time_logs")

            for task in atividades:
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    
                    # Logica para descobrir o último status desta tarefa para este usuário
                    user_task_logs = df_logs[(df_logs['email'] == email_input) & (df_logs['atividade'] == task)]
                    status_atual = user_task_logs.iloc[-1]['status'] if not user_task_logs.empty else "PENDENTE"

                    with col_info:
                        st.markdown(f"""
                            <div class="kpi-card">
                                <strong>{task}</strong><br>
                                <small>Último Status: {status_atual}</small>
                            </div>
                        """, unsafe_allow_html=True)

                    with col_btn:
                        if status_atual == "INICIAR" or status_atual == "RETOMAR":
                            # Se está rodando, permite Pausar ou Finalizar
                            c1, c2 = st.columns(2)
                            if c1.button("⏸️", key=f"pause_{task}"):
                                modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "PAUSAR")
                            if c2.button("✅", key=f"fin_{task}"):
                                modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "FINALIZAR")
                        else:
                            # Se está parado/pausado/finalizado, permite Iniciar/Retomar
                            btn_label = "🚀 INICIAR" if status_atual == "PENDENTE" else "▶️ RETOMAR"
                            if st.button(btn_label, key=f"start_{task}"):
                                modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "INICIAR")

    with tab_dash:
        st.subheader("Dashboard em desenvolvimento")
        st.dataframe(df_logs[df_logs['projeto'] == projeto_sel] if not df_logs.empty else [])

if __name__ == "__main__":
    main()
