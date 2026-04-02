from pydoc import text
from numpy import divide
import streamlit as st
from utils.funcoes import (
    selecionar_arquivo, 
    split_uf_columns, 
    get_aliquotas_uf,
    get_tabela_icms,
    get_tabela_cfop,
    remover_primeiro_digito,
    manter_apenas_primeiro_digito,
    get_tributacao_icms,
    corrigindo_data

)
import polars as pl
import io
from datetime import date, datetime
from typing import Union
import pandas as pd

COLUNAS_CALCULO_ICMS = ["Vlr Operação", "aliquota", "Vlr ICMS"]
COLUNA_UF_ORIGEM_DESTINO = "UF Origem/Destino"

# Principal
def subvencoes_investimento():
    """
    Processa planilha de subvenções com dados tributários.
    """
    st.header("Subvenções para Investimentos", divider="green")

    ufs = get_aliquotas_uf()
    siglas = ["Selecione..."] + ufs['sigla'].to_list()

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            selecao_uf = st.selectbox(
                "Selecione a aliquota Exterior",
                siglas,
                index=0,
                key="aliquota_exterior",
                help="Selecione a Aliquota do Estado que irá para o Exterior"
            )

    # Filtra apenas se o usuário escolheu uma UF válida
    if selecao_uf != "Selecione...":
        linha_uf = ufs.filter(pl.col("sigla") == selecao_uf)

        # Exibe valores
        aliquota_antiga = linha_uf[0, "aliquota_antiga"]
        aliquota_nova = linha_uf[0, "aliquota_nova"]
        data_vigencia = linha_uf[0, "data_vigencia"]

        st.write(f"O estado é {selecao_uf} Aliquota Antiga: {aliquota_antiga}% | Aliquota Nova: {aliquota_nova}% Data de Vigência: {data_vigencia}")

    arquivo = selecionar_arquivo()
    
    if arquivo is None:
        return
    
    planilha = pl.read_excel(arquivo)

    try:
        with st.spinner("📊 Processando planilha..."):
            corrigindo_periodo = corrigindo_data(planilha, coluna_data="Período")
            cfop_maior_5000 = filtrar_cfop_maior_que_5000(corrigindo_periodo) #Filtando CFOP maior que 5000
            acrescentar_ex_uf_origem = corrigir_estados_vazios(cfop_maior_5000)
            separa_colunas_uf_destino_Origem = separa_colunas(acrescentar_ex_uf_origem) # uf_destino = PR uf_origem = MG
            acrescentar_icms_cfop = acrescentar_info_icms_cfop(separa_colunas_uf_destino_Origem)
            separar_cst_icms = remover_digitos_cst_icms(acrescentar_icms_cfop)
            adicionar_origem = adicionar_csm_origem(separar_cst_icms)
            acrescentar_uf_destino = corrigir_uf_destino(adicionar_origem)
            teste_aliquota = aplicando_aliquota_exterior(acrescentar_uf_destino, aliquota_nova, aliquota_antiga, data_vigencia)
            
            st.dataframe(teste_aliquota)
            # preencher_uf_vazias_EX = preencher_uf_origem_destino(adicionar_origem)
            # preencher_aliquota_ext = preencher_aliquota_exterior(preencher_uf_vazias_EX, aliquota_exterior)

            # corrigir_aliquota = corrigir_aliquota_uf(preencher_uf_vazias)
            # aliquotas_ao_cfop_maior_7000 = aplicar_aliquota_7000(corrigir_aliquota)
            # para_porcentagem = aliquota_para_porcentagem(aliquotas_ao_cfop_maior_7000)

            # para_porcentagem = aliquota_para_porcentagem(preencher_uf_vazias)


            # subvencoes = calcular_subvencoes_icms(para_porcentagem)
            # colunas_selecionadas = selecionar_colunas(preencher_aliquota_ext)

            # separar_informacaoes(planilha)

            # st.dataframe(colunas_selecionadas)

            # df_pandas = colunas_selecionadas.to_pandas()
            df_pandas = teste_aliquota.to_pandas()

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_pandas.to_excel(writer, index=False, sheet_name="Resultados")

            st.download_button(
                label="Download Resultados (Excel)",
                data=buffer.getvalue(),
                file_name="subvencoes_investimento.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Baixar todos os dados processados em formato Excel (.xlsx)",
                icon="📥",
                key="download_excel"
            )

    except Exception as e:
        st.error(f"Erro ao processar planilha: {str(e)}")

