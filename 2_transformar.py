import os
import urllib.parse
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Carrega as credenciais do .env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Trata o caractere especial @ da senha
senha_segura = urllib.parse.quote_plus(DB_PASS)

# Cria o motor de conexão com o PostgreSQL
DATABASE_URL = f"postgresql://{DB_USER}:{senha_segura}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def limpar_valor(valor_str):
    """Função para converter valores em texto (ex: '1.250,50') para Decimal aceito no SQL (1250.50)"""
    if pd.isna(valor_str) or str(valor_str).strip() in ['Sem informação', '', 'nan']:
        return 0.0
    # Remove pontos de milhar e troca a vírgula decimal por ponto
    dado_limpo = str(valor_str).replace('.', '').replace(',', '.').strip()
    try:
        return float(dado_limpo)
    except:
        return 0.0

def limpar_data(data_str):
    """Função para converter datas em texto (DD/MM/YYYY) para o formato do banco (YYYY-MM-DD)"""
    if pd.isna(data_str) or str(data_str).strip() in ['Sem informação', '', 'nan']:
        return None
    try:
        return pd.to_datetime(data_str, format='%d/%m/%Y').date()
    except:
        return None

def processar_camada_silver():
    print("Iniciando o processamento da Camada Silver (Transformação)...")

    with engine.connect() as conexao:
        # ============================================================
        # 1. PROCESSANDO A TABELA: VIAGEM
        # ============================================================
        try:
            print("Transformando dados de Viagens...")
            # Idempotência: Limpa a tabela silver_viagem antes de carregar
            conexao.execute(text("TRUNCATE TABLE silver.silver_viagem CASCADE;"))
            conexao.commit()

            # Lendo a tabela bruta diretamente do banco de dados
            df_viagem = pd.read_sql_table('raw_viagem', con=engine, schema='raw')

            # Mapeamento e Limpeza das Colunas
            df_silver_viagem = pd.DataFrame()
            df_silver_viagem['id_viagem'] = df_viagem['Identificador do processo de viagem']
            df_silver_viagem['num_proposta'] = df_viagem['Número da Proposta (PCDP)']
            df_silver_viagem['situacao'] = df_viagem['Situação']
            df_silver_viagem['viagem_urgente'] = df_viagem['Viagem Urgente']
            df_silver_viagem['cod_orgao_superior'] = df_viagem['Código do órgão superior']
            df_silver_viagem['nome_orgao_superior'] = df_viagem['Nome do órgão superior']
            df_silver_viagem['nome_viajante'] = df_viagem['Nome']
            df_silver_viagem['cargo'] = df_viagem['Cargo']
            
            # Tratamento de Datas
            df_silver_viagem['data_inicio'] = df_viagem['Período - Data de início'].apply(limpar_data)
            df_silver_viagem['data_fim'] = df_viagem['Período - Data de fim'].apply(limpar_data)
            
            df_silver_viagem['destinos'] = df_viagem['Destinos']
            df_silver_viagem['motivo'] = df_viagem['Motivo']
            
            # Tratamento de Valores Monetários
            df_silver_viagem['valor_diarias'] = df_viagem['Valor diárias'].apply(limpar_valor)
            df_silver_viagem['valor_passagens'] = df_viagem['Valor passagens'].apply(limpar_valor)
            df_silver_viagem['valor_devolucao'] = df_viagem['Valor devolução'].apply(limpar_valor)
            df_silver_viagem['valor_outros_gastos'] = df_viagem['Valor outros gastos'].apply(limpar_valor)

            # [REGRA DO SENAI] CAMPOS CALCULADOS: Valor Total e Duração em Dias
            df_silver_viagem['valor_total'] = (
                df_silver_viagem['valor_diarias'] + 
                df_silver_viagem['valor_passagens'] + 
                df_silver_viagem['valor_outros_gastos'] - 
                df_silver_viagem['valor_devolucao']
            )
            
            # Calcula a diferença de dias entre fim e início
            duracao = (pd.to_datetime(df_silver_viagem['data_fim']) - pd.to_datetime(df_silver_viagem['data_inicio'])).dt.days
            df_silver_viagem['duracao_dias'] = duracao.fillna(0).astype(int)

            # Evitar IDs duplicados que quebrem a Primary Key na Silver
            df_silver_viagem = df_silver_viagem.drop_duplicates(subset=['id_viagem'])

            # Salva na Camada Silver
            df_silver_viagem.to_sql('silver_viagem', con=engine, schema='silver', if_exists='append', index=False)
            print("Sucesso: Tabela silver.silver_viagem populada!")

        except Exception as e:
            print(f"Erro ao processar a tabela Viagem: {e}")

        # ============================================================
        # 2. PROCESSANDO A TABELA: PAGAMENTO
        # ============================================================
        try:
            print("Transformando dados de Pagamentos...")
            conexao.execute(text("TRUNCATE TABLE silver.silver_pagamento CASCADE;"))
            conexao.commit()

            df_pag = pd.read_sql_table('raw_pagamento', con=engine, schema='raw')

            df_silver_pag = pd.DataFrame()
            df_silver_pag['id_viagem'] = df_pag['Identificador do processo de viagem']
            df_silver_pag['num_proposta'] = df_pag['Número da Proposta (PCDP)']
            df_silver_pag['nome_orgao_pagador'] = df_pag['Nome do órgao pagador']
            df_silver_pag['nome_ug_pagadora'] = df_pag['Nome da unidade gestora pagadora']
            df_silver_pag['tipo_pagamento'] = df_pag['Tipo de pagamento']
            df_silver_pag['valor'] = df_pag['Valor'].apply(limpar_valor)

            # Remove registros cujos IDs de viagem não existem na tabela pai (Evita quebra de FK)
            df_silver_pag = df_silver_pag[df_silver_pag['id_viagem'].isin(df_silver_viagem['id_viagem'])]

            # id_pagamento não vai aqui porque ele é SERIAL (Auto-incremento do banco)
            df_silver_pag.to_sql('silver_pagamento', con=engine, schema='silver', if_exists='append', index=False)
            print("Sucesso: Tabela silver.silver_pagamento populada!")

        except Exception as e:
            print(f"Erro ao processar a tabela Pagamento: {e}")

        # ============================================================
        # 3. PROCESSANDO A TABELA: PASSAGEM
        # ============================================================
        try:
            print("Transformando dados de Passagens...")
            conexao.execute(text("TRUNCATE TABLE silver.silver_passagem CASCADE;"))
            conexao.commit()

            df_pas = pd.read_sql_table('raw_passagem', con=engine, schema='raw')

            df_silver_pas = pd.DataFrame()
            df_silver_pas['id_viagem'] = df_pas['Identificador do processo de viagem']
            df_silver_pas['meio_transporte'] = df_pas['Meio de transporte']
            df_silver_pas['pais_origem_ida'] = df_pas['País - Origem ida']
            df_silver_pas['uf_origem_ida'] = df_pas['UF - Origem ida']
            df_silver_pas['cidade_origem_ida'] = df_pas['Cidade - Origem ida']
            df_silver_pas['pais_destino_ida'] = df_pas['País - Destino ida']
            df_silver_pas['uf_destino_ida'] = df_pas['UF - Destino ida']
            df_silver_pas['cidade_destino_ida'] = df_pas['Cidade - Destino ida']
            df_silver_pas['valor_passagem'] = df_pas['Valor da passagem'].apply(limpar_valor)
            df_silver_pas['taxa_servico'] = df_pas['Taxa de serviço'].apply(limpar_valor)
            df_silver_pas['data_emissao'] = df_pas['Data da comércio/compra' if 'Data da comércio/compra' in df_pas.columns else 'Data da emissão/compra'].apply(limpar_data)

            df_silver_pas = df_silver_pas[df_silver_pas['id_viagem'].isin(df_silver_viagem['id_viagem'])]

            df_silver_pas.to_sql('silver_passagem', con=engine, schema='silver', if_exists='append', index=False)
            print("Sucesso: Tabela silver.silver_passagem populada!")

        except Exception as e:
            print(f"Erro ao processar a tabela Passagem: {e}")

        # ============================================================
        # 4. PROCESSANDO A TABELA: TRECHO
        # ============================================================
        try:
            print("Transformando dados de Trechos...")
            conexao.execute(text("TRUNCATE TABLE silver.silver_trecho CASCADE;"))
            conexao.commit()

            df_tre = pd.read_sql_table('raw_trecho', con=engine, schema='raw')

            df_silver_tre = pd.DataFrame()
            # Note o espaço em branco que veio no cabeçalho do arquivo bruto removido pelo strip()
            df_silver_tre['id_viagem'] = df_tre.iloc[:, 0] # Pega a primeira coluna independente do espaço no nome
            df_silver_tre['sequencia_trecho'] = df_tre['Sequência Trecho'].fillna(0).astype(int)
            df_silver_tre['origem_data'] = df_tre['Origem - Data'].apply(limpar_data)
            df_silver_tre['origem_uf'] = df_tre['Origem - UF']
            df_silver_tre['origem_cidade'] = df_tre['Origem - Cidade']
            df_silver_tre['destino_data'] = df_tre['Destino - Data'].apply(limpar_data)
            df_silver_tre['destino_uf'] = df_tre['Destino - UF']
            df_silver_tre['destino_cidade'] = df_tre['Destino - Cidade']
            df_silver_tre['meio_transporte'] = df_tre['Meio de transporte']
            df_silver_tre['numero_diarias'] = df_tre['Número Diárias'].apply(limpar_valor)

            # Garante integridade referencial e remove duplicatas da restrição UNIQUE composta (id_viagem + sequencia_trecho)
            df_silver_tre = df_silver_tre[df_silver_tre['id_viagem'].isin(df_silver_viagem['id_viagem'])]
            df_silver_tre = df_silver_tre.drop_duplicates(subset=['id_viagem', 'sequencia_trecho'])

            df_silver_tre.to_sql('silver_trecho', con=engine, schema='silver', if_exists='append', index=False)
            print("Sucesso: Tabela silver.silver_trecho populada!")

        except Exception as e:
            print(f"Erro ao processar a tabela Trecho: {e}")

    print("\n--- Pipeline de Dados concluído com Sucesso! Camada Silver Pronta! ---")

if __name__ == "__main__":
    processar_camada_silver()