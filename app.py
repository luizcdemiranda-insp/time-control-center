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
    st.error("Biblioteca 'st-gsheets-connection' não encontrada. Instale via pip.")
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
# 3. CONEXÃO E FUNÇÕES DE DADOS (BLINDAGEM SÊNIOR)
# =====================================================================
def inicializar_conexao():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error("🚨 FALHA NA CONEXÃO COM O GOOGLE SHEETS")
        st.exception(e)
        st.stop()

conn = inicializar_conexao()

@st.cache_data(ttl=0) # Cache zerado para refletir a planilha instantaneamente
def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            # BLINDAGEM: Limpa espaços e coloca todos os cabeçalhos em minúsculo
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df.fillna("")
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def registrar_log(email, nome, projeto, atividade, acao):
    try:
        df_existente = get_data("time_logs") # Usa a função blindada
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
        st.error(f"Erro ao salvar na planilha: {e}")
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

    # Carregamento da aba de usuários
    df_users = get_data("users")

    with st.sidebar:
        st.header("🔐 Acesso")
        email_input = st.text_input("Gmail cadastrado:").strip().lower()

        # ==================== RAIO-X ====================
        st.divider()
        st.write("🛠️ **RAIO-X DA PLANILHA**")
        if not df_users.empty:
            st.write("Colunas Detectadas:", df_users.columns.tolist())
            st.dataframe(df_users.head(3)) # Mostra como o Python está lendo as células
        else:
            st.warning("A aba 'users' está vazia ou não foi encontrada.")
        st.divider()
        # ================================================

        # Trava 1: Se a coluna email não existir, interrompe sem crash
        if "email" not in df_users.columns:
            st.error("🚨 ERRO: O sistema não encontrou a coluna 'email'. Verifique o RAIO-X acima para ver o que ele está lendo.")
            return

        # Trava 2: Validação de e-mail segura
        if email_input:
            lista_emails = [str(e).strip().lower() for e in df_users['email'].tolist()]
            if email_input in lista_emails:
                st.success("✅ Acesso Liberado")
            else:
                st.error("❌ E-mail não localizado na base de dados.")

    # Protege a tela principal até o usuário passar no login
    if not email_input or "email" not in df_users.columns or email_input not in lista_emails:
        st.info("Aguardando login válido na barra lateral...")
        return

    # Se chegou aqui, o usuário está logado. Resgata o nome.
    user_row = df_users[df_users['email'] == email_input].iloc[0]
    nome_usuario = user_row.get('nome', 'Usuário')

    # Navegação do App
    tab_track, tab_dash = st.tabs(["🕒 Execução", "📊 Dashboard"])

    with tab_track:
        df_tasks = get_data("projects_tasks")
        
        # Validação da aba de tarefas
        if df_tasks.empty or "projeto" not in df_tasks.columns or "atividade" not in df_tasks.columns:
            st.warning("⚠️ A aba 'projects_tasks' precisa ter as colunas 'projeto' e 'atividade' preenchidas.")
        else:
            projeto_sel = st.selectbox("Selecione o Projeto Ativo", df_tasks['projeto'].unique())
            atividades = df_tasks[df_tasks['projeto'] == projeto_sel]['atividade'].unique()
            
            st.divider()
            df_logs = get_data("time_logs")

            # Renderiza as atividades
            for task in atividades:
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    
                    status_atual = "PENDENTE"
                    # Blindagem ao ler o histórico de logs
                    if not df_logs.empty and "email" in df_logs.columns and "atividade" in df_logs.columns:
                        user_task_logs = df_logs[(df_logs['email'] == email_input) & (df_logs['atividade'] == task)]
                        if not user_task_logs.empty:
                            status_atual = user_task_logs.iloc[-1].get('status', 'PENDENTE')

                    with col_info:
                        st.markdown(f'<div class="kpi-card"><strong>{task}</strong><br><small>Status: {status_atual}</small></div>', unsafe_allow_html=True)
                    
                    with col_btn:
                        # Dinâmica de Botões
                        if status_atual in ["INICIAR", "RETOMAR"]:
                            c1, c2 = st.columns(2)
                            if c1.button("⏸️", key=f"p_{task}"): modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "PAUSAR")
                            if c2.button("✅", key=f"f_{task}"): modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "FINALIZAR")
                        else:
                            label = "🚀 INICIAR" if status_atual == "PENDENTE" else "▶️ RETOMAR"
                            if st.button(label, key=f"s_{task}"): modal_confirmacao(email_input, nome_usuario, projeto_sel, task, "INICIAR")

    with tab_dash:
        st.subheader(f"Visão Geral: {projeto_sel}")
        if not df_logs.empty and "projeto" in df_logs.columns:
            df_projeto = df_logs[df_logs['projeto'] == projeto_sel]
            st.dataframe(df_projeto, use_container_width=True)
        else:
            st.info("Nenhum log registrado para este projeto ainda.")

if __name__ == "__main__":
    main()
