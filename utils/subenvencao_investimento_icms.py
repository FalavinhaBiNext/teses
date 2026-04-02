import streamlit as st
import polars as pl
import pandas as pd
from tabelas import dados_aliquotas
import io

def adicionar_descricao_cst_resto(df, coluna_cst_resto="CST Resto", 
                            coluna_descricao_resto="CST Resto Descrição",
                            mapeamento_cst_resto=None):
    """
    Adiciona uma coluna com a descrição do CST baseada no resto do CST.
    
    Args:
        df: DataFrame Polars
        coluna_cst: Nome da coluna com o resto do CST
        coluna_descricao_resto: Nome da nova coluna de descrição
        mapeamento_cst_resto: Dicionário com o mapeamento (default: CST_ICMS)
    
    Returns:
        DataFrame com a nova coluna de descrição
    """
    # Dicionário padrão se não for informado
    if mapeamento_cst_resto is None:
        mapeamento_cst_resto = {
            "00": "Tributada integralmente",
            "10": "Tributada e com cobrança do ICMS por substituição tributária",
            "20": "Com redução de base de cálculo",
            "30": "Isenta ou não tributada e com cobrança do ICMS por substituição tributária",
            "40": "Isenta",
            "41": "Não tributada",
            "50": "Suspensão",
            "51": "Diferimento",
            "60": "ICMS cobrado anteriormente por substituição tributária",
            "70": "Com redução de base de cálculo e cobrança do ICMS por substituição tributária",
            "90": "Outras"
        }
    
    return df.with_columns(
        pl.col(coluna_cst_resto)
            .replace(mapeamento_cst_resto)      # ✅ Faz o mapeamento
            .alias(coluna_descricao_resto)      # ✅ Nome da nova coluna
    )

def adicionar_descricao_cst(df, coluna_cst="CST Primeiro Dígito", 
                            coluna_descricao="CST Descrição",
                            mapeamento_cst=None):
    """
    Adiciona uma coluna com a descrição do CST baseada no primeiro dígito.
    
    Args:
        df: DataFrame Polars
        coluna_cst: Nome da coluna com o primeiro dígito do CST
        coluna_descricao: Nome da nova coluna de descrição
        mapeamento_cst: Dicionário com o mapeamento (default: CST_ICMS)
    
    Returns:
        DataFrame com a nova coluna de descrição
    """
    # Dicionário padrão se não for informado
    if mapeamento_cst is None:
        mapeamento_cst = {
            0: "Nacional",
            1: "Estrangeira – Importação direta",
            2: "Estrangeira – Adquirida no mercado interno",
            3: "Nacional",
            4: "Nacional",
            5: "Nacional",
            6: "Estrangeira – Importação direta",
            7: "Estrangeira – Adquirida no mercado interno",
            8: "Nacional",
            9: "Outros"
        }
    
    return df.with_columns(
        pl.col(coluna_cst)
            .replace(mapeamento_cst)      # ✅ Faz o mapeamento
            .alias(coluna_descricao)      # ✅ Nome da nova coluna
    )

def separar_cst_icms(df, coluna_origem="CST ICMS", 
                     coluna_primeiro="CST Primeiro Dígito", 
                     coluna_resto="CST Resto"):
    """
    Separa o primeiro dígito do CST ICMS do restante do código.
    
    Exemplo:
        "010" → "0" e "10"
        "020" → "0" e "20"
        "100" → "1" e "00"
    
    Args:
        df: DataFrame Polars
        coluna_origem: Nome da coluna original com o CST
        coluna_primeiro: Nome da coluna para o primeiro dígito
        coluna_resto: Nome da coluna para o restante do código
    
    Returns:
        DataFrame com as duas novas colunas
    """
    return df.with_columns(
        # 1️⃣ Primeiro dígito (posição 0)
        pl.col(coluna_origem)
            .cast(pl.Utf8)           # Garante que é string
            .str.slice(0, 1)         # Pega 1 caractere a partir da posição 0
            .alias(coluna_primeiro),
        
        # 2️⃣ Resto do código (posição 1 em diante)
        pl.col(coluna_origem)
            .cast(pl.Utf8)           # Garante que é string
            .str.slice(1)            # Pega do caractere 1 até o final
            .alias(coluna_resto)
    )

