from numpy import test
from sqlalchemy.util.concurrency import greenlet_error
import streamlit as st
import polars as pl
import io
from utils.funcoes import (
    remover_colunas_nulas, 
    maisculas_acentos,
    remover_linha_metadados_ecd,
)
from utils.funcoes_pis_cofins import filtragem_natureza_contas

def pis_cofins_sobre_insumos():
    st.header(" 💰 PIS/COFINS sobre Insumos", divider="green")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            arquivo_contabil = st.file_uploader("📂 **Arquivo Contábil**", type=["xlsx", "xls"])
        with col2:
            arquivo_fiscal = st.file_uploader("📂 **Arquivo Fiscal**", type=["xlsx", "xls"])
        with col3:
            arquivo_plano_de_contas = st.file_uploader("📂 **Plano de contas**", type=["xlsx", "xls"])

        if not (arquivo_contabil and arquivo_fiscal and arquivo_plano_de_contas):
            st.toast("⚠️ Por favor, carregue todos os arquivos para continuar.")
            return  # Interrompe aqui se algum arquivo faltar

        st.toast("✅ Arquivos carregados com sucesso!")

        # --- Leitura dos arquivos usando BytesIO ---
        try:
            planilha_contabil = pl.read_excel(io.BytesIO(arquivo_contabil.read())) 
            planilha_fiscal = pl.read_excel(io.BytesIO(arquivo_fiscal.read()))
            planilha_plano_de_contas = pl.read_excel(io.BytesIO(arquivo_plano_de_contas.read()))

        except Exception as e:
            st.error(f"❌ Erro ao ler os arquivos: {e}")
            return

        # Mostrar métricas
        st.divider()
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Total de linhas Contabil", value=len(planilha_contabil), border=True)
            with col2:
                st.metric(label="Total de linhas Fiscal", value=len(planilha_fiscal), border=True)
            with col3:
                st.metric(label="Total de linhas Planos de contas", value=len(planilha_plano_de_contas), border=True)

        #  ==============================ETAPA 1================================
        # Mapeando as colunas 'Código' para 'Natureza Conta' e 'Descrição Conta Societária'
        mapa_natureza = dict(zip(planilha_plano_de_contas["Conta"].to_list(), planilha_plano_de_contas["Natureza Conta"].to_list())) # Mapear natureza da conta
        mapa_descricao = dict(zip(planilha_plano_de_contas["Conta"].to_list(), planilha_plano_de_contas["Descrição Conta Societária"].to_list())) # Mapear descrição da conta
        mapa_tipo_conta = dict(zip(planilha_plano_de_contas["Conta"].to_list(), planilha_plano_de_contas["Tipo Conta"].to_list()))  # Mapear tipo da conta

        planilha_contabil = planilha_contabil.with_columns([
            pl.col("Código").replace(mapa_natureza).alias("Natureza Conta"),  # Adicionar natureza da conta
            pl.col("Código").replace(mapa_descricao).alias("Descrição Conta Societária"),  # Adicionar descrição da conta
            pl.col("Código").replace(mapa_tipo_conta).alias("Tipo Conta")  # Adicionar tipo da conta
        ])

        #  ==============================ETAPA 2================================
        planilha_contabil = (
            planilha_contabil
            .pipe(remover_linha_metadados_ecd) # Remover linhas metadados
            .pipe(transformar_vlr_saldo_final) # Transformar a coluna 'Vlr Saldo Final' em numérica
            .pipe(remover_colunas_nulas) # Remover colunas 100% nulas
            .pipe(filtragem_historico_DC) # Filtrar historico contabil retira as linhas em branco, e apenas as que tem D/C = D
            .pipe(maisculas_acentos) # Transformar tudo em maiusculo e tira todos os acentos
            .pipe(maior_que_zero) # Filtrar maior que zero
            .pipe(extrair_nf_polars) # Extrair NF do historico
            .pipe(filtragem_natureza_contas) # Filtrar natureza da conta
        )

        planilha_fiscal = (
            planilha_fiscal
            .pipe(remover_linha_metadados_ecd) # Remover linhas metadados
            .pipe(remover_colunas_nulas) # Remover colunas 100% nulas
            .pipe(maisculas_acentos) # Transformar tudo em maiusculo e tira todos os acentos
            .pipe(filtrar_aliquota_pis) # Filtrar aliquota pis
        )

        planilha_plano_de_contas = (
            planilha_plano_de_contas
            .pipe(remover_colunas_nulas) # Remover colunas 100% nulas
            .pipe(maisculas_acentos) # Transformar tudo em maiusculo
        )

        #  ==============================ETAPA 3================================
        # Filtando a planilha contabil Natureza conta
        # planilha_contabil = (
        # planilha_contabil
        # .pipe(filtragem_natureza_contas)
        # )
         #  ==============================ETAPA 4================================

        st.dataframe(planilha_contabil)
        st.metric(label="Total de linhas Contabil", value=len(planilha_contabil), border=True)
        
        # fazer download do arquivo contabil com as informações do plano de contas
        with io.BytesIO() as output:
            planilha_contabil.write_excel(output)
            st.download_button(
                label="📥 Baixar arquivo contábil com informações do plano de contas",
                data=output.getvalue(),
                file_name="planilha_contabil_com_info.xlsx",
                mime="application/vnd.ms-excel"
            )

