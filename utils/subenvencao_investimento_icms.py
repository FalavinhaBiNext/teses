import streamlit as st
import polars as pl
import pandas as pd
from tabelas import dados_aliquotas
import io
from dataclasses import dataclass


@dataclass
class Config:
    ICONES = {
        "upload": "📤",
        "processando": "⚙️",
        "sucesso": "✅",
        "erro": "❌",
        "info": "ℹ️",
        "tabela": "📋",
        "grafico": "📊",
        "download": "📥",
        "ano": "📅",
        "uf": "🗺️",
        "documento": "📄",
        "alerta": "⚠️",
        "calculo": "🧮",
        "limpar": "🗑️",
    }
    COR_PRINCIPAL = "#2E86AB"
    COR_SECUNDARIA = "#1B4965"
    COR_FUNDO_CARD = "#F8F9FA"
    COR_BORDA = "#DEE2E6"


st.set_page_config(
    page_title="Subvenções de Investimento - ICMS",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    div[data-testid="stMetric"] {
        background-color: #F8F9FA;
        border: 1px solid #DEE2E6;
        padding: 12px;
        border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] {
        color: #495057;
        font-size: 13px;
    }
    div[data-testid="stMetricValue"] {
        color: #212529;
        font-size: 20px;
        font-weight: 600;
    }
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #DEE2E6;
        border-radius: 8px;
    }
    .card-metric {
        background-color: #FFFFFF;
        border-left: 4px solid #2E86AB;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .section-header {
        color: #1B4965;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #DEE2E6;
    }
    .info-box {
        background-color: #E7F3FF;
        border: 1px solid #B6D4FE;
        padding: 12px;
        border-radius: 6px;
        color: #0C5460;
    }
    .warning-box {
        background-color: #FFF3CD;
        border: 1px solid #FFEEBA;
        padding: 12px;
        border-radius: 6px;
        color: #856404;
    }
    .error-box {
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        padding: 12px;
        border-radius: 6px;
        color: #721C24;
    }
    .success-box {
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        padding: 12px;
        border-radius: 6px;
        color: #155724;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def carregar_dados(file):
    return pl.read_excel(file, engine="calamine")


@st.cache_data(show_spinner=False)
def processar_subvencao(df, ano, uf_uf, _dados_aliquotas):
    # Inicia o modo Lazy para otimização do plano de execução
    lf = df.lazy()

    # 1. Filtros precoces AGRESSIVOS antes de qualquer transformação cara.
    # Filtra simultaneamente o CFOP e o Ano utilizando extração de string rápida,
    # eliminando linhas irrelevantes antes do parser de datas.
    lf = lf.filter(
        (pl.col("CFOP").cast(pl.Int64, strict=False) >= 5000)
        & (pl.col("Período").str.slice(-4).cast(pl.Int64, strict=False) <= ano)
    )

    # 2. Transformações Iniciais Paralelas
    lf = lf.with_columns(
        [
            pl.col("Período")
            .str.strptime(pl.Date, "%d/%m/%Y", strict=False)
            .alias("Período"),
            pl.col("Período").str.slice(-4).cast(pl.Int64, strict=False).alias("Ano"),
            pl.col("CST ICMS")
            .cast(pl.Utf8)
            .str.slice(0, 1)
            .alias("CST Primeiro Dígito"),
            pl.col("CST ICMS").cast(pl.Utf8).str.slice(1).alias("CST Resto"),
        ]
    )

    # 3. Tratamento Otimizado de CST e UF
    mapeamento_primeiro = {
        "0": "Nacional",
        "1": "Estrangeira – Importação direta",
        "2": "Estrangeira – Adquirida no mercado interno",
        "3": "Nacional",
        "4": "Nacional",
        "5": "Nacional",
        "6": "Estrangeira – Importação direta",
        "7": "Estrangeira – Adquirida no mercado interno",
        "8": "Nacional",
        "9": "Outros",
    }
    mapeamento_resto = {
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
        "90": "Outras",
    }

    # Normalizamos a string base e verificamos condições
    uf_normalizado = (
        pl.col("UF Origem/Destino").cast(pl.Utf8).str.strip_chars().fill_null("")
    )
    uf_final = (
        pl.when(
            (uf_normalizado == "")
            | uf_normalizado.str.to_uppercase().str.contains("EX")
        )
        .then(pl.lit(uf_uf))
        .otherwise(uf_normalizado)
    ).alias("UF Origem/Destino")

    lf = lf.with_columns(
        [
            pl.col("CST Primeiro Dígito")
            .replace(mapeamento_primeiro, default=pl.col("CST Primeiro Dígito"))
            .alias("CST Descrição"),
            pl.col("CST Resto")
            .replace(mapeamento_resto, default=pl.col("CST Resto"))
            .alias("CST Resto Descrição"),
            uf_final,
        ]
    )

    # Separação rápida de UFs sem ramificação condicional para estruturação (evita perda de performance do polars.Struct)
    lf = lf.with_columns(
        [
            pl.col("UF Origem/Destino")
            .str.split_exact("/", 1)
            .struct.rename_fields(["UF Origem", "UF Destino"])
            .alias("ufs")
        ]
    ).unnest("ufs")

    # Se não houver UF Destino (ex: era apenas "SP"), copiamos o Origem num fallback rápido.
    lf = lf.with_columns(
        [pl.col("UF Destino").fill_null(pl.col("UF Origem")).alias("UF Destino")]
    )

    # 4. Alíquotas (Tabela Eagerizada p/ Join Imediato)
    df_aliquotas = (
        pl.DataFrame(_dados_aliquotas)
        .with_columns(
            [
                pl.col("data_vigencia")
                .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                .alias("data_vigencia_date")
            ]
        )
        .lazy()
    )

    # Join otimizado
    lf = lf.join(
        df_aliquotas,
        left_on=["UF Origem", "UF Destino"],
        right_on=["uf_origem", "uf_destino"],
        how="left",
    )

    # 5. Seleção Condicional das Alíquotas e Cálculos Finais
    lf = lf.with_columns(
        [
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
        ]
    )

    # Drop precoce das colunas auxiliares do Join antes de criar o select final
    lf = lf.drop(
        ["aliquota_antiga", "aliquota_nova", "data_vigencia", "data_vigencia_date"]
    )

    lf = lf.with_columns(
        (
            (pl.col("Vlr Operação") * (pl.col("Alíquota ICMS Calculada") / 100)).round(
                2
            )
            - pl.col("Vlr ICMS")
        )
        .round(2)
        .fill_null(0.0)
        .alias("Diferença ICMS")
    )

    # Executa o pipeline lazy otimizado.
    return lf.collect()


def _render_section_header(icon: str, title: str):
    st.markdown(
        f"""
    <div style="
        display: flex; 
        align-items: center; 
        gap: 10px;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #DEE2E6;
    ">
        <span style="font-size: 24px;">{icon}</span>
        <h3 style="margin: 0; color: #1B4965; font-weight: 600;">{title}</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )


def _render_metric_card(label: str, value: str, icon: str = "", color: str = "#2E86AB"):
    st.markdown(
        f"""
    <div style="
        background-color: #FFFFFF;
        border-left: 4px solid {color};
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    ">
        <div style="color: #6C757D; font-size: 13px; margin-bottom: 4px;">
            {icon} {label}
        </div>
        <div style="color: #212529; font-size: 20px; font-weight: 600;">
            {value}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def _render_alert_box(message: str, alert_type: str = "info"):
    configs = {
        "info": {"bg": "#E7F3FF", "border": "#B6D4FE", "color": "#0C5460", "icon": "ℹ️"},
        "warning": {
            "bg": "#FFF3CD",
            "border": "#FFEEBA",
            "color": "#856404",
            "icon": "⚠️",
        },
        "error": {
            "bg": "#F8D7DA",
            "border": "#F5C6CB",
            "color": "#721C24",
            "icon": "❌",
        },
        "success": {
            "bg": "#D4EDDA",
            "border": "#C3E6CB",
            "color": "#155724",
            "icon": "✅",
        },
    }
    cfg = configs.get(alert_type, configs["info"])
    st.markdown(
        f"""
    <div style="
        background-color: {cfg["bg"]};
        border: 1px solid {cfg["border"]};
        padding: 12px;
        border-radius: 6px;
        color: {cfg["color"]};
        margin-bottom: 16px;
    ">
        {cfg["icon"]} {message}
    </div>
    """,
        unsafe_allow_html=True,
    )


def _format_number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _render_sidebar_filters():
    # with st.sidebar:
        st.markdown(
            """
        <div style="
            background: linear-gradient(135deg, #2E86AB 0%, #1B4965 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            color: white;
        ">
            <h2 style="margin: 0; font-size: 18px; font-weight: 600;">
                💰 Subvenções de Investimento
            </h2>
            <p style="margin: 8px 0 0 0; font-size: 12px; opacity: 0.9;">
                Cálculo de Diferença de ICMS
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("### 📋 Filtros")

        col1, col2 = st.columns(2)

        with col1:
            ano = st.selectbox(
                "Ano",
                [2026, 2025, 2024, 2023, 2022],
                index=0,
                help="Selecione o ano fiscal para análise",
                key="ano",
            )

        with col2:
            uf = st.selectbox(
                "UF",
                [
                    "SP",
                    "MG",
                "PR",
                "RS",
                "RJ",
                "SC",
                "BA",
                "CE",
                "GO",
                "MT",
                "MS",
                "PE",
                "PA",
                "AM",
                "ES",
                "PB",
                "RN",
                "AL",
                "PI",
                "MA",
                "RO",
                "TO",
                "DF",
                "SE",
                "AC",
                "AP",
                "RR",
            ],
            help="Selecione a Unidade Federativa",
            key="uf",
        )

        st.divider()

        with st.expander("ℹ️ Informações", expanded=False):
            st.markdown("""
            **CFOPs analisados:** 5xxx (saídas interestaduais)
            
            **Cálculo:** 
            (Valor Operação × Alíquota Calculada) - ICMS Documento
            
            **Alíquotas:** Selecionadas conforme Vigência e UF Origem/Destino
            """)

        return ano, uf


def _render_upload_section():
    st.markdown("### 📤 Upload do Arquivo")

    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        uploaded_file = st.file_uploader(
            "Selecione o arquivo Excel",
            type="xlsx",
            help="Arquivo deve conter dados de_SUBVENÇÃO ou Sped Fiscal",
            label_visibility="collapsed",
        )
    with col_info:
        st.markdown(
            """
        <div style="
            background-color: #F8F9FA;
            padding: 12px;
            border-radius: 6px;
            font-size: 13px;
            color: #6C757D;
        ">
            💡 <b>Dica:</b> O arquivo deve conter as colunas padrão do/sped fiscal ou nota fiscal
        </div>
        """,
            unsafe_allow_html=True,
        )

    return uploaded_file


def _render_metrics_row(df_raw):
    total_linhas = _format_number(len(df_raw))
    contagem_zeros = _format_number((df_raw["Alíquota ICMS"] == 0).sum())
    contagem_vazios = _format_number(df_raw["Alíquota ICMS"].null_count())

    c1, c2, c3 = st.columns(3)
    with c1:
        _render_metric_card("Total de Linhas", total_linhas, "📊", "#2E86AB")
    with c2:
        _render_metric_card("Alíquota Zero", contagem_zeros, "⚠️", "#FFC107")
    with c3:
        _render_metric_card("Alíquota Vazia", contagem_vazios, "❌", "#DC3545")


def _render_data_preview(df_exportacao):
    _render_section_header("📋", "Dados Detalhados")

    preview_limit = 50000
    if len(df_exportacao) > preview_limit:
        _render_alert_box(
            f"Exibindo prévia das primeiras {_format_number(preview_limit)} linhas de {_format_number(len(df_exportacao))} disponíveis.",
            "warning",
        )
        st.dataframe(df_exportacao.head(preview_limit), use_container_width=True)
    else:
        st.dataframe(df_exportacao, use_container_width=True)


def _render_pivot_table(df_final_):
    _render_section_header("📊", "Diferença de ICMS por CST e Ano")

    df_agregado = df_final_.group_by(["Ano", "CST Resto Descrição"]).agg(
        pl.count().alias("Qtd Documentos"),
        pl.col("Diferença ICMS").sum().round(2).alias("Total Diferença"),
    )

    if df_agregado.is_empty():
        _render_alert_box("Sem dados para a tabela dinâmica.", "info")
        return None, None

    df_pivot = df_agregado.pivot(
        index="CST Resto Descrição",
        columns="Ano",
        values="Total Diferença",
        aggregate_function=None,
    ).fill_null(0.0)

    anos_cols = sorted(
        [col for col in df_pivot.columns if col != "CST Resto Descrição"]
    )
    cols_ordenadas = ["CST Resto Descrição"] + anos_cols
    df_pivot = df_pivot.select(cols_ordenadas)

    df_pivot = df_pivot.with_columns(
        pl.sum_horizontal(anos_cols).round(2).alias("TOTAL")
    ).sort("TOTAL", descending=True)

    totais_por_ano = {col: [df_pivot[col].sum()] for col in anos_cols}
    linha_total = pl.DataFrame(
        {
            "CST Resto Descrição": ["TOTAL GERAL"],
            **totais_por_ano,
            "TOTAL": [df_pivot["TOTAL"].sum()],
        }
    )
    linha_total = linha_total.select(df_pivot.columns)
    df_pivot = pl.concat([df_pivot, linha_total])

    st.dataframe(
        df_pivot,
        use_container_width=True,
        hide_index=True,
        column_config={
            "TOTAL": st.column_config.NumberColumn(
                "TOTAL", format="R$ %.2f", help="Soma total por CST"
            )
        }
        if "TOTAL" in df_pivot.columns
        else {},
    )

    total_geral = df_pivot["TOTAL"].sum() if "TOTAL" in df_pivot.columns else 0
    st.markdown(
        f"""
    <div style="
        text-align: right;
        padding: 16px;
        background: linear-gradient(135deg, #2E86AB 0%, #1B4965 100%);
        border-radius: 8px;
        color: white;
        font-size: 16px;
        font-weight: 600;
        margin-top: 16px;
    ">
        💰 Total Geral: {_format_currency(total_geral)}
    </div>
    """,
        unsafe_allow_html=True,
    )

    return df_pivot, df_agregado


def _render_download_section(df_exportacao, df_pivot, df_agregado, uf, ano):
    _render_section_header("📥", "Exportação")

    with st.spinner("🔄 Gerando arquivo Excel..."):
        with io.BytesIO() as output:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_exportacao.to_pandas(use_pyarrow_extension_array=True).to_excel(
                    writer, sheet_name="Dados Detalhados", index=False
                )
                if df_pivot is not None and not df_agregado.is_empty():
                    df_pivot.to_pandas(use_pyarrow_extension_array=True).to_excel(
                        writer, sheet_name="Diferença por CST e Ano", index=False
                    )

            file_name = f"subvencoes_icms_{uf}_{ano}.xlsx"

            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                st.download_button(
                    label="⬇️ Baixar Excel",
                    data=output.getvalue(),
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )
            with col_info:
                st.markdown(
                    f"""
                <div style="
                    background-color: #D4EDDA;
                    border: 1px solid #C3E6CB;
                    padding: 12px;
                    border-radius: 6px;
                    color: #155724;
                    font-size: 13px;
                ">
                    ✅ Arquivo pronto! Clique no botão para baixar.
                </div>
                """,
                    unsafe_allow_html=True,
                )


def subvencoes_investimento_icms():
    st.markdown(
        """
    <style>
        .block-container { padding-top: 2rem; }
        div[data-testid="stExpander"] { border: 1px solid #DEE2E6; border-radius: 8px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    ano, uf = _render_sidebar_filters()
    uf_uf = f"{uf}/{uf}"

    uploaded_file = _render_upload_section()

    if uploaded_file is None:
        _render_alert_box("Aguardando upload do arquivo...", "info")
        return

    try:
        with st.spinner("⏳ Carregando arquivo..."):
            df_raw = carregar_dados(uploaded_file)

        _render_metrics_row(df_raw)

        with st.spinner("🔧 Processando dados..."):
            df_final_ = processar_subvencao(df_raw, ano, uf_uf, dados_aliquotas)

        if len(df_final_) == 0:
            _render_alert_box(
                "Nenhum dado encontrado após os filtros (CFOP >= 5000 e Ano selecionado).",
                "warning",
            )
            return

        colunas_exibidas = [
            "CNPJ",
            "Inscrição Estadual",
            "Período",
            "Tipo Operação",
            "Indicador Emitente",
            "Registro Escrituração",
            "Código Participante",
            "CNPJ/CPF Participante",
            "Nome Participante",
            "UF Origem/Destino",
            "Código Município",
            "Município",
            "Modelo",
            "Situação",
            "Série",
            "Número Documento",
            "Chave Documento Eletrônico",
            "Data Documento",
            "Data Entrada/Saída",
            "Vlr Documento",
            "Vlr Desconto",
            "Vlr Abatimento NT",
            "Vlr Mercadoria",
            "Vlr Frete",
            "Vlr Seguro",
            "Vlr Outras DA",
            "Número Item",
            "Código Item",
            "Descrição Item",
            "Tipo Item",
            "Código Barra",
            "NCM",
            "Qtde Item",
            "Unidade Medida",
            "Vlr Item",
            "Vlr Desconto Item",
            "Vlr Operação",
            "CFOP",
            "Descrição CFOP",
            "CST ICMS",
            "Vlr Base Cálculo ICMS",
            "Vlr/Percentual Redução Base Cálculo ICMS",
            "Alíquota Interna ICMS - 0200",
            "Vlr ICMS",
            "Vlr Base Cálculo ICMS ST",
            "Alíquota ICMS ST",
            "Vlr ICMS ST",
            "Vlr IPI",
            "CST Primeiro Dígito",
            "CST Descrição",
            "CST Resto",
            "CST Resto Descrição",
            "Alíquota ICMS",
            "Alíquota ICMS Calculada",
            "Diferença ICMS",
            "Ano",
            "UF Origem",
            "UF Destino",
        ]

        colunas_disponiveis = [
            col for col in colunas_exibidas if col in df_final_.columns
        ]
        df_exportacao = df_final_.select(colunas_disponiveis)

        _render_data_preview(df_exportacao)

        df_pivot, df_agregado = _render_pivot_table(df_final_)

        _render_download_section(df_exportacao, df_pivot, df_agregado, uf, ano)

        _render_alert_box(
            f"Processamento concluído com sucesso! {_format_number(len(df_exportacao))} registros analisados.",
            "success",
        )

    except Exception as e:
        _render_alert_box(f"Erro ao processar o arquivo: {str(e)}", "error")
        with st.expander("📋 Detalhes do Erro"):
            st.exception(e)


if __name__ == "__main__":
    subvencoes_investimento_icms()
