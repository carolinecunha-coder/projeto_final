import os
import zipfile
import urllib.parse
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Carrega as credenciais do seu .env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Trata o caractere especial @ da senha
senha_segura = urllib.parse.quote_plus(DB_PASS)

# Cria o motor de conexão
DATABASE_URL = f"postgresql://{DB_USER}:{senha_segura}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def extrair_e_carregar():
    zip_path = "viagens_2025_6meses.zip" 
    pasta_destino = "data"

    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    # --- PASSO 1: DESCOMPACTAR O ZIP ---
    try:
        print(f"Abrindo o arquivo compactado: {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(pasta_destino)
        print(f"Arquivos CSV extraídos com sucesso na pasta '{pasta_destino}'!")
    except FileNotFoundError:
        print(f"Erro: O arquivo '{zip_path}' não foi encontrado.")
        return
    except Exception as e:
        print(f"Erro inesperado ao abrir o zip: {e}")
        return

    # --- PASSO 2: MAPEAMENTO DOS ARQUIVOS ---
    mapeamento = {
        "2025_Viagem.csv": "raw_viagem",
        "2025_Passagem.csv": "raw_passagem",
        "2025_Pagamento.csv": "raw_pagamento",
        "2025_Trecho.csv": "raw_trecho"
    }

    # --- PASSO 3: CARGA DINÂMICA (Criação automática da Camada Raw) ---
    for csv_nome, tabela_destino in mapeamento.items():
        csv_completo = os.path.join(pasta_destino, csv_nome)
        
        if not os.path.exists(csv_completo):
            print(f"Aviso: O arquivo {csv_nome} não foi achado. Pulando...")
            continue

        try:
            print(f"Carregando dados brutos em raw.{tabela_destino}...")
            
            # Lendo a primeira parte (chunk) para criar a tabela com a estrutura correta do CSV
            # Usamos if_exists='replace' na primeira iteração para o Pandas criar as colunas exatas
            primeiro_bloco = True
            
            for chunk in pd.read_csv(csv_completo, chunksize=10000, sep=';', dtype=str, encoding='latin1'):
                if primeiro_bloco:
                    # 'replace' reconstrói a tabela raw se adaptando aos nomes reais do CSV
                    chunk.to_sql(
                        name=tabela_destino,
                        con=engine,
                        schema='raw',
                        if_exists='replace',
                        index=False
                    )
                    primeiro_bloco = False
                else:
                    # Os blocos seguintes são apenas anexados ('append')
                    chunk.to_sql(
                        name=tabela_destino,
                        con=engine,
                        schema='raw',
                        if_exists='append',
                        index=False
                    )
            
            print(f"Sucesso! Tabela raw.{tabela_destino} populada com êxito.")
            
        except Exception as e:
            print(f"Erro ao processar e salvar a tabela {tabela_destino}: {e}")

if __name__ == "__main__":
    extrair_e_carregar()