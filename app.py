import streamlit as st
import pandas as pd
from pymongo import MongoClient, errors
from datetime import datetime
import requests
from urllib.parse import urlencode

# Adicione a função configure_page aqui
def configure_page():
    st.set_page_config(layout="wide", page_title="Dashboard", page_icon=":bar_chart:")

configure_page()

# Função para conectar ao MongoDB
def get_mongo_client():
    try:
        username = "lennonmms7"
        password = "7d5b6r77"
        cluster_address = "teste.baoswin.mongodb.net"
        DATABASE_URL = f"mongodb+srv://{username}:{password}@{cluster_address}/?retryWrites=true&w=majority&appName=teste"

        client = MongoClient(DATABASE_URL, serverSelectionTimeoutMS=5000)
        client.server_info()  # Testa a conexão
        return client
    except errors.ServerSelectionTimeoutError as err:
        st.error(f"Erro ao conectar ao MongoDB: {err}")
        return None

# Função para salvar recibo e atualizar status no banco de dados
def salvar_recibo(nome, recibo, mes_ano, data_recibo):
    client = get_mongo_client()
    if client:
        try:
            collection = client['teste']['financeiro_itnac']
            data_datetime = datetime.combine(data_recibo, datetime.min.time())
            recibo_bytes = recibo.read()

            result = collection.update_one(
                {'nome': nome, 'mes_ano': mes_ano},
                {
                    '$inc': {'valor': 50.00},
                    '$set': {
                        'recibo': recibo_bytes,
                        'data': data_datetime,
                        'pago': True
                    }
                }
            )

            if result.modified_count > 0:
                st.success(f"Recibo de {nome} salvo e status atualizado!")
                # Simula uma recarga leve da interface
                st.experimental_set_query_params(recarregar="true")
            else:
                st.error("Erro ao atualizar o recibo no banco de dados.")

        except Exception as e:
            st.error(f"Erro ao salvar o recibo: {e}")

def recarregar_pagina():
    params = {"recarregar": "true"}
    url = f"{st.experimental_get_query_params()}?{urlencode(params)}"
    st.experimental_set_query_params(**params)
    
# Função para carregar todos os valores pagos para cálculo geral
def carregar_todos_os_valores():
    client = get_mongo_client()
    if client:
        try:
            collection = client['teste']['financeiro_itnac']
            registros = list(collection.find({'pago': True}, {'_id': 0, 'valor': 1}))
            return sum(registro.get('valor', 0) for registro in registros)
        except Exception as e:
            st.error(f"Erro ao carregar valores do banco de dados: {e}")
            return 0
    else:
        st.warning("Não foi possível conectar ao banco de dados.")
        return 0

# Função para carregar alunos do mês selecionado
def carregar_lista_alunos(mes_ano):
    client = get_mongo_client()
    if client:
        try:
            collection = client['teste']['financeiro_itnac']
            registros = list(collection.find(
                {'mes_ano': mes_ano},
                {'_id': 0, 'nome': 1, 'pago': 1, 'mes_ano': 1, 'valor': 1, 'data': 1}
            ))
            return pd.DataFrame(registros)
        except Exception as e:
            st.error(f"Erro ao carregar a lista de alunos: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# Gerar filtro de meses
def gerar_filtro_meses():
    meses = [
        datetime(year, month, 1).strftime("%m/%Y")
        for year in range(2024, 2026)
        for month in range(1, 13)
        if (year, month) >= (2024, 11) and (year, month) <= (2025, 11)
    ]
    return meses

# Encontrar o mês/ano atual no formato desejado
mes_atual = datetime.today().strftime("%m/%Y")

# Obter a lista de meses
meses = gerar_filtro_meses()

# Definir o índice inicial para o mês atual
indice_mes_atual = meses.index(mes_atual) if mes_atual in meses else 0

# Interface de seleção do mês
mes_ano = st.sidebar.selectbox("Selecione o Mês/Ano", meses, index=indice_mes_atual)

# Carregar alunos e valores
alunos_df = carregar_lista_alunos(mes_ano)
valor_mes = alunos_df[alunos_df['pago'] == True]['valor'].sum() if 'valor' in alunos_df.columns else 0
valor_geral = carregar_todos_os_valores()

# Exibir os valores na sidebar
st.sidebar.subheader(f"💰 Total Arrecadado ({mes_ano}): R$ {valor_mes:.2f}")
st.sidebar.subheader(f"💰 Total Geral Arrecadado: R$ {valor_geral:.2f}")

# Layout principal com duas colunas
col_form, col_listas = st.columns([2, 1], gap="large")

# Formulário de envio de recibo
with col_form:
    st.title("🎓 Tesouraria da Formatura")
    st.header("Envio de Recibo")
    st.info("💳 Pagamento via Pix: **11737030632**")

    if not alunos_df.empty:
        nomes = ["Selecionar Nome"] + list(alunos_df[alunos_df['pago'] == False]['nome'])
        nome = st.selectbox("Selecione seu nome", nomes)
        data_recibo = st.date_input("Data do Recibo", datetime.today().date())
        data_formatada = data_recibo.strftime('%d/%m/%Y')
        st.write(f"📅 Data Selecionada: **{data_formatada}**")

        recibo = st.file_uploader("Arraste e solte o arquivo ou clique para selecionar", type=["pdf", "jpg", "png"])

        if st.button("Enviar Recibo") and nome != "Selecionar Nome" and recibo:
            salvar_recibo(nome, recibo, mes_ano, data_recibo)

    else:
        st.warning("Nenhum aluno cadastrado para este mês.")

# Lista de pagamentos realizados e pendentes
with col_listas:
    st.subheader(f"✅ Pagamentos Realizados ({mes_ano})")
    pagos = alunos_df[alunos_df['pago'] == True]
    if pagos.empty:
        st.info("Nenhum aluno realizou o pagamento ainda.")
    else:
        for _, row in pagos.iterrows():
            data_formatada = row['data'].strftime('%d/%m/%Y') if pd.notnull(row['data']) else 'Sem data'
            st.write(f"- {row['nome']} (Data: {data_formatada})")

    st.subheader(f"⚠️ Pagamentos Pendentes ({mes_ano})")
    pendentes = alunos_df[alunos_df['pago'] == False]
    if pendentes.empty:
        st.info("Todos os alunos já pagaram.")
    else:
        for nome in pendentes['nome']:
            st.write(f"- {nome}")