def aplicando_aliquota_exterior(
    planilha: pl.DataFrame,
    aliquota_antiga: float,
    aliquota_nova:   float,
    data_vigencia:  Union[date, None] = None
) -> pl.DataFrame:
    """
    Corrige a alíquota ICMS de transações internacionais.

    Se `data_vigencia` for fornecida (não vazia), a regra considera o período;
    caso contrário, ignora‑o.
    """

    # 1️⃣ Garante que “Periodo” esteja em Date
    # planilha = planilha.with_columns(
    #     pl.col("Período").str.strptime(pl.Date, format="%d/%m/%Y", strict=False)   # <-- aqui
    #     .alias("Período")                                       # renomeia se quiser
    # )

    # ------------------------------------------------------------------
    # 2️⃣ Constrói a expressão de comparação de período (se houver)
    # ------------------------------------------------------------------
    if data_vigencia is None or (isinstance(data_vigencia, date) and not data_vigencia.strip()):
        # Sem vigência: o filtro do período nunca será aplicado
        period_cond = pl.lit(True)          # sempre verdadeiro
    else:
        # Converte a vigência para literal Date
        date_lit = (
            pl.lit(data_vigencia)
            if isinstance(data_vigencia, (date, datetime))
            else pl.lit(str(data_vigencia)).str.strptime(format="%Y-%m-%d")
        ).cast(pl.Date)

        period_cond = pl.col("Periodo") <= date_lit

    # ------------------------------------------------------------------
    # 3️⃣ Monta a condição completa
    # ------------------------------------------------------------------
    cond_principal = (
        (pl.col("CFOP").cast(pl.Int64, strict=False) >= 7000)
        & (pl.col("Alíquota ICMS") == 0)
        & period_cond
    )

    # ------------------------------------------------------------------
    # 4️⃣ Aplica a regra
    # ------------------------------------------------------------------
    return planilha.with_columns(
        pl.when(cond_principal)
          .then(pl.lit(aliquota_antiga))
          .otherwise(pl.lit(aliquota_nova))   # <-- aqui cai a nova alíquota
          .alias("Alíquota teste")            # substitui a coluna existente
    )

def separa_colunas(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Separa a coluna "UF Origem/Destino" em UF Origem e UF Destino
    '''
    return split_uf_columns(planilha, COLUNA_UF_ORIGEM_DESTINO)

def acrescentar_info_icms_cfop(planilha: pl.DataFrame) -> pl.DataFrame:
    """
    - Carrega os select dos bancos de dados
    - cria uma nova coluna com os estados da Tabela_ICMS separados uf_origem, uf_destino e aliquota
    - cria uma nova coluna com a descrição do CFOP
    """
    # Carrega os bancos de dados
    carregar_banco_ICMS = get_tabela_icms()
    carregar_banco_CFOP = get_tabela_cfop()

    # Se a tabela de ICMS foi carregada com sucesso, faz o join
    if not carregar_banco_ICMS.is_empty():
        planilha = planilha.join(
            carregar_banco_ICMS,
            left_on=["UF_Origem", "UF_Destino"],  # Colunas da planilha original
            right_on=["origem", "destino"],       # Colunas da tabela ICMS
            how="left",  # Mantém todos os registros da planilha original
        )

    if not carregar_banco_CFOP.is_empty():
        planilha = planilha.join(
            carregar_banco_CFOP,
            left_on="CFOP",      # Coluna CFOP da planilha original
            right_on="cfop",    # Coluna CFOP da tabela auxiliar
            how="left",          # Mantém todos os registros originais
        )
        
        # Renomeia a coluna de descrição para um nome mais amigável
        if "descricao" in planilha.columns:
            planilha = planilha.rename({"descricao": "Descrição_CFOP"})
    
    return planilha

def remover_digitos_cst_icms(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Separa as informações do CST ICMS.
    - Remove o primeiro dígito do CST ICMS e Converte o CST ICMS para inteiro
    - Mantem apenas o primeiro dígito do CST ICMS e Converte o CST ICMS para inteiro
    '''
    planilha_processada = (
        planilha
        .pipe(remover_primeiro_digito, ["CST ICMS"])
        .with_columns(pl.col("CST ICMS_SEM_1_DIGITO").cast(pl.Int64, strict=False))
    )

    resultado = (
        planilha_processada
        .pipe(manter_apenas_primeiro_digito, ["CST ICMS"])
        .with_columns(pl.col("CST ICMS_APENAS_1_DIGITO").cast(pl.Int64, strict=False))
    )

    return resultado   

def adicionar_csm_origem(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Carrega a tabela tributacao icms
    - adiciona a descrição da tributação_ICMS
    '''

    carregar_banco_tributacao_icms = get_tributacao_icms()

    if not carregar_banco_tributacao_icms.is_empty():
        planilha = planilha.join(
            carregar_banco_tributacao_icms,
            left_on="CST ICMS_SEM_1_DIGITO",
            right_on="codigo",
            how="left",
        ).rename(
            {
                "nome": "DESCRIÇÃO CST ICMS",
                "descricao": "descricao_tributacao_icms",
            }
        )

    return planilha

def filtrar_cfop_maior_que_5000(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Filtra CFOP maior que 5000
    '''
    return planilha.filter(
        pl.col("CFOP").cast(pl.Int64, strict=False) >= 5000)   

def preencher_uf_origem_destino(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Preenche a coluna UF Origem/Destino com "EX/EX" quando for nulo ou vazio
    '''
    return planilha.with_columns(
        pl.when(
            pl.col("UF Origem/Destino").is_null() | (pl.col("UF Origem/Destino") == "")
        ).then(pl.lit("EX/EX"))
        .otherwise(pl.col("UF Origem/Destino"))
        .alias("UF Origem/Destino")
    )

def preencher_aliquota_exterior(planilha: pl.DataFrame, aliquota_exterior: float) -> pl.DataFrame:
    return planilha.with_columns(
        pl.when(
            pl.col("UF Origem/Destino") == "EX/EX"
        )
        .then(pl.lit(aliquota_exterior))  # valor literal da variável
        .alias("aliquota_teste")  # sobrescreve a coluna existente
    )

def corrigir_uf_destino(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Corrige a coluna UF Destino com o valor da coluna UF Origem quando for nulo ou vazio
    '''
    return planilha.with_columns(
        pl.when(
            pl.col("UF_Origem").is_not_null() & 
            (pl.col("UF_Destino").is_null() | pl.col("UF_Destino").eq(""))
        ).then(pl.col("UF_Origem"))
        .otherwise(pl.col("UF_Destino"))
        .alias("UF_Destino")
    )

def corrigir_aliquota_uf(planilha: pl.DataFrame) -> pl.DataFrame:
    return planilha.with_columns(
        pl.when(pl.col("Alíquota ICMS") == 0)
        .then(pl.col("aliquota"))  # Mantém se diferente de zero
        .otherwise(pl.col("Alíquota ICMS"))  # Usa 'aliquota' apenas se ICMS for zero
        .alias("aliquota_corrigida")
    )    

def aplicar_aliquota_7000(planilha: pl.DataFrame) -> pl.DataFrame:
    return planilha.with_columns(
        pl.when(
            pl.col("CFOP").cast(pl.Int64, strict=False) >= 7000)
        # .then(pl.lit(0.18)) # 18%
        .then(pl.lit(18)) # 18
        .otherwise(pl.col("aliquota_corrigida"))
        .alias("aliquota_corrigida")
    )

def aliquota_para_porcentagem(planilha: pl.DataFrame) -> pl.DataFrame:
    return planilha.with_columns(
        pl.col("aliquota_corrigida") / 100
    )

def calcular_subvencoes_icms(planilha: pl.DataFrame) -> pl.DataFrame:
    return planilha.with_columns([
        (
            (pl.col("Vlr Operação") * pl.col("aliquota_corrigida")) - pl.col("Vlr ICMS")
        ).round(2).alias("SUBVENÇÃO ICMS")
    ])
     
def selecionar_colunas(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Seleciona as colunas desejadas
    '''
    campos = [
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
        "Vlr Operação",
        "CFOP",
        "Descrição_CFOP",
        "CST ICMS",
        "DESCRIÇÃO CST ICMS",
        "Vlr Base Cálculo ICMS",
        "Vlr/Percentual Redução Base Cálculo ICMS",
        "Alíquota Interna ICMS - 0200",
        "aliquota",
        "Alíquota ICMS",
        "Vlr ICMS",
        "SUBVENÇÃO ICMS",
        "Vlr Base Cálculo ICMS ST",
        "aliquota_corrigida",
        "Vlr ICMS ST",
        "Vlr IPI",
        "aliquota_teste" 
    ]      

    colunas_existentes = [col for col in campos if col in planilha.columns]
     
    return planilha.select(colunas_existentes)

def corrigir_estados_vazios(planilha: pl.DataFrame) -> pl.DataFrame:
    """
    Se CFOP >= 7000 e 'UF Origem/Destino' estiver vazia/nula,
    preenche com 'EX/EX'.
    """
    cond_cfop = pl.col("CFOP").cast(pl.Int64, strict=False) >= 7000
    # Considera nulo OU string só com espaços como vazia
    cond_uf_vazia = (
        pl.col("UF Origem/Destino").is_null() |
        (
            pl.col("UF Origem/Destino")
            .cast(pl.Utf8, strict=False)
            .str.replace_all(r"^\s+|\s+$", "")  # 'strip' via regex
            == ""
        )
    )

    return planilha.with_columns(
        pl.when((cond_cfop) & (cond_uf_vazia))
        .then(pl.lit("EX/EX"))
        .otherwise(pl.col("UF Origem/Destino"))
        .alias("UF Origem/Destino")
    )
