import streamlit as st
import sqlite3
from sqlite3 import Error
from datetime import datetime, timedelta
import hashlib

st.set_page_config(layout="wide")

# Função para criar a conexão com o banco de dados SQLite
def criar_conexao(db_file):
    """Cria a conexão com o banco de dados SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
    return conn

# Função para atualizar a tabela existente de SIs com novas colunas
def alterar_tabela_sis(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sis)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "roteiro_aprovado" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN roteiro_aprovado TEXT")
        if "mo_enviada" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN mo_enviada TEXT")
        if "agentes_que_receberam" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN agentes_que_receberam TEXT")
        if "data_envio_mo" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN data_envio_mo DATE")
        if "agentes_de_acordo" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN agentes_de_acordo TEXT")
        if "data_de_acordo" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN data_de_acordo DATE")
        if "tipo_si" not in columns:
            cursor.execute("ALTER TABLE sis ADD COLUMN tipo_si TEXT")

        conn.commit()
    except Error as e:
        st.error(f"Erro ao alterar a tabela sis: {e}")

# Função para criar as tabelas de usuários e alterar a tabela sis
def criar_tabelas(conn):
    try:
        cursor = conn.cursor()

        # Criar tabela de usuários
        sql_create_users_table = """CREATE TABLE IF NOT EXISTS usuarios (
                                    nome TEXT PRIMARY KEY,
                                    senha TEXT NOT NULL,
                                    primeiro_acesso INTEGER NOT NULL
                                );"""
        cursor.execute(sql_create_users_table)

        # Alterar a tabela de SIs para adicionar novas colunas, se necessário
        alterar_tabela_sis(conn)

        # Verificar se os usuários padrão já existem
        cursor.execute("SELECT * FROM usuarios WHERE nome = 'Ciromar Araujo'")
        if cursor.fetchone() is None:
            senha_hash = hashlib.sha256('12345'.encode()).hexdigest()
            cursor.execute("INSERT INTO usuarios (nome, senha, primeiro_acesso) VALUES (?, ?, ?)", 
                           ('Ciromar Araujo', senha_hash, 1))

        cursor.execute("SELECT * FROM usuarios WHERE nome = 'Pedro Lima'")
        if cursor.fetchone() is None:
            senha_hash = hashlib.sha256('12345'.encode()).hexdigest()
            cursor.execute("INSERT INTO usuarios (nome, senha, primeiro_acesso) VALUES (?, ?, ?)", 
                           ('Pedro Lima', senha_hash, 1))

        conn.commit()

    except Error as e:
        st.error(f"Erro ao criar ou alterar tabelas: {e}")

# Função para verificar login
def verificar_login(conn, nome, senha):
    cursor = conn.cursor()
    cursor.execute("SELECT senha, primeiro_acesso FROM usuarios WHERE nome = ?", (nome,))
    user = cursor.fetchone()
    
    if user:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        if senha_hash == user[0]:
            return user[1]  # Retorna o estado do primeiro acesso
    return None

# Função para atualizar senha no primeiro acesso
def atualizar_senha(conn, nome, nova_senha):
    senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET senha = ?, primeiro_acesso = 0 WHERE nome = ?", (senha_hash, nome))
    conn.commit()

# Função para buscar todas as SIs no banco de dados
def listar_sis_db(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, titulo, prazo_final, status, responsavel FROM sis")
    rows = cur.fetchall()
    return rows

# Função para aplicar cores conforme o status do prazo
def cor_prazo(prazo):
    if isinstance(prazo, str):
        try:
            prazo = datetime.strptime(prazo, '%Y-%m-%d').date()  # Converter string para datetime.date
        except ValueError:
            return 'white'
    if prazo < datetime.now().date():  # Comparar apenas a data
        return 'red'
    elif prazo < datetime.now().date() + timedelta(days=3):
        return 'yellow'
    return 'green'

# Função para editar uma SI existente no banco de dados
def editar_si_db(conn, si_data):
    sql = ''' UPDATE sis
              SET titulo = ?, descricao = ?, prazo_final = ?, rm_prazo = ?, mo_prazo = ?, ai_prazo = ?, acordos_prazo = ?, status = ?, responsavel = ?, roteiro_aprovado = ?, mo_enviada = ?, agentes_que_receberam = ?, data_envio_mo = ?, agentes_de_acordo = ?, data_de_acordo = ?, tipo_si = ?
              WHERE id = ? '''
    cur = conn.cursor()
    cur.execute(sql, si_data)
    conn.commit()

# Função para excluir uma SI do banco de dados
def excluir_si_db(conn, si_id):
    sql = 'DELETE FROM sis WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, (si_id,))
    conn.commit()

# Função para atualizar o responsável da SI
def atualizar_responsavel_db(conn, responsavel, si_id):
    sql = ''' UPDATE sis
              SET responsavel = ?
              WHERE id = ? '''
    cur = conn.cursor()
    cur.execute(sql, (responsavel, si_id))
    conn.commit()

# Função para exibir um card com as informações relevantes e botões de ação
def exibir_card(conn, id, titulo, prazo_final, status, responsavel, cor_card):
    st.markdown(f"""
        <div style='background-color: {cor_card}; padding: 15px; margin-bottom: 10px; border-radius: 10px;'>
            <h4>ID: {id} - {titulo}</h4>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Prazo Final:</strong> {prazo_final}</p>
            <p><strong>Responsável:</strong> {responsavel if responsavel else 'Não atribuído'}</p>
            <div style='text-align: right;'>
    """, unsafe_allow_html=True)
    
    # Botão para Editar
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Editar", key=f"edit_{id}"):
            st.session_state.edit_si = (id, titulo, prazo_final, status, responsavel)  # Passar dados para edição
            st.experimental_rerun()

    # Botão para Atribuir ou Devolver
    with col2:
        if responsavel is None or responsavel == 'Não atribuído':
            if st.button("Atribuir", key=f"assign_{id}"):
                atualizar_responsavel_db(conn, st.session_state.nome_usuario, id)
                st.experimental_rerun()
        else:
            if responsavel == st.session_state.nome_usuario:
                if st.button("Devolver", key=f"devolver_{id}"):
                    atualizar_responsavel_db(conn, None, id)
                    st.experimental_rerun()

    # Botão para Excluir
    with col3:
        if st.button("Excluir", key=f"delete_{id}"):
            excluir_si_db(conn, id)
            st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# Função para listar os agentes de acordo com a subestação
def listar_agentes(subestacao):
    if subestacao == "SDM":
        return ["ECHO - Echoenergia", "TEB - Toda Energia do Brasil", "COP - Copel"]
    elif subestacao == "ACT":
        return ["ECHO - Echoenergia", "TEB - Toda Energia do Brasil", "COP - Copel"]
    elif subestacao == "ARI2":
        return ["ENEL", "CTG", "Newave"]
    elif subestacao == "ARN":
        return ["ENEL", "CTG", "Newave"]
    return []

# Inicializar conexão com o banco de dados
db_file = 'sis_database.db'
conn = criar_conexao(db_file)

# Criar as tabelas de usuários e alterar a tabela sis
if conn is not None:
    criar_tabelas(conn)

# Tela de Login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.nome_usuario = ""

if not st.session_state.logged_in:
    st.title("Login")
    nome = st.text_input("Nome do Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Login"):
        primeiro_acesso = verificar_login(conn, nome, senha)
        if primeiro_acesso is not None:
            st.session_state.logged_in = True
            st.session_state.nome_usuario = nome
            st.session_state.primeiro_acesso = primeiro_acesso
            st.experimental_rerun()
        else:
            st.error("Nome ou senha incorretos!")

# Troca de Senha no Primeiro Acesso
if st.session_state.logged_in and st.session_state.primeiro_acesso:
    st.title("Troca de Senha - Primeiro Acesso")
    nova_senha = st.text_input("Nova Senha", type="password")
    confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")

    if st.button("Alterar Senha"):
        if nova_senha == confirmar_senha and len(nova_senha) > 0:
            atualizar_senha(conn, st.session_state.nome_usuario, nova_senha)
            st.success("Senha alterada com sucesso!")
            st.session_state.primeiro_acesso = 0  # Atualiza o estado de primeiro acesso
            st.experimental_rerun()
        else:
            st.error("As senhas não coincidem ou são inválidas!")

# Tela Principal (se o usuário estiver logado e não for o primeiro acesso)
if st.session_state.logged_in and not st.session_state.primeiro_acesso:
    st.sidebar.title(f"Bem-vindo, {st.session_state.nome_usuario}!")
    
    menu = ["Cadastrar SI", "Monitorar SIs", "Alterar Senha", "Sair"]
    escolha = st.sidebar.selectbox("Menu", menu)

    if escolha == "Sair":
        st.session_state.logged_in = False
        st.session_state.nome_usuario = ""
        st.experimental_rerun()

    ### Alteração de Senha
    if escolha == "Alterar Senha":
        st.title("Alterar Senha")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")

        if st.button("Salvar Nova Senha"):
            if nova_senha == confirmar_senha and len(nova_senha) > 0:
                alterar_senha(conn, st.session_state.nome_usuario, nova_senha)
                st.success("Senha alterada com sucesso!")
            else:
                st.error("As senhas não coincidem ou são inválidas!")

    ### Página de Cadastro de SI
    if escolha == "Cadastrar SI":
        st.title("Cadastrar Nova Solicitação de Intervenção (SI)")

        # Formulário para adicionar nova SI com prazos dos documentos e ID manual
        id_manual = st.text_input("ID Manual da SI (deve ser único)")
        titulo = st.text_input("Título da SI")
        descricao = st.text_area("Descrição da SI")
        prazo_final = st.date_input("Prazo Final da SI", datetime.now().date() + timedelta(days=7))

        st.write("### Prazos dos Documentos Necessários")
        rm_prazo = st.date_input("Prazo do RM (Roteiro de Manobra)", datetime.now().date() + timedelta(days=7))
        mo_prazo = st.date_input("Prazo do MO (Mensagens Operativas)", datetime.now().date() + timedelta(days=7))
        ai_prazo = st.date_input("Prazo do AI (Solicitações de Impedimento)", datetime.now().date() + timedelta(days=7))
        acordos_prazo = st.date_input("Prazo dos Acordos", datetime.now().date() + timedelta(days=7))

        roteiro_aprovado = st.selectbox("Roteiro Aprovado?", ["Pendente", "Aprovado"])
        mo_enviada = st.selectbox("MO Enviada?", ["Não", "Sim"])
        data_envio_mo = st.date_input("Data de Envio da MO", datetime.now().date())
        agentes_que_receberam = st.multiselect("Agentes que Receberam MO", listar_agentes(st.selectbox("Subestação", ["SDM", "ACT", "ARI2", "ARN"])))
        agentes_de_acordo = st.selectbox("Todos os Agentes Deram o de Acordo?", ["Não", "Sim"])
        data_de_acordo = st.date_input("Data de Recebimento dos Acordos", datetime.now().date())

        tipo_si = st.selectbox("Tipo de SI", ["Normal", "Solicitação de Acesso Provisório"])

        status = st.selectbox("Status", ["Em Análise", "Pendente", "Aprovado", "Necessita Correção"])

        if st.button("Cadastrar SI"):
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO sis(id, titulo, descricao, prazo_final, rm_prazo, mo_prazo, ai_prazo, acordos_prazo, status, responsavel, roteiro_aprovado, mo_enviada, agentes_que_receberam, data_envio_mo, agentes_de_acordo, data_de_acordo, tipo_si)
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                           (id_manual, titulo, descricao, prazo_final, rm_prazo, mo_prazo, ai_prazo, acordos_prazo, status, None, roteiro_aprovado, mo_enviada, ",".join(agentes_que_receberam), data_envio_mo, agentes_de_acordo, data_de_acordo, tipo_si))
            conn.commit()
            st.success(f"Solicitação de Intervenção '{titulo}' cadastrada com sucesso!")

    ### Página de Monitoramento de SIs
    elif escolha == "Monitorar SIs":
        st.title("Monitoramento de Solicitações de Intervenção (SI)")
        
        # Exibe todas as SIs cadastradas no banco de dados
        sis_cadastradas = listar_sis_db(conn)
        if sis_cadastradas:
            st.subheader("Lista de SIs Cadastradas")

            # Exibir as SIs como cards coloridos com botões de ação
            for si in sis_cadastradas:
                id, titulo, prazo_final, status, responsavel = si

                # Obter a cor do card com base no prazo
                cor_card = cor_prazo(prazo_final)

                # Exibir o card com as informações relevantes e os botões
                exibir_card(conn, id, titulo, prazo_final, status, responsavel, cor_card)
        else:
            st.write("Nenhuma SI cadastrada ainda.")

# Fechar a conexão
if conn:
    conn.close()
