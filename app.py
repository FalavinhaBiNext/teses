"""
Sistema Tributário - Aplicação Principal

Sistema web para processamento e análise de dados tributários,
desenvolvido com Streamlit e Polars para alta performance.

Funcionalidades:
- Processamento de planilhas de subvenções
- Cálculos de ICMS interestaduais
- Integração com banco de dados tributários
- Interface intuitiva e responsiva
"""

import streamlit as st
from datetime import datetime
from pages_.tibutario_page import pagina_principal_tributario
from utils.funcoes import validar_integridade_dados, obter_estatisticas_banco

# Constantes da aplicação
APP_TITLE = "Sistema Tributário"
# APP_ICON = "📊"
VERSION = "2.0.0"
AUTHOR = "Desenvolvimento Falavinha"

# Opções do menu principal
MENU_OPTIONS = {
    "Tributario": {
        "title": "📋 Tributário",
        "description": "Processamento de dados tributários",
        "function": pagina_principal_tributario

    },
    "Sobre": {
        "title": "ℹ️ Sobre",
        "description": "Informações sobre o sistema",
        "function": None
    },
    "Contato": {
        "title": "📞 Contato",
        "description": "Informações de contato",
        "function": None
    }
}


def configurar_pagina() -> None:
    """
    Configura as propriedades básicas da página Streamlit.
    """
    st.set_page_config(
        page_title=APP_TITLE,
        # page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': f"# {APP_TITLE}\nVersão {VERSION}\n\nSistema para análise tributária."
        }
    )

    # CSS customizado para cor de fundo do sidebar
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                background-color: #105b61;
            }
            [data-testid="stSidebar"] * {
                color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)


def exibir_sidebar() -> str:
    """
    Exibe a barra lateral com menu de navegação e informações do sistema.
    
    Returns:
        Opção selecionada pelo usuário
    """
    with st.sidebar:
        # Logo
        st.image("assets/logo_falavinha-removebg.png")
        # Cabeçalho
        # st.title(f"{APP_ICON} {APP_TITLE}")
        st.caption(f"Versão {VERSION}")
        st.markdown("---")
        
        # Menu principal
        opcao_selecionada = st.selectbox(
            "🧭 Navegação:",
            options=list(MENU_OPTIONS.keys()),
            format_func=lambda x: MENU_OPTIONS[x]["title"],
            key="menu_principal"
        )
        
        # Informações do sistema
        st.markdown("---")
        _exibir_status_sistema()
        
        # Rodapé
        st.markdown("---")
        st.caption(f"© 2025 {AUTHOR}")
        st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        return opcao_selecionada


def _exibir_status_sistema() -> None:
    """
    Exibe informações de status do sistema na sidebar.
    """
    with st.expander("🔧 Status do Sistema", expanded=False):
        # Validar integridade do banco
        if validar_integridade_dados():
            st.success("✅ Banco de dados: OK")
            
            # Exibir estatísticas
            stats = obter_estatisticas_banco()
            if stats:
                st.write("**Registros no banco:**")
                for tabela, count in stats.items():
                    st.write(f"• {tabela}: {count:,}")
        else:
            st.error("❌ Problemas no banco de dados")
            st.info("Execute o script seed.py para inicializar")


def exibir_pagina_sobre() -> None:
    """
    Exibe a página de informações sobre o sistema.
    """
    st.title("ℹ️ Sobre o Sistema Tributário")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 Objetivo
        
        O Sistema Tributário foi desenvolvido para facilitar o processamento e análise 
        de dados tributários, com foco em:
        
        - **Subvenções para Investimentos**: Cálculo automático de benefícios fiscais
        - **ICMS Interestadual**: Aplicação de alíquotas corretas por UF
        - **Análise de CST**: Classificação e processamento de códigos tributários
        
        ### 🚀 Tecnologias Utilizadas
        
        - **Streamlit**: Interface web interativa
        - **Polars**: Processamento de dados de alta performance
        - **SQLite**: Banco de dados local para informações tributárias
        - **Python**: Linguagem principal do sistema
        
        ### 📋 Funcionalidades Principais
        
        1. **Upload de Planilhas**: Suporte a arquivos Excel (.xlsx, .xls)
        2. **Filtros Avançados**: Filtros por data e outros critérios
        3. **Cálculos Automáticos**: Subvenções e diferenças de ICMS
        4. **Exportação**: Download dos resultados em CSV
        5. **Validação**: Verificação automática de dados e colunas
        """)
    
    with col2:
        st.info(f"""
        **Versão**: {VERSION}
        
        **Desenvolvido por**: {AUTHOR}
        
        **Última atualização**: {datetime.now().strftime('%d/%m/%Y')}
        """)
        
        # Estatísticas do banco
        stats = obter_estatisticas_banco()
        if stats:
            st.success("**Base de Dados**")
            for tabela, count in stats.items():
                st.metric(
                    label=tabela.replace("_", " ").title(),
                    value=f"{count:,} registros"
                )


def exibir_pagina_contato() -> None:
    """
    Exibe a página de informações de contato.
    """
    st.title("📞 Contato")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🏢 Equipe Tributária
        
        Para dúvidas, sugestões ou suporte técnico, entre em contato:
        
        **📧 E-mail**: servico.bi@falavinha.com.br
        
        **📱 Telefone**: (41) 99743-9145
        
        **🕒 Horário de Atendimento**:
        - Segunda a Quinta: 8h às 18h
        - Sexta: 8h às 17h
        """)
    
    with col2:
        st.markdown("""
        ### 🆘 Suporte Técnico
        
        **Para problemas técnicos**:
        - Verifique se o arquivo está no formato correto
        - Consulte a documentação do sistema
        - Entre em contato com a equipe de Desenvolvimento
        
        **Para dúvidas tributárias**:
        - Consulte a equipe Tributária
        - Verifique a legislação vigente
        - Solicite orientação especializada
        """)
    
    # Formulário de contato
    st.markdown("---")
    st.subheader("📝 Enviar Mensagem")
    
    with st.form("formulario_contato"):
        nome = st.text_input("Nome completo:")
        email = st.text_input("E-mail:")
        assunto = st.selectbox(
            "Assunto:",
            ["Dúvida técnica", "Sugestão", "Problema no sistema", "Outro"]
        )
        mensagem = st.text_area("Mensagem:", height=100)
        
        if st.form_submit_button("📤 Enviar Mensagem"):
            if nome and email and mensagem:
                st.success("✅ Mensagem enviada com sucesso!")
                st.info("Retornaremos o contato em até 24 horas.")
            else:
                st.error("❌ Preencha todos os campos obrigatórios.")


def main() -> None:
    """
    Função principal da aplicação.
    """
    # Configurar página
    configurar_pagina()
    
    # Exibir sidebar e obter opção selecionada
    opcao_selecionada = exibir_sidebar()
    
    # Roteamento das páginas
    opcao_config = MENU_OPTIONS[opcao_selecionada]
    
    if opcao_config["function"]:
        # Página com função específica
        opcao_config["function"]()
    elif opcao_selecionada == "Sobre":
        exibir_pagina_sobre()
    elif opcao_selecionada == "Contato":
        exibir_pagina_contato()


if __name__ == "__main__":
    main()

