import streamlit as st
import polars as pl
import pandas as pd
from tabelas import dados_aliquotas
import io

# Cache para o carregamento do arquivo
@st.cache_data(show_spinner=False)
def carregar_dados(file):
    return pl.read_excel(file, engine="calamine")

# Cache para o processamento pesado
@st.cache_data(show_spinner=False)
def processar_subvencao(df, ano, uf_uf, _dados_aliquotas):
    # Inicia o modo Lazy para otimização do plano de execução
    lf = df.lazy()
    
    # 1. Filtros precoces (CFOP >= 5000) - Reduz o volume de dados imediatamente
    lf = lf.filter(pl.col("CFOP").cast(pl.Int64) >= 5000)
    
    # 2. Transformações de Coluna Combinadas
    lf = lf.with_columns([
        # Período: String -> Date
        pl.col("Período").str.strptime(pl.Date, "%d/%m/%Y").alias("Período"),
    ])
    
    # Adiciona o ano e filtra por ano selecionado (filtro precoce)
    lf = lf.with_columns(pl.col("Período").dt.year().alias("Ano"))
    lf = lf.filter(pl.col("Ano") <= ano)
    
    # 3. Tratamento de CST e UF Origem/Destino
    # Separar CST
    lf = lf.with_columns([
        pl.col("CST ICMS").cast(pl.Utf8).str.slice(0, 1).alias("CST Primeiro Dígito"),
        pl.col("CST ICMS").cast(pl.Utf8).str.slice(1).alias("CST Resto")
    ])
    
    # Descrições CST
    mapeamento_primeiro = {
        "0": "Nacional", "1": "Estrangeira – Importação direta", "2": "Estrangeira – Adquirida no mercado interno",
        "3": "Nacional", "4": "Nacional", "5": "Nacional", "6": "Estrangeira – Importação direta",
        "7": "Estrangeira – Adquirida no mercado interno", "8": "Nacional", "9": "Outros"
    }
    mapeamento_resto = {
        "00": "Tributada integralmente",
        "10": "Tributada e com cobrança do ICMS por substituição tributária",
        "20": "Com redução de base de cálculo",
        "30": "Isenta ou não tributada e com cobrança do ICMS por substituição tributária",
        "40": "Isenta", "41": "Não tributada", "50": "Suspensão", "51": "Diferimento",
        "60": "ICMS cobrado anteriormente por substituição tributária",
        "70": "Com redução de base de cálculo e cobrança do ICMS por substituição tributária", "90": "Outras"
    }
    
    lf = lf.with_columns([
        pl.col("CST Primeiro Dígito").replace(mapeamento_primeiro, default=pl.col("CST Primeiro Dígito")).alias("CST Descrição"),
        pl.col("CST Resto").replace(mapeamento_resto, default=pl.col("CST Resto")).alias("CST Resto Descrição"),
        # UF Origem/Destino: preencher vazios
        pl.when(pl.col("UF Origem/Destino").is_null() | (pl.col("UF Origem/Destino").cast(pl.Utf8).str.strip_chars() == ""))
        .then(pl.lit(uf_uf))
        .otherwise(pl.col("UF Origem/Destino"))
        .alias("UF Origem/Destino")
    ])
    
    # Normalizar EX
    lf = lf.with_columns(
        pl.when(pl.col("UF Origem/Destino").cast(pl.Utf8).str.contains("(?i)EX"))
        .then(pl.lit(uf_uf))
        .otherwise(pl.col("UF Origem/Destino"))
        .alias("UF Origem/Destino")
    )
    
    # Separar UF Origem e Destino
    lf = lf.with_columns(
        pl.when(pl.col("UF Origem/Destino").is_not_null() & pl.col("UF Origem/Destino").str.contains("/"))
        .then(pl.col("UF Origem/Destino").str.split_exact("/", 1).struct.rename_fields(["UF Origem", "UF Destino"]))
        .otherwise(pl.struct([pl.col("UF Origem/Destino").alias("UF Origem"), pl.col("UF Origem/Destino").alias("UF Destino")]))
        .alias("ufs")
    ).unnest("ufs")
    
    # 4. Alíquotas (Join com Alíquotas)
    df_aliquotas = pl.DataFrame(_dados_aliquotas).with_columns([
        pl.when(pl.col("data_vigencia").is_not_null())
        .then(pl.col("data_vigencia").str.strptime(pl.Date, "%Y-%m-%d"))
        .otherwise(None)
        .alias("data_vigencia_date")
    ])
    
    # Join
    lf = lf.join(
        df_aliquotas.lazy(),
        left_on=["UF Origem", "UF Destino"],
        right_on=["uf_origem", "uf_destino"],
        how="left"
    )
    
    # Seleção da Alíquota
    lf = lf.with_columns([
        pl.when(pl.col("Alíquota ICMS") == 0)
        .then(
            pl.when(pl.col("aliquota_antiga").is_not_null())
            .then(
                pl.when(pl.col("data_vigencia_date").is_not_null())
                .then(
                    pl.when(pl.col("Período") < pl.col("data_vigencia_date"))
                    .then(pl.col("aliquota_antiga"))
                    .otherwise(pl.col("aliquota_nova"))
                )
                .otherwise(pl.col("aliquota_antiga"))
            )
            .otherwise(None)
        )
        .otherwise(pl.col("Alíquota ICMS"))
        .alias("Alíquota ICMS Calculada")
    ])
    
    # Limpeza de colunas do join
    colunas_remover = ["aliquota_antiga", "aliquota_nova", "data_vigencia", "data_vigencia_date"]
    lf = lf.drop(colunas_remover)
    
    # 5. Cálculo Diferença ICMS
    lf = lf.with_columns(
        ((pl.col("Vlr Operação") * (pl.col("Alíquota ICMS Calculada") / 100)).round(2) - pl.col("Vlr ICMS"))
        .round(2)
        .fill_null(0)
        .alias("Diferença ICMS")
    )
    
    # Coleta os resultados (Executa o plano otimizado)
    return lf.collect()

