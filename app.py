try:
    test_df = conn.read(worksheet="users", ttl=0)
    st.sidebar.success("✅ Conexão com Sheets: OK")
except Exception as e:
    st.sidebar.error("❌ Falha no Secrets/Planilha")
    st.sidebar.caption(str(e))


# =====================================================================
# 1. CONFIGURAÇÕES, IMPORTAÇÕES E CSS
# =====================================================================
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Mercúrio - Time Tracker", layout="wide")

# Injeção de CSS para UI Tática
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #F1C40F; }
    .stButton>button { border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { border-color: #FF4B4B; color: #FF4B4B; }
    /* Card Customizado */
    .kpi-card {
        background-color: #161B22;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 2. CONEXÃO E GESTÃO DE DADOS (BLINDAGEM & CACHE)
# =====================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)  # Cache de 1 minuto para velocidade
def get_data(worksheet):
    try:
        return conn.read(worksheet=worksheet).fillna("")
    except Exception as e:
        st.error(f"Erro ao acessar aba {worksheet}: {e}")
        return pd.DataFrame()

def save_log(data_row):
    """Registra a ação na aba time_logs"""
    try:
        df_existente = conn.read(worksheet="time_logs")
        df_novo = pd.concat([df_existente, pd.DataFrame([data_row])], ignore_index=True)
        conn.update(worksheet="time_logs", data=df_novo)
        st.cache_data.clear() # Limpa cache para refletir mudança
        return True
    except Exception as e:
        st.error(f"Falha ao registrar log: {e}")
        return False

# =====================================================================
# 3. COMPONENTES DE INTERFACE (DIÁLOGOS/POP-UPS)
# =====================================================================
@st.dialog("Confirmação de Atividade")
def confirmar_acao(email, nome, projeto, atividade, acao):
    st.write(f"Deseja **{acao}** a atividade: **{atividade}**?")
    st.caption(f"Projeto: {projeto}")
    
    if st.button(f"Confirmar {acao}", use_container_width=True):
        payload = {
            "email": email,
            "nome": nome,
            "projeto": projeto,
            "atividade": atividade,
            "status": acao,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        if save_log(payload):
            st.success("Registrado com sucesso!")
            time.sleep(1)
            st.rerun()

# =====================================================================
# 4. LÓGICA PRINCIPAL (CONTROLE DE FLUXO)
# =====================================================================
def main():
    # Sidebar - Login Simples (Foco em Velocidade)
    st.sidebar.title("🔐 Acesso")
    user_input = st.sidebar.text_input("Seu Gmail cadastrado:").strip().lower()

    if not user_input:
        st.warning("Por favor, insira seu e-mail para continuar.")
        return

    # Validação de Usuário Blindada
    df_users = get_data("users")
    user_data = df_users[df_users['email'].str.lower() == user_input]

    if user_data.empty:
        st.error("E-mail não autorizado.")
        return

    nome_usuario = user_data.iloc[0]['nome']
    st.sidebar.success(f"Logado como: {nome_usuario}")

    tab_exec, tab_dash = st.tabs(["🕒 Cronômetro", "📊 Dashboard"])

    with tab_exec:
        # Seleção de Projeto
        df_tasks = get_data("projects_tasks")
        projetos = df_tasks['projeto'].unique()
        projeto_sel = st.selectbox("Selecione o Projeto Ativo", projetos)

        st.divider()

        # Listagem de Atividades
        atividades = df_tasks[df_tasks['projeto'] == projeto_sel]['atividade'].tolist()
        
        # Busca o último status de cada atividade para este usuário
        df_logs = get_data("time_logs")
        
        for idx, task in enumerate(atividades):
            with st.container():
                col_txt, col_btn = st.columns([3, 1])
                
                # Verifica status atual da tarefa para o usuário
                last_log = df_logs[(df_logs['email'] == user_input) & (df_logs['atividade'] == task)].last_valid_index()
                status_atual = df_logs.loc[last_log, 'status'] if last_log is not None else "PENDENTE"
                
                with col_txt:
                    st.markdown(f"""<div class='kpi-card'><b>{task}</b><br><small>Status: {status_atual}</small></div>""", unsafe_allow_html=True)
                
                with col_btn:
                    if status_atual == "INICIAR" or status_atual == "PAUSAR":
                        if st.button(f"▶️ RETOMAR", key=f"btn_{idx}"):
                            confirmar_acao(user_input, nome_usuario, projeto_sel, task, "INICIAR")
                    elif status_atual == "INICIAR":
                         # Se já está rodando, oferece Pausar ou Finalizar
                         c1, c2 = st.columns(2)
                         if c1.button("⏸️", key=f"p_{idx}"): confirmar_acao(user_input, nome_usuario, projeto_sel, task, "PAUSAR")
                         if c2.button("✅", key=f"f_{idx}"): confirmar_acao(user_input, nome_usuario, projeto_sel, task, "FINALIZAR")
                    else:
                        if st.button(f"🚀 INICIAR", key=f"btn_{idx}"):
                            confirmar_acao(user_input, nome_usuario, projeto_sel, task, "INICIAR")

    with tab_dash:
        # Dashboard Tático
        st.subheader(f"Análise: {projeto_sel}")
        # Aqui entra a lógica de agregação de tempo (diff entre timestamps)
        st.info("O Dashboard será populado conforme os logs forem gerados na planilha.")

if __name__ == "__main__":
    import time
    main()
