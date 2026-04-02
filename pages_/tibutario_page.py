"""
Módulo para processamento de dados tributários.

Este módulo contém funcionalidades para:
- Processamento de planilhas de subvenções
- Cálculos de ICMS
- Integração com dados tributários do banco
"""

import streamlit as st
import polars as pl 
from utils.subenvencao_investimento_icms import subvencoes_investimento_icms
from utils.pis_cofins_sobre_Insumos import pis_cofins_sobre_insumos
from utils.difal import difal
from utils.exclusao_icms import exclusao_icms

# Constantes
OPCOES_TESES = [
    "📋 Selecione uma Tese...", 
    "Subvenções para Investimentos ICMS", 
    "PIS COFINS Insumos",
    "Excl. DIFAL B.C. Pis Cofins",
    "Excl. ICMS B.C. Pis Cofins",

]

def pagina_principal_tributario() -> None:
    """
    Página principal do módulo tributário.

    Exibe interface para seleção de teses tributárias e
    direciona para o processamento correspondente.
    """
    st.title("🔍 Tributário")

    opcao_selecionada = st.selectbox(
        "Selecione uma tese tributária:",
        OPCOES_TESES,
        key="opcao_tese_select"
    )

    # Processamento da opção selecionada
    if opcao_selecionada == "Subvenções para Investimentos ICMS":
        subvencoes_investimento_icms()
    elif opcao_selecionada == "PIS COFINS Insumos":
        pis_cofins_sobre_insumos()
    elif opcao_selecionada == "Excl. DIFAL B.C. Pis Cofins":
        difal()
    elif opcao_selecionada == "Excl. ICMS B.C. Pis Cofins":
        exclusao_icms()

    elif opcao_selecionada == "📋 Selecione uma Tese...":
        st.info("👆 Por favor, escolha uma tese acima para continuar.")
    else:
        st.warning("⚠️ Opção não reconhecida. Isso não deveria acontecer.")
    
if __name__ == "__main__":  
    pagina_principal_tributario()