# Nota: As funções de tratamento individuais foram integradas à pipeline processar_subvencao para otimização com Lazy API.

def subvencoes_investimento_icms():
    st.title("Subvenções de Investimento")
    
    col1, col2 = st.columns(2)
    with col1:
        ano = st.selectbox("Selecione o ano", [2022, 2023, 2024, 2025, 2026], key="ano")
    with col2:
        uf = st.selectbox("Selecione a UF", ["AC", "AL", "AP", "AM",
         "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
         "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP",
         "SE", "TO"], key="uf")

    # Formata a UF para o formato "UF/UF"
    uf_uf = f"{uf}/{uf}"

    uploaded_file = st.file_uploader("Upload do arquivo", type="xlsx")
    
    if uploaded_file is None:
        st.info("Por favor, selecione um arquivo.")
        return
    
    try:
        # 1. Carregamento rápido
        with st.spinner("📂 Carregando arquivo..."):
            df_raw = carregar_dados(uploaded_file)
        
        # Métricas rápidas no arquivo bruto
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(border=True, label="Total de linhas", value=len(df_raw))
        with c2:
            contagem_zeros = (df_raw["Alíquota ICMS"] == 0).sum()
            st.metric(border=True, label="Linhas com Alíquota 0", value=contagem_zeros)
        with c3:
            contagem_vazios = df_raw["Alíquota ICMS"].null_count()
            st.metric(border=True, label="Linhas com Alíquota Vazia", value=contagem_vazios)

        # 2. Processamento Otimizado (Lazy e Cache)
        with st.spinner("🚀 Processando e otimizando dados..."):
            df_final_ = processar_subvencao(df_raw, ano, uf_uf, dados_aliquotas)

        if len(df_final_) == 0:
            st.warning("Nenhum dado encontrado após os filtros (CFOP >= 5000 e Ano selecionado).")
            return

        # 3. Exibição e Tabela Dinâmica
        colunas_exibidas = ['CNPJ', 'Inscrição Estadual', 'Período',
            'Tipo Operação', 'Indicador Emitente', 'Registro Escrituração',
            'Código Participante', 'CNPJ/CPF Participante', 'Nome Participante',
            'UF Origem/Destino', 'Código Município', 'Município', 'Modelo',
            'Situação', 'Série', 'Número Documento', 'Chave Documento Eletrônico',
            'Data Documento', 'Data Entrada/Saída', 'Vlr Documento', 'Vlr Desconto',
            'Vlr Abatimento NT', 'Vlr Mercadoria', 'Vlr Frete', 'Vlr Seguro',
            'Vlr Outras DA', 'Número Item', 'Código Item', 'Descrição Item',
            'Tipo Item', 'Código Barra', 'NCM', 'Qtde Item', 'Unidade Medida',
            'Vlr Item', 'Vlr Desconto Item', 'Vlr Operação', 'CFOP', 'Descrição CFOP',
            'CST ICMS', 'Vlr Base Cálculo ICMS', 'Vlr/Percentual Redução Base Cálculo ICMS',
            'Alíquota Interna ICMS - 0200', 'Vlr ICMS', 'Vlr Base Cálculo ICMS ST',
            'Alíquota ICMS ST', 'Vlr ICMS ST', 'Vlr IPI', 'CST Primeiro Dígito', 'CST Descrição',
            'CST Resto','CST Resto Descrição', 'Alíquota ICMS', 'Alíquota ICMS Calculada', 'Diferença ICMS',
            'Ano', 'UF Origem', 'UF Destino'
        ]

        st.subheader("📋 Dados Detalhados")
        # Mostrar apenas uma amostra se o df for muito grande para não travar o browser
        if len(df_final_) > 50000:
            st.warning("O arquivo é muito grande. Exibindo as primeiras 50.000 linhas na pré-visualização.")
            st.dataframe(df_final_.head(50000).select(colunas_exibidas))
        else:
            st.dataframe(df_final_.select(colunas_exibidas))

        # ============================================
        # TABELA DINÂMICA OTIMIZADA
        # ============================================
        st.subheader("📊 Diferença de ICMS por CST e Ano")
        
        # Agregação via Polars (extremamente rápido)
        df_agregado = df_final_.group_by(["Ano", "CST Resto Descrição"]).agg(
            pl.count().alias("Qtd Documentos"),
            pl.col("Diferença ICMS").sum().round(2).alias("Total Diferença"),
        )

        if not df_agregado.is_empty():
            df_pivot = df_agregado.pivot(
                index="CST Resto Descrição",
                columns="Ano",
                values="Total Diferença",
                aggregate_function=None
            ).fill_null(0)

            anos_cols = sorted([col for col in df_pivot.columns if col != "CST Resto Descrição"])
            
            # Ordenar colunas: Descrição, Anos (ordenados), TOTAL
            cols_ordenadas = ["CST Resto Descrição"] + anos_cols
            df_pivot = df_pivot.select(cols_ordenadas)

            # Adicionar coluna Horizontal TOTAL
            df_pivot = df_pivot.with_columns(
                pl.sum_horizontal(anos_cols).round(2).alias("TOTAL")
            ).sort("TOTAL", descending=True)

            # Preparar linha de Total Geral com as mesmas colunas e ordem
            totais_por_ano = {col: df_pivot[col].sum() for col in anos_cols}
            linha_total = pl.DataFrame({
                "CST Resto Descrição": ["TOTAL GERAL"],
                **{col: [totais_por_ano[col]] for col in anos_cols},
                "TOTAL": [df_pivot["TOTAL"].sum()]
            })
            
            # Garantir que a linha_total tenha exatamente as mesmas colunas e ordem que df_pivot
            linha_total = linha_total.select(df_pivot.columns)
            
            df_pivot = pl.concat([df_pivot, linha_total])
            
            st.dataframe(df_pivot, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados para a tabela dinâmica.")

        # ============================================
        # EXPORTAÇÃO (CORRIGIDA!)
        # ============================================
        with io.BytesIO() as output:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Converter para pandas apenas no final para exportação
                df_final_.select(colunas_exibidas).to_pandas().to_excel(writer, sheet_name="Dados Detalhados", index=False)
                if not df_agregado.is_empty():
                    df_pivot.to_pandas().to_excel(writer, sheet_name="Diferença por CST e Ano", index=False)
            
            st.download_button(
                label="📥 Baixar Excel Completo",
                data=output.getvalue(),
                file_name=f"subvencoes_icms_{uf}_{ano}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")
        st.exception(e)


if __name__ == "__main__":
    subvencoes_investimento_icms()
    