# FUNÇÕES CONTABILIDADE
def filtragem_historico_DC(planilha: pl.DataFrame):
    return planilha.filter(
        (pl.col("Histórico").is_not_null()) &
        (pl.col("Histórico").str.strip_chars() != "") &
        (pl.col("D/C").is_not_null()) &
        (pl.col("D/C").str.strip_chars() != "") &
        (pl.col("D/C") != "C")
    )

def transformar_vlr_saldo_final(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Transforma a coluna 'Vlr Saldo Final' em numérica.
    '''
    return planilha.with_columns(
        pl.col("Vlr Saldo Final").cast(pl.Float64, strict=False)
    )

def maior_que_zero(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Filtra linhas onde a coluna 'Vlr Saldo Final' é maior que zero.
    '''
    # Garantir que a coluna é numérica
    return planilha.filter(
        pl.col("Vlr Saldo Final").is_not_null() & (pl.col("Vlr Saldo Final") > 0)
    )
def extrair_nf_polars(planilha: pl.DataFrame) -> pl.DataFrame:
    return planilha.with_columns([
        pl.coalesce([
            # 1. Número antes de algo como "N.F.", "NFE", etc
            pl.col("Histórico").str.extract(r"\b(\d{4,9})\s*N\.?F\.?", 1),

            # 2. Número após "NF", "NF NÚMERO", etc
            pl.col("Histórico").str.extract(r"(?i)\bNF(?:\s*N[ÚU]MERO)?[:\s]*([0-9]{4,9})", 1),

            # 3. Número no início com hífen
            pl.col("Histórico").str.extract(r"^(\d{4,9})\s*[-]", 1),

            # 4. Fallback: primeiro número de 4 a 9 dígitos
            pl.col("Histórico").str.extract(r"\b(\d{4,9})\b", 1),

            # 5. Fallback: MAIOR número da frase com 4 a 14 dígitos
            pl.col("Histórico")
                .str.extract_all(r"\b(\d{4,18})\b")  # retorna lista de strings
                .list.eval(pl.element().cast(pl.Int64)).list.max()
                .cast(pl.Utf8)
        ]).alias("cod_histórico")
    ])

# FUNÇÕES FISCAL
def filtrar_aliquota_pis(planilha: pl.DataFrame) -> pl.DataFrame:
    # Converter a coluna para string, substituir vírgula por ponto e converter para Float64
    planilha = planilha.with_columns(
        pl.col("Alíquota PIS")
        .cast(pl.Utf8, strict=False)        # Garante que é string
        .str.replace(",", ".")              # Substitui vírgula por ponto
        .cast(pl.Float64, strict=False)     # Converte para Float64
        .alias("Alíquota PIS")
    )

    # Filtrar valores não nulos e maiores que zero
    planilha = planilha.filter(
        pl.col("Alíquota PIS").is_not_null() & (pl.col("Alíquota PIS") > 0)
    )
    
    return planilha

if __name__ == "__main__":
    pis_cofins_sobre_insumos()
    