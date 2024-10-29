import streamlit as st
import pandas as pd
from pymongo import MongoClient, errors
from datetime import datetime

# Conectar ao MongoDB
def get_mongo_client():
    username = "lennonmms7"
    password = "7d5b6r77"
    cluster_address = "teste.baoswin.mongodb.net"
    DATABASE_URL = f"mongodb+srv://{username}:{password}@{cluster_address}/?retryWrites=true&w=majority&appName=teste"
    try:
        client = MongoClient(DATABASE_URL, serverSelectionTimeoutMS=5000)
        client.server_info()
        return client
    except errors.ServerSelectionTimeoutError as err:
        st.error(f"Erro ao conectar ao MongoDB: {err}")
        return None

# Função para carregar alunos do mês selecionado
def carregar_lista_alunos(mes_ano):
    client = get_mongo_client()
    if client:
        collection = client['teste']['financeiro_itnac']
        registros = list(collection.find(
            {'mes_ano': mes_ano},
            {'_id': 0, 'nome': 1, 'pago': 1, 'mes_ano': 1, 'valor': 1, 'data': 1}
        ))
        return pd.DataFrame(registros)
    return pd.DataFrame()

# Função para carregar todos os valores para cálculo geral
def carregar_todos_os_valores():
    client = get_mongo_client()
    if client:
        collection = client['teste']['financeiro_itnac']
        registros = list(collection.find(
            {'pago': True}, {'_id': 0, 'valor': 1}
        ))
        return sum([registro['valor'] for registro in registros])
    return 0

# Função para salvar recibo e atualizar o status no banco de dados
def salvar_recibo(nome, recibo, mes_ano, data_recibo):
    client = get_mongo_client()
    if client:
        collection = client['teste']['financeiro_itnac']

        # Converter data para datetime
        data_datetime = datetime.combine(data_recibo, datetime.min.time())

        # Incrementa o valor e salva a data no MongoDB
        result = collection.update_one(
            {'nome': nome, 'mes_ano': mes_ano},
            {
                '$inc': {'valor': 50.00},
                '$set': {
                    'recibo': recibo.getvalue(),
                    'data': data_datetime,
                    'pago': True
                }
            }
        )

        if result.modified_count > 0:
            st.success(f"Recibo de {nome} salvo e status atualizado!")
            st.experimental_rerun()  # Recarregar a interface após sucesso
        else:
            st.error("Erro ao atualizar o recibo no banco de dados.")

# Gerar filtro de meses no formato MM/YYYY
def gerar_filtro_meses():
    meses = [
        datetime(year, month, 1).strftime("%m/%Y")
        for year in range(2024, 2026)
        for month in range(1, 13)
        if (year, month) >= (2024, 11) and (year, month) <= (2025, 11)
    ]
    return meses

# Filtro de meses na sidebar
mes_ano = st.sidebar.selectbox("Selecione o Mês/Ano", gerar_filtro_meses(), index=0)

# Carregar alunos para o mês selecionado
alunos_df = carregar_lista_alunos(mes_ano)

# Layout com duas colunas: formulário e lista de pagamentos
col_form, col_listas = st.columns([2, 1], gap="large")

# Formulário de envio de recibo e exibição do Pix
with col_form:
    st.title("🎓 Tesouraria da Formatura")
    st.header("Envio de Recibo")
    st.info("💳 Pagamento via Pix: **11737030632**")  # Exibe o Pix

    if not alunos_df.empty:
        # Selectbox com placeholder "Selecionar Nome"
        nomes = ["Selecionar Nome"] + list(alunos_df[alunos_df['pago'] == False]['nome'])
        nome = st.selectbox("Selecione seu nome", nomes)

        # Campo de seleção da data do recibo
        data_recibo = st.date_input("Data do Recibo", datetime.today().date())

        # Exibir a data no formato brasileiro (dd/mm/yyyy)
        data_formatada = data_recibo.strftime('%d/%m/%Y')
        st.write(f"📅 Data Selecionada: **{data_formatada}**")  # Exibe data formatada

        recibo = st.file_uploader(
            "Arraste e solte o arquivo ou clique para selecionar",
            type=["pdf", "jpg", "png"]
        )

        if st.button("Enviar Recibo"):
            if nome == "Selecionar Nome":
                st.warning("Por favor, selecione seu nome.")
            elif not recibo:
                st.warning("Por favor, anexe o recibo.")
            else:
                salvar_recibo(nome, recibo, mes_ano, data_recibo)
    else:
        st.warning("Nenhum aluno cadastrado para este mês.")

# Lista de pagamentos
with col_listas:
    st.subheader(f"✅ Pagamentos Realizados ({mes_ano})")
    pagos = alunos_df[alunos_df['pago'] == True]
    if pagos.empty:
        st.info("Nenhum aluno realizou o pagamento ainda.")
    else:
        for _, row in pagos.iterrows():
            # Exibir a data no formato brasileiro
            data_formatada = row['data'].strftime('%d/%m/%Y') if pd.notnull(row['data']) else 'Sem data'
            st.write(f"- {row['nome']} (Data: {data_formatada})")

    st.subheader(f"⚠️ Pagamentos Pendentes ({mes_ano})")
    pendentes = alunos_df[alunos_df['pago'] == False]
    if pendentes.empty:
        st.info("Todos os alunos já pagaram.")
    else:
        for nome in pendentes['nome']:
            st.write(f"- {nome}")

# Exibir o valor total arrecadado na sidebar
valor_mes = alunos_df[alunos_df['pago'] == True]['valor'].sum() if 'valor' in alunos_df.columns else 0
valor_geral = carregar_todos_os_valores()

st.sidebar.subheader(f"💰 Total Arrecadado ({mes_ano}): R$ {valor_mes:.2f}")
st.sidebar.subheader(f"💰 Total Geral Arrecadado: R$ {valor_geral:.2f}")