def calcular_diferenca_icms(df, coluna_valor_operacao="Vlr Operação", 
                           coluna_aliquota="Alíquota ICMS Calculada", 
                           coluna_icms="Vlr ICMS",
                           coluna_resultado="Diferença ICMS",
                           preencher_null=0):  # ← Novo parâmetro
    """
    Calcula a diferença de ICMS com tratamento de nulos.
    
    Args:
        preencher_null: Valor para substituir null no resultado (default: 0)
                       Use None para manter null
    """
    resultado = (
        (pl.col(coluna_valor_operacao) * (pl.col(coluna_aliquota) / 100))
        .round(2)
        - pl.col(coluna_icms)
    ).round(2).alias(coluna_resultado)
    
    # Se quiser preencher null com um valor padrão
    if preencher_null is not None:
        resultado = resultado.fill_null(preencher_null)
    
    return df.with_columns(resultado)

def normalizar_uf_com_ex(df, coluna, uf_padrao):
    """
    Normaliza a coluna UF:
    1. Se contiver 'EX' → substitui por UF/UF
    2. Se for nulo ou vazio → substitui por UF/UF
    3. Caso contrário → mantém o valor
    """
    return df.with_columns(
        pl.when(
            # Tem EX?
            pl.col(coluna).cast(pl.Utf8).str.contains("(?i)EX") |
            # É nulo?
            pl.col(coluna).is_null() |
            # É vazio ou só espaços?
            (pl.col(coluna).cast(pl.Utf8).str.strip_chars() == "")
        )
        .then(pl.lit(uf_padrao))
        .otherwise(pl.col(coluna))
        .alias(coluna)
    ) 


def aplicar_depara_aliquotas(df, dados_aliquotas, 
                             coluna_aliquota_original="Alíquota ICMS",
                             coluna_aliquota_nova="Alíquota ICMS Calculada"):
    """
    Faz o depara das alíquotas de ICMS baseado em UF Origem, UF Destino e Período.
    
    Regras:
    - Se Alíquota ICMS == 0, busca no dicionário
    - Se data_vigencia existe e Período < data_vigencia → usa aliquota_antiga
    - Se data_vigencia existe e Período >= data_vigencia → usa aliquota_nova
    - Se data_vigencia é None → usa aliquota_antiga
    - Se não encontrar match → deixa null
    
    Args:
        df: DataFrame Polars
        dados_aliquotas: Dicionário/lista com as alíquotas por UF
        coluna_aliquota_original: Nome da coluna original (não será modificada)
        coluna_aliquota_nova: Nome da nova coluna com os valores calculados
    
    Returns:
        DataFrame com a nova coluna de alíquota calculada
    """
    
    # 1️⃣ Converter o dicionário em DataFrame Polars
    df_aliquotas = pl.DataFrame(dados_aliquotas)
    
    # 2️⃣ Converter data_vigencia para tipo Date (se não for None)
    df_aliquotas = df_aliquotas.with_columns(
        pl.when(pl.col("data_vigencia").is_not_null())
        .then(pl.col("data_vigencia").str.strptime(pl.Date, "%Y-%m-%d"))
        .otherwise(None)
        .alias("data_vigencia_date")
    )
    
    # 3️⃣ ✅ Período já é Date, apenas criar alias para clareza
    df = df.with_columns(
        pl.col("Período").alias("Período_date")
    )
    
    # 4️⃣ Fazer o LEFT JOIN entre os DataFrames
    df_result = df.join(
        df_aliquotas,
        left_on=["UF Origem", "UF Destino"],
        right_on=["uf_origem", "uf_destino"],
        how="left"
    )
    
    # 5️⃣ Aplicar a lógica de seleção da alíquota
    # ⚠️ MUDANÇA PRINCIPAL: Criar NOVA coluna em vez de sobrescrever
    df_result = df_result.with_columns(
        pl.when(
            # Condição 1: Alíquota original é 0 (precisa buscar)
            pl.col(coluna_aliquota_original) == 0
        )
        .then(
            # Condição 2: Encontrou match no dicionário?
            pl.when(pl.col("aliquota_antiga").is_not_null())
            .then(
                # Tem data_vigencia?
                pl.when(pl.col("data_vigencia_date").is_not_null())
                .then(
                    # Período < data_vigencia?
                    pl.when(pl.col("Período_date") < pl.col("data_vigencia_date"))
                    .then(pl.col("aliquota_antiga"))  # Usa antiga
                    .otherwise(pl.col("aliquota_nova"))  # Usa nova
                )
                .otherwise(pl.col("aliquota_antiga"))  # data_vigencia = None → usa antiga
            )
            .otherwise(None)  # Não encontrou match → null
        )
        .otherwise(pl.col(coluna_aliquota_original))  # Não era 0 → mantém original
        .alias(coluna_aliquota_nova)  # ✅ NOVO NOME DE COLUNA
    )
    
    # 6️⃣ Remover colunas temporárias
    colunas_temporarias = [
        "uf_origem", "uf_destino", "aliquota_antiga", 
        "aliquota_nova", "data_vigencia", "data_vigencia_date",
        "Período_date"
    ]
    
    df_result = df_result.drop([c for c in colunas_temporarias if c in df_result.columns])
    
    return df_result

