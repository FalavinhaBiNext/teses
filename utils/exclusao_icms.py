import streamlit as st
import polars as pl
import pandas as pd
import io
from openpyxl import load_workbook


def exclusao_icms():
    '''
    Processamento de Exclusão ICMS
    '''
    st.header("✔️ Exclusão ICMS", divider="green")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            arquivo_contribuicoes = st.file_uploader("📂 **Arquivo Contribuiçôes**", type=["xlsx", "xls"])
        with col2:
            arquivo_apuracao = st.file_uploader("📂 **Arquivo Apuração**", type=["xlsx", "xls"])
        with col3:
            arquivo_pis_cofins = st.file_uploader("📂 **Arquivo PIS/COFINS**", type=["xlsx", "xls"])

    if not (arquivo_contribuicoes and arquivo_apuracao and arquivo_pis_cofins):
        st.toast("⚠️ Por favor, carregue todos os arquivos para continuar.")
        return

    st.toast("✅ Arquivos carregados com sucesso!")

    # Leitura dos arquivos
    try:
        planilha_contribuicoes = pl.read_excel(io.BytesIO(arquivo_contribuicoes.read()))
        planilha_apuracao = pl.read_excel(io.BytesIO(arquivo_apuracao.read()))
        planilha_pis_cofins = pl.read_excel(io.BytesIO(arquivo_pis_cofins.read()))
    except Exception as e:
        st.error(f"❌ Erro ao ler os arquivos: {e}")
        return

    # Metricas
    st.divider()
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total de linhas Contribuiçôes", value=len(planilha_contribuicoes), border=True)
        with col2:
            st.metric(label="Total de linhas Apuração", value=len(planilha_apuracao), border=True)
        with col3:
            st.metric(label="Total de linhas PIS/COFINS", value=len(planilha_pis_cofins), border=True)

    # ======================== ETAPA 1 - Diferença entre Base de Cálculo e Receita Bruta ========================
    planilha_contribuicoes = planilha_contribuicoes.with_columns(
        (
            pl.col("Vlr Receita Bruta") - pl.col(
                    "Vlr Base Cálculo Contribuição Antes Ajustes")
        ).alias(
            "DIFERENÇA")
        .round(2)
    )

    # ======================== ETAPA 2 - Mapear regime por Período ========================
    mapa = planilha_apuracao.select(["Período", "Vlr Débito"])

    planilha_contribuicoes = planilha_contribuicoes.join(
        mapa,
        left_on="Período",
        right_on="Período",
        how="left"
    ).with_columns(pl.col("Vlr Débito").round(2).alias("DÉBITO ICMS"))


    # ======================== ETAPA 3 - Status Diferença e Percentual de Diferença ========================
    planilha_contribuicoes = planilha_contribuicoes.with_columns(
        pl.when(pl.col("DIFERENÇA").abs() < pl.col("DÉBITO ICMS") * 0.30)
        .then(pl.lit("CONSIDERAR"))
        .otherwise(pl.lit("NÃO CONSIDERAR"))
        .alias("status_diferenca")
    )

    planilha_contribuicoes = planilha_contribuicoes.with_columns(
        (pl.col("DIFERENÇA").abs() / pl.col("DÉBITO ICMS"))
        .alias("percentual_diferenca").round(2)
    )

    # ======= ETAPA 4 - Filtragem apenas nao considerar e considerar =======
    # planilha_contribuicoes_nao_considerar = planilha_contribuicoes.filter(
    #     pl.col("status_diferenca") == "NÃO CONSIDERAR"
    # )
    
    planilha_contribuicoes_considerar = planilha_contribuicoes.filter(
        pl.col("status_diferenca") == "CONSIDERAR"
    )


    # # ======= ETAPA 5 - Join =======
    # planilha_pis_cofins_teste = planilha_pis_cofins.join(
    #     planilha_contribuicoes_considerar.select("Período"),
    #     on="Período",
    #     how="semi"
    # )


    # ======================== ETAPA 4 - Mapear regime por Período ========================
    periodos_validos = (
        planilha_contribuicoes
        .select("Período")
        .unique()
        .to_series()
    )

    planilha_pis_cofins = planilha_pis_cofins.with_columns(
        pl.when(pl.col("Período").is_in(periodos_validos))
        .then(pl.lit("Considerar"))
        .otherwise(pl.lit("Não considerar"))
        .alias("status_periodo")
    )

    # ======================== ETAPA 5 - Exportar arquivo ========================

    # Agregação por ANO
    soma_por_periodo_ano = (
        planilha_pis_cofins
        .with_columns(pl.col("Período").dt.year().alias("Período"))
        .group_by("Período")
        .agg([
            pl.col("Vlr Diferença PIS").sum().alias("Vlr Diferença PIS - Soma"),
            pl.col("Vlr Diferença Cofins").sum().alias("Vlr Diferença Cofins - Soma")
        ])
        .sort("Período")
    )


    planilha_pis_cofins = planilha_pis_cofins.select([
        "CNPJ",
        "Período",
        "Código Participante",
        "CNPJ Participante",
        "CPF Participante",
        "Nome Participante",
        "Situação",
        "Número Documento",
        "Chave NF-e",
        "Data Documento",
        "Data Entrada/Saída",
        "Número Item",
        "Código Item",
        "Descrição Item",
        "NCM",
        "CFOP",
        "CFOP Faturamento",
        "CST PIS/Cofins",
        "Vlr Item",
        "Vlr Desconto Item",
        "Vlr Base Cálculo ICMS",
        "Alíquota ICMS",
        "Vlr ICMS",
        "Vlr ICMS e IPI C/ Pagamento PIS/Cofins",
        "Vlr Rateio Frete/Seguro/DA",
        "Valor IPI",
        "Vlr Base Cálculo PIS/Cofins",
        "Vlr Base Cálculo Recalculada",
        "Vlr Diferença Base Recalculada",
        "Vlr Base Cálculo - STF",
        "Vlr Diferença Base",
        "SELIC Acumulada",
        "Alíquota PIS",
        "Vlr PIS",
        "Vlr PIS - STF",
        "Vlr Diferença PIS",
        "Vlr SELIC S/PIS",
        "Vlr Total PIS Recuperar",
        "Alíquota Cofins",
        "Vlr Cofins",
        "Vlr Cofins - STF",
        "Vlr Diferença Cofins",
        "Vlr SELIC S/Cofins",
        "Vlr Total Cofins Recuperar",
        "Vlr Total Recuperar Atualizado"
    ])

    st.dataframe(planilha_pis_cofins)
    st.dataframe(soma_por_periodo_ano)

    # Preparar arquivo Excel em memória com duas abas: "planilha_pis_cofins" e "soma_por_periodo_ano"
    planilha_pis_cofins = planilha_pis_cofins.to_pandas()
    soma_por_periodo_ano = soma_por_periodo_ano.to_pandas()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        planilha_pis_cofins.to_excel(writer, sheet_name='planilha_pis_cofins', index=False)
        soma_por_periodo_ano.to_excel(writer, sheet_name='soma_por_periodo_ano', index=False)
    output.seek(0)


    # Botão de download
    st.download_button(
        label="📥 Baixar arquivo Exclusão ICMS",
        data=output,
        file_name="exclusao_icms.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )