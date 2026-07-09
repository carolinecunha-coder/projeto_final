# ✈️ Pipeline de Dados de Viagens a Serviço (Governo Federal) — Fase 3: Camada Gold

## 📋 Escopo do Projeto e Problema Resolvido

Este projeto implementa um pipeline de dados robusto no padrão de arquitetura **Medallion (Raw → Silver → Gold)** para extrair, transformar e analisar dados públicos sobre despesas e trechos de viagens realizadas a serviço por servidores do Governo Federal.

O principal objetivo é consolidar dados brutos distribuídos em múltiplos arquivos de origem (como passagens, trechos, pagamentos e viagens), tratando inconsistências, valores ausentes, dados zerados ou negativos, e entregando uma **Camada Gold centralizada**. Essa camada permite responder a perguntas estratégicas de negócio sobre eficiência de custos, meios de transporte e comportamento de despesas públicas, gerando insights visuais automáticos.

---

# 🛠️ Técnicas e Tecnologias Utilizadas

O ecossistema técnico do projeto foi desenvolvido com tecnologias líderes de mercado em Engenharia de Dados:

- **Linguagem Principal:** Python 3.11
- **Orquestração e ETL:** `pandas` (manipulação e higienização de DataFrames), `os` e `urllib.parse`
- **Armazenamento e Banco de Dados:** PostgreSQL 18 (com uso de schemas para separação das camadas `raw`, `silver` e `gold`)
- **Conectividade:** `SQLAlchemy` para execução de queries nativas em alta performance e mapeamento relacional
- **Visualização de Dados e BI:** `Matplotlib` e `Seaborn` para geração automatizada de relatórios gráficos de alta resolução (300 DPI)

### 📊 Arquitetura de Dados (Camada Gold)

Na **Camada Gold**, os dados foram estruturados de duas formas principais para atender requisitos de negócio distintos:

1. **Tabela Física (`gold.fato_viagens_trechos`)**
   - Construída combinando tabelas da camada Silver através de operações de `INNER JOIN`.
   - Agrega dados na granularidade de trechos por viagem.

2. **VIEW Relacional (`gold.vw_financeiro_pagamentos`)**
   - Criada dinamicamente utilizando `INNER JOIN` e `GROUP BY`.
   - Centraliza o rastreio financeiro de órgãos pagadores e tipos de transação sem duplicar dados em disco.

---

# 🔐 Tratamento de Dados Sensíveis e Informações Sigilosas

Durante a execução e consolidação da Camada Gold (especificamente na análise da viagem de maior duração), o pipeline se deparou com desafios reais de governança de dados e segurança nacional presentes nas bases do Portal da Transparência.

### 1. Mascaramento por Sigilo Legal

Viagens realizadas por servidores de agências de inteligência (ABIN), segurança pública (Polícia Federal) ou missões de soberania nacional (Ministério da Defesa) têm seus campos de `nome_viajante` e `destinos` protegidos por lei.

O pipeline foi programado para tratar esses textos de forma padronizada (`.title().strip()`), garantindo que o sigilo legal seja respeitado e exibido de forma polida nos relatórios analíticos:

> *"Informações Protegidas Por Sigilo"*

### 2. Limpeza de Registros Nulos/Zerados

O banco de dados original continha viagens longas com custo total registrado como `0.0` (erros de preenchimento ou cancelamentos).

O pipeline aplicou regras rígidas na query da Camada Gold:

```sql
WHERE valor_total > 0
```

Assim, foram descartados ruídos e mantidos apenas registros financeiros válidos e auditáveis.

---

# 📈 Conclusões e Insights das Perguntas de Negócio

Abaixo estão os principais insights derivados das sete perguntas de negócio respondidas pelo arquivo `3_analise.ipynb`.

### 1. Top Órgãos com Maior Custo

Identifica quais ministérios e autarquias demandam maior orçamento para deslocamento de pessoal, permitindo auditorias focadas.

### 2. Destinos de Maior Custo Médio (Tratado)

Utilizando técnicas de split de texto (`SPLIT_PART`), foram limpos os históricos de escalas para isolar o destino principal.

Isso revelou localidades com maiores custos médios de diárias fora do eixo administrativo comum de Brasília.

### 3. Análise de Outliers (Maior Duração)

Localizou de forma precisa uma viagem atípica de **378 dias**, cujo custo totalizado foi de **R$ 120.650,00**.

O valor se mostrou proporcional ao período (cerca de **R$ 319,00 por dia**), demonstrando a capacidade do pipeline de isolar missões contínuas no exterior ou de longo prazo sem distorcer as médias gerais.

### 4. Meio de Transporte Mais Utilizado

Inicialmente visualizado em gráfico de pizza, foi convertido para um **gráfico de barras horizontais** para evitar a sobreposição de rótulos pequenos (*Ferroviário* e *Marítimo*).

O resultado mostrou de forma clara o predomínio dos modais **Aéreo** e **Rodoviário**.

### 5. Tipo de Pagamento com Maior Valor Médio

Revelou quais modalidades de repasse financeiro concentram os maiores tickets médios por transação via VIEW analítica.

### 6. UF de Destino Mais Frequente

Mapeamento geográfico de trechos que auxilia na negociação de contratos corporativos de passagens para os estados mais visitados.

### 7. Órgão Pagador Líder em Recursos

Demonstra a concentração do desembolso de verbas públicas por entidade financeira de origem.

---

# 🚀 Como Executar o Sistema

Siga os passos abaixo para implantar e executar o pipeline completo no seu ambiente local utilizando o VS Code.

## 1. Clonar e Organizar as Pastas

Certifique-se de manter a seguinte estrutura de arquivos na raiz do projeto:

```text
.
├── .env
├── requirements.txt
├── 0_criar_banco.sql
├── 1_extrair.py
├── 2_transformar.py
├── 3_analise.ipynb
└── data/
    └── viagens_2025_6meses.zip
```

---

## 2. Configurar as Variáveis de Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto e preencha com as credenciais do seu banco PostgreSQL.

```env
DB_USER=seu_usuario
DB_PASS=sua_senha_segura
DB_HOST=localhost
DB_PORT=5432
DB_NAME=projeto_final
```

---

## 3. Instalar as Dependências

Abra o terminal do VS Code e execute:

```bash
pip install -r requirements.txt
```

---

## 4. Executar os Scripts em Sequência

### Execute o script SQL

No **pgAdmin 4**, execute:

```text
0_criar_banco.sql
```

### Execute a extração dos dados

```bash
python 1_extrair.py
```

### Execute a transformação (Camada Silver)

```bash
python 2_transformar.py
```

### Execute a análise

Abra o arquivo:

```text
3_analise.ipynb
```

No VS Code:

- selecione o Kernel Python no canto superior direito;
- clique em **Run All (Executar Tudo)**.

> **Nota:** Ao finalizar a execução do notebook, os sete gráficos analíticos serão gerados automaticamente e salvos como arquivos `.png` de alta qualidade na raiz do projeto.

---

# 🔮 Melhorias Futuras

Para evolução deste ecossistema de dados, as seguintes melhorias de engenharia podem ser ser aplicadas:

### Modularização de Queries

Mover as queries SQL de strings embutidas para arquivos `.sql` separados, melhorando a manutenção do código.

### Orquestração com Airflow/Prefect

Substituir as execuções manuais por uma esteira automatizada com controle de falhas e retentativas.

### Testes de Qualidade de Dados (Great Expectations)

Implementar asserções automáticas para impedir a entrada de dados zerados ou negativos na Camada Silver.