def adicionar_uf_origem_destino(df, coluna, uf_padrao):
    return df.with_columns(
        pl.when(
            pl.col(coluna).is_null() |                    # É nulo?
            (pl.col(coluna).cast(pl.Utf8).str.strip_chars() == "")  # OU é vazio/só espaços?
        )
        .then(pl.lit(uf_padrao))                          # Substitui pelo valor literal
        .otherwise(pl.col(coluna))                        # Mantém o original
        .alias(coluna)                                    # Mantém o nome da coluna
    )

def separar_uf_origem_destino(df, coluna):
    """
    Corrige as colunas de UF Origem e UF Destino, que estão no formato "UF Origem/Destino".
    """
    return df.with_columns(
        pl.when(pl.col(coluna).is_not_null() & 
                pl.col(coluna).str.contains("/"))
        .then(
            pl.col(coluna)
                .str.split_exact("/", 1)  # ← CORREÇÃO: 1 split = 2 campos
                .struct.rename_fields(["UF Origem", "UF Destino"])
        )
        .otherwise(
            pl.struct([
                pl.col(coluna).alias("UF Origem"),
                pl.col(coluna).alias("UF Destino"),
            ])
        )
        .alias("ufs")
    ).unnest("ufs")

def transformar_coluna_string_em_data(df, coluna):
    return df.with_columns(
        pl.col(coluna)
        .str.strptime(pl.Date, "%d/%m/%Y")
    )

def separar_ano(df, coluna):
    return df.with_columns(
        pl.col(coluna)
        .dt.year()
        .alias("Ano")
    )

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
    
    if uploaded_file is not None:
        df = pl.read_excel(uploaded_file)
    else:
        st.info("Por favor, selecione um arquivo.")
        return
    
    try:
        with st.spinner("🚀 Processando o arquivo..."):

            coluna1, coluna2, coluna3 = st.columns(3)
            with coluna1:
                st.metric(border=True, label="Total de linhas", value=len(df))
            with coluna2:
                contagem_zeros = (df["Alíquota ICMS"] == 0).sum()
                st.metric(border=True, label="Total de linhas com Alíquota ICMS igual a 0", value=contagem_zeros)
            with coluna3:
                contagem_vazios = df["Alíquota ICMS"].null_count()
                st.metric(border=True, label="Total de linhas com Alíquota ICMS nula ou vazia", value=contagem_vazios)

            # Inicio do tratamento das colunas
            df = separar_cst_icms(df) # separa o CST ICMS em duas colunas
            df = adicionar_descricao_cst(df) # adiciona a descrição do CST
            df = adicionar_descricao_cst_resto(df) # adiciona a descrição do CST
            df = adicionar_uf_origem_destino(df, "UF Origem/Destino", uf_uf) # adicionar UF a valores vazios na coluna "UF Origem/Destino"
            df = transformar_coluna_string_em_data(df, "Período") # transforma a coluna "Período" em data
            df = separar_ano(df, "Período") # separa o ano da coluna "Período"

            filtrar_maior_5000 = df.filter(pl.col("CFOP").cast(pl.Int64) >= 5000) # filtrar as linhas onde o CFOP seja maior ou igual a 5000
            noramlizar_EX = normalizar_uf_com_ex(filtrar_maior_5000, "UF Origem/Destino", uf_uf) # Normalizar a EX para o Estado Setado
            separar_uf = separar_uf_origem_destino(noramlizar_EX, "UF Origem/Destino") # Separar as colunas de UF Origem e UF Destino
            maior_que_ano = separar_uf.filter(pl.col("Ano") <= ano) # filtrar as linhas onde o ano seja maior que o ano selecionado

            aplicar_aliquotas = aplicar_depara_aliquotas(maior_que_ano, dados_aliquotas)
            df_final_ = calcular_diferenca_icms(aplicar_aliquotas, preencher_null=0)
            # Fim do tratamento das colunas

            # selecionar as colunas que serão exibidas
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

            df_exibicao = df_final_.select(colunas_exibidas)
            st.dataframe(df_exibicao)

            # ============================================
            # 1️⃣ AGREGAR OS DADOS
            # ============================================
            df_agregado = df_final_.group_by(["Ano", "CST Resto Descrição"]).agg(
                pl.count().alias("Qtd Documentos"),
                pl.col("Diferença ICMS").sum().round(2).alias("Total Diferença"),
            ).sort(["Ano", "Total Diferença"], descending=[False, True])

            # ============================================
            # 2️⃣ CRIAR A TABELA DINÂMICA (PIVOT)
            # ============================================
            df_pivot = df_agregado.pivot(
                index="CST Resto Descrição",
                columns="Ano",
                values="Total Diferença",
                aggregate_function=None
            )

            # ============================================
            # 3️⃣ ORDENAR COLUNAS
            # ============================================
            anos_cols = sorted([col for col in df_pivot.columns if col != "CST Resto Descrição"])
            df_pivot = df_pivot.select(["CST Resto Descrição"] + anos_cols)

            # ============================================
            # 4️⃣ PREENCHER NULOS COM 0
            # ============================================
            df_pivot = df_pivot.fill_null(0)

            # ============================================
            # 5️⃣ ADICIONAR COLUNA "TOTAL GERAL"
            # ============================================
            df_pivot = df_pivot.with_columns(
                pl.sum_horizontal(anos_cols).round(2).alias("TOTAL")
            )

            # ============================================
            # 6️⃣ ORDENAR LINHAS
            # ============================================
            df_pivot = df_pivot.sort("TOTAL", descending=True)

            # ============================================
            # 7️⃣ ADICIONAR LINHA DE TOTAL GERAL
            # ============================================
            totais_por_ano = {col: df_pivot[col].sum() for col in anos_cols}
            linha_total = pl.DataFrame({
                "CST Resto Descrição": ["TOTAL GERAL"],
                **{col: [totais_por_ano[col]] for col in anos_cols},
                "TOTAL": [df_pivot["TOTAL"].sum()]
            })
            df_pivot = pl.concat([df_pivot, linha_total])

            # ============================================
            # 8️⃣ MOSTRAR NO STREAMLIT
            # ============================================
            st.subheader("📊 Diferença de ICMS por CST e Ano")
            st.dataframe(df_pivot, use_container_width=True, hide_index=True)

            # ============================================
            # 9️⃣ EXPORTAR PARA EXCEL (CORRIGIDO!)
            # ============================================
            with io.BytesIO() as output:
                # ✅ Usar pandas com ExcelWriter para múltiplas abas
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    # Aba 1: Dados Detalhados (converter Polars → Pandas)
                    df_exibicao = df_final_.select(colunas_exibidas).to_pandas()
                    df_exibicao.to_excel(writer, sheet_name="Dados Detalhados", index=False)
                    
                    # Aba 2: Tabela Dinâmica (converter Polars → Pandas)
                    df_pivot_pd = df_pivot.to_pandas()
                    df_pivot_pd.to_excel(writer, sheet_name="Diferença por CST e Ano", index=False)
                
                # Botão de download
                st.download_button(
                    label="📥 Baixar Excel com Tabela Dinâmica",
                    data=output.getvalue(),
                    file_name=f"subvencoes_icms_pivot_{uf}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")


if __name__ == "__main__":
    subvencoes_investimento_icms()
    


