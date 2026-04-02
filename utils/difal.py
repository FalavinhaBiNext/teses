import streamlit as st
import polars as pl
import pandas as pd
import io
from openpyxl import load_workbook

def difal():
    '''
    Processamento de Difal
    '''
    st.header("🚚 Difal", divider="green")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            arquivo_contribuicoes = st.file_uploader("📂 **Arquivo Contribuiçôes**", type=["xlsx", "xls"])
        with col2:
            arquivo_difal = st.file_uploader("📂 **Arquivo Apuração**", type=["xlsx", "xls"])


    if not (arquivo_contribuicoes and arquivo_difal):
        st.toast("⚠️ Por favor, carregue todos os arquivos para continuar.")
        return

    st.toast("✅ Arquivos carregados com sucesso!")

    try:
        planilha_contribuicoes = pl.read_excel(io.BytesIO(arquivo_contribuicoes.read()))
        planilha_difal = pl.read_excel(io.BytesIO(arquivo_difal.read()))
    except Exception as e:
        st.error(f"❌ Erro ao ler os arquivos: {e}")
        return

    st.divider()
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total de linhas Contribuiçôes", value=len(planilha_contribuicoes), border=True)
        with col2:
            st.metric(label="Total de linhas Difal", value=len(planilha_difal), border=True)

    # Mapear regime por Período
    mapa = planilha_contribuicoes.select(["Período", "Regime Incidência Tributária"])
    planilha_difal = planilha_difal.join(
        mapa,
        left_on="Período",
        right_on="Período",
        how="left"
    )

    # Calculo CRÉDITO PIS COFINS
    planilha_difal = planilha_difal.with_columns([
        (
            pl.when(pl.col("Regime Incidência Tributária") == "2 - Cumulativo")
              .then(pl.col("Vlr Recolhimento DIFAL") * 0.0365)
              .when(pl.col("Regime Incidência Tributária") == "1 - Não-cumulativo")
              .then(pl.col("Vlr Recolhimento DIFAL") * 0.0925)
              .otherwise(None)
              .round(2)
        ).alias("CRÉDITO PIS COFINS")
    ])

    # Agregação por ANO
    soma_por_periodo_ano = (
        planilha_difal
        .with_columns(pl.col("Período").dt.year().alias("Período"))
        .group_by("Período")
        .agg([
            pl.col("Vlr Recolhimento DIFAL").sum().alias("Vlr Recolhimento DIFAL - Soma"),
            pl.col("CRÉDITO PIS COFINS").sum().alias("CRÉDITO PIS COFINS - Soma")
        ])
        .sort("Período")
    )

    # Convertendo coluna "Período" para data
    planilha_difal = planilha_difal.with_columns(
        pl.col("Período").dt.strftime("%Y-%m-%d").alias("Período")
    )

    planilha_difal = planilha_difal.select([
        "CNPJ",
        "Inscrição Estadual",
        "Período",
        "UF Apuração ICMS Diferencial Alíquota/FCP",
        "Indicador Movimento",
        "Vlr Saldo Credor Período Anterior",
        "Vlr Débito",
        "Vlr Outros Débitos",
        "Vlr Crédito",
        "Vlr Outros Créditos",
        "Vlr Saldo Devedor Antes Dedução",
        "Vlr Dedução",
        "Vlr Recolhimento DIFAL",
        "Regime Incidência Tributária",
        "CRÉDITO PIS COFINS",
        "Vlr Saldo Credor Transportar Período Seguinte",
        "Vlr Recolhido/Recolher Extra Apuração",
        "Vlr Saldo Credor Período Anterior FCP",
        "Vlr Débito FCP",
        "Vlr Outros Débitos FCP",
        "Vlr Crédito FCP",
        "Vlr Outros Créditos FCP",
        "Vlr Saldo Devedor Antes Dedução FCP",
        "Vlr Dedução FCP",
        "Vlr Recolhimento FCP",
        "Vlr Saldo Credor Transportar Período Seguinte FCP",
        "Vlr Recolhido/Recolher Extra Apuração FCP"
        ]
    )

    st.dataframe(planilha_difal)
    st.dataframe(soma_por_periodo_ano)

    # Preparar arquivo Excel em memória com duas abas: "Detalhe DIFAL" e "Resumo Anual"
    pdf_difal = planilha_difal.to_pandas()
    pdf_resumo = soma_por_periodo_ano.to_pandas()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl", mode="w") as writer:
        pdf_difal.to_excel(writer, sheet_name="Detalhe DIFAL", index=False)
        pdf_resumo.to_excel(writer, sheet_name="Resumo Anual", index=False)
    output.seek(0)

    # Botão de download
    st.download_button(
        label="📥 Baixar arquivo Difal com informações anuais",
        data=output,
        file_name="difal_anual.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
