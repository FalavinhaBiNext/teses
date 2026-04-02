"""
Módulo de funções utilitárias para processamento de dados tributários.

Este módulo contém funções auxiliares para:
- Manipulação de arquivos Excel
- Processamento de strings e dígitos
- Filtros de data
- Integração com banco de dados SQLite
- Transformações de dados com Polars
"""

import streamlit as st
import polars as pl
from datetime import datetime, date
import sqlite3
from typing import Optional, List, Union
from pathlib import Path
import re


# Constantes
DB_PATH = "tributario.db"
SUPPORTED_FILE_TYPES = ["xlsx", "xls"]
DEFAULT_START_DATE = date(2024, 1, 1)

def selecionar_arquivo() -> Optional[st.runtime.uploaded_file_manager.UploadedFile]:
    """
    Interface para seleção de arquivo Excel pelo usuário.
    
    Returns:
        Arquivo carregado ou None se nenhum arquivo foi selecionado
    """
    arquivo = st.file_uploader(
        "📁 Selecione o arquivo Excel:",
        type=SUPPORTED_FILE_TYPES,
        help="Carregue sua planilha em formato Excel (.xlsx ou .xls)",
        key="file_uploader_main"
    )
    
    if arquivo:
        # Validar tamanho do arquivo (limite de 200MB)
        if arquivo.size > 200 * 1024 * 1024:
            st.error("❌ Arquivo muito grande. Limite máximo: 200MB")
            return None
        
        # st.success(f"✅ Arquivo selecionado: {arquivo.name} ({arquivo.size / 1024 / 1024:.1f} MB)")
        st.toast(f"✅ Arquivo selecionado: {arquivo.name} ({arquivo.size / 1024 / 1024:.1f} MB)")

    return arquivo

def manter_apenas_primeiro_digito(df: pl.DataFrame, colunas: List[str]) -> pl.DataFrame:
    """
    Mantém apenas o primeiro dígito das colunas especificadas.
    
    Args:
        df: DataFrame de entrada
        colunas: Lista de nomes das colunas a processar
        
    Returns:
        DataFrame com novas colunas contendo apenas o primeiro dígito
        
    Raises:
        ValueError: Se alguma coluna não existir no DataFrame
    """
    if not colunas:
        return df
    
    # Validar se todas as colunas existem
    colunas_inexistentes = [col for col in colunas if col not in df.columns]
    if colunas_inexistentes:
        raise ValueError(f"Colunas não encontradas: {', '.join(colunas_inexistentes)}")
    
    df_resultado = df
    for coluna in colunas:
        try:
            df_resultado = df_resultado.with_columns(
                pl.col(coluna)
                .cast(pl.Utf8)
                .str.slice(0, 1)
                .alias(f"{coluna}_APENAS_1_DIGITO")
            )
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar coluna '{coluna}': {str(e)}")
    
    return df_resultado

def remover_primeiro_digito(df: pl.DataFrame, colunas: List[str]) -> pl.DataFrame:
    """
    Remove o primeiro dígito das colunas especificadas.
    
    Args:
        df: DataFrame de entrada
        colunas: Lista de nomes das colunas a processar
        
    Returns:
        DataFrame com novas colunas sem o primeiro dígito
        
    Raises:
        ValueError: Se alguma coluna não existir no DataFrame
    """
    if not colunas:
        return df
    
    # Validar se todas as colunas existem
    colunas_inexistentes = [col for col in colunas if col not in df.columns]
    if colunas_inexistentes:
        raise ValueError(f"Colunas não encontradas: {', '.join(colunas_inexistentes)}")
    
    df_resultado = df
    for coluna in colunas:
        try:
            df_resultado = df_resultado.with_columns(
                pl.col(coluna)
                .cast(pl.Utf8)
                .str.slice(1)
                .alias(f"{coluna}_SEM_1_DIGITO")
            )
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar coluna '{coluna}': {str(e)}")
    
    return df_resultado

def filtrar_por_data(df: pl.DataFrame, coluna_data: str) -> pl.DataFrame:
    """
    Filtra DataFrame por intervalo de datas com interface interativa.
    
    Args:
        df: DataFrame a ser filtrado
        coluna_data: Nome da coluna contendo as datas
        
    Returns:
        DataFrame filtrado pelo intervalo de datas
    """
    if coluna_data not in df.columns:
        st.error(f"❌ Coluna '{coluna_data}' não encontrada")
        return df
    
    # Interface para seleção de datas
    col1, col2 = st.columns(2)
    
    with col1:
        data_inicio = st.date_input(
            "📅 Data início:",
            value=DEFAULT_START_DATE,
            key="data_inicio_filtro",
            help="Selecione a data inicial do período"
        )
    
    with col2:
        data_fim = st.date_input(
            "📅 Data fim:",
            value=date.today(),
            key="data_fim_filtro",
            help="Selecione a data final do período"
        )
    
    # Validar intervalo de datas
    if data_inicio > data_fim:
        st.error("❌ Data de início deve ser anterior à data fim")
        return df
    
    # Aplicar filtro
    try:
        df_filtrado = df.with_columns(
            pl.col(coluna_data).cast(pl.Date)
        ).filter(
            (pl.col(coluna_data) >= data_inicio) & 
            (pl.col(coluna_data) <= data_fim)
        )
        
        registros_originais = df.height
        registros_filtrados = df_filtrado.height
        percentual = (registros_filtrados / registros_originais * 100) if registros_originais > 0 else 0
        
        st.info(
            f"📊 Filtro aplicado: {registros_filtrados:,} de {registros_originais:,} "
            f"registros ({percentual:.1f}%)"
        )
        
        return df_filtrado
        
    except Exception as e:
        st.error(f"❌ Erro ao filtrar por data: {str(e)}")
        st.info("Verifique se a coluna contém datas válidas")
        return df

def split_uf_columns(df: pl.DataFrame, coluna_uf: str) -> pl.DataFrame:
    """
    Divide coluna UF em colunas separadas de origem e destino.
    
    Espera formato: "UF_ORIGEM/UF_DESTINO" (ex: "SP/RJ")
    
    Args:
        df: DataFrame de entrada
        coluna_uf: Nome da coluna contendo UFs no formato "origem/destino"
        
    Returns:
        DataFrame com colunas UF_Origem e UF_Destino adicionadas
    """
    if coluna_uf not in df.columns:
        st.error(f"❌ Coluna '{coluna_uf}' não encontrada")
        return df
    
    try:
        # Função para extrair UF origem de forma segura
        def extrair_uf_origem(valor):
            if valor is None or valor == "":
                return None
            partes = str(valor).split("/")
            return partes[0].strip() if len(partes) > 0 and partes[0].strip() else None
        
        # Função para extrair UF destino de forma segura
        def extrair_uf_destino(valor):
            if valor is None or valor == "":
                return None
            partes = str(valor).split("/")
            return partes[1].strip() if len(partes) > 1 and partes[1].strip() else None
        
        # Aplicar as funções de extração
        df_split = df.with_columns([
            pl.col(coluna_uf)
            .map_elements(extrair_uf_origem, return_dtype=pl.Utf8)
            .alias("UF_Origem"),
            
            pl.col(coluna_uf)
            .map_elements(extrair_uf_destino, return_dtype=pl.Utf8)
            .alias("UF_Destino")
        ])
        
        # Validar se a divisão foi bem-sucedida
        ufs_invalidas = df_split.filter(
            (pl.col("UF_Origem").is_null()) | 
            (pl.col("UF_Destino").is_null())
        ).height
        
        if ufs_invalidas > 0:
            st.toast(
                f"{ufs_invalidas} registros com formato UF inválido "
                "(esperado: 'ORIGEM/DESTINO')", icon="⚠️"
            )
            
            # Mostrar alguns exemplos de valores inválidos para debug
            exemplos_invalidos = df_split.filter(
                (pl.col("UF_Origem").is_null()) | 
                (pl.col("UF_Destino").is_null())
            ).select(coluna_uf).head(5)
            
            if not exemplos_invalidos.is_empty():
                st.toast(f"Exemplos de valores inválidos: {exemplos_invalidos[coluna_uf].to_list()}")
        
        return df_split
        
    except Exception as e:
        st.error(f"❌ Erro ao dividir coluna UF: {str(e)}")
        return df

def _executar_query_db(query: str, params: tuple = ()) -> pl.DataFrame:
    """
    Executa query no banco de dados e retorna DataFrame Polars.
    
    Args:
        query: Query SQL a ser executada
        params: Parâmetros para a query (opcional)
        
    Returns:
        DataFrame com resultados da query ou DataFrame vazio em caso de erro
    """
    try:
        # Verificar se arquivo do banco existe
        if not Path(DB_PATH).exists():
            st.error(f"❌ Banco de dados não encontrado: {DB_PATH}")
            return pl.DataFrame()
        
        with sqlite3.connect(DB_PATH) as conn:
            df = pl.read_database(query, conn)
            return df
            
    except sqlite3.Error as e:
        st.error(f"❌ Erro no banco de dados: {str(e)}")
        return pl.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro inesperado ao acessar banco: {str(e)}")
        return pl.DataFrame()

def get_aliquotas_uf() -> pl.DataFrame:
    """
    Retorna dados da tabela Aliquotas_UF.
    
    Returns:
        DataFrame com colunas 'sigla', 'aliquota_antiga', 'aliquota_nova' e 'data_vigencia'
    """
    query = "SELECT sigla, aliquota_antiga, aliquota_nova, data_vigencia FROM Aliquotas_UF ORDER BY sigla"

    return _executar_query_db(query)


def get_tributacao_data_origem() -> pl.DataFrame:
    """
    Retorna dados da tabela origem.
    
    Returns:
        DataFrame com colunas 'codigo', 'nome' e 'descricao' das origens
    """
    query = "SELECT codigo, nome, descricao FROM origem ORDER BY codigo"
    return _executar_query_db(query)

def get_tributacao_icms() -> pl.DataFrame:
    """
    Retorna dados da tabela origem.
    
    Returns:
        DataFrame com colunas 'codigo', 'nome' e 'descricao' das origens
    """
    query = "SELECT codigo, nome, descricao FROM Tributacao_icms ORDER BY codigo"
    return _executar_query_db(query)

def get_tabela_icms() -> pl.DataFrame:
    """
    Retorna dados da tabela Tabela_ICMS com alíquotas interestaduais.
    
    Returns:
        DataFrame com colunas 'origem', 'destino' e 'aliquota'
    """
    query = "SELECT origem, destino, aliquota, data_vigencia, aliquota_antiga FROM Tabela_ICMS ORDER BY origem, destino"
    df = _executar_query_db(query)
    
    # Remove duplicatas mantendo apenas a primeira ocorrência
    if not df.is_empty():
        df = df.unique(subset=["origem", "destino"], keep="first")
    
    return df

def get_tabela_cfop() -> pl.DataFrame:
    """
    Retorna dados da tabela Tabela_CFOP.

    Returns:
        DataFrame com colunas 'cfop' e 'descricao'
    """
    query = "SELECT cfop, descricao FROM Tabela_CFOP ORDER BY cfop"
    df = _executar_query_db(query)
    # Garante que a coluna 'descricao' está presente e não nula
    if not df.is_empty() and "descricao" in df.columns:
        df = df.with_columns([
            pl.col("descricao").fill_null("").alias("descricao")
        ])
    return df

def validar_integridade_dados() -> bool:
    """
    Valida a integridade dos dados no banco.
    
    Returns:
        True se todos os dados estão íntegros, False caso contrário
    """
    try:
        # Verificar se as tabelas principais existem e têm dados
        tabelas_verificar = [
            ("Tributacao_icms", "SELECT COUNT(*) as count FROM Tributacao_icms"),
            ("origem", "SELECT COUNT(*) as count FROM origem"),
            ("Tabela_ICMS", "SELECT COUNT(*) as count FROM Tabela_ICMS"),
            ("Tabela_CFOP", "SELECT COUNT(*) as count FROM Tabela_CFOP")
        ]
        
        for nome_tabela, query in tabelas_verificar:
            resultado = _executar_query_db(query)
            if resultado.is_empty() or resultado["count"][0] == 0:
                st.warning(f"⚠️ Tabela '{nome_tabela}' está vazia")
                return False
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro na validação de integridade: {str(e)}")
        return False

def obter_estatisticas_banco() -> dict:
    """
    Obtém estatísticas do banco de dados.
    
    Returns:
        Dicionário com contadores de registros por tabela
    """
    estatisticas = {}
    
    tabelas = ["Tributacao_icms", "origem", "Tabela_ICMS", "Tabela_CFOP"]
    
    for tabela in tabelas:
        try:
            query = f"SELECT COUNT(*) as count FROM {tabela}"
            resultado = _executar_query_db(query)
            estatisticas[tabela] = resultado["count"][0] if not resultado.is_empty() else 0
        except Exception:
            estatisticas[tabela] = 0
    
    return estatisticas

def remover_colunas_nulas(
    df: pl.DataFrame | pl.LazyFrame,
    log_removal: bool = True,
    source_name: str = "DataFrame"
) -> pl.DataFrame | pl.LazyFrame:
    """
    Remove colunas que são 100% nulas (todos os valores são null).

    Parâmetros
    ----------
    df : pl.DataFrame ou pl.LazyFrame
        O DataFrame ou LazyFrame a ser limpo.
    log_removal : bool
        Se True, exibe um log (ou st.write) das colunas removidas.
    source_name : str
        Nome descritivo para identificar a origem (útil em logs).

    Retorna
    -------
    pl.DataFrame ou pl.LazyFrame
        Cópia do DataFrame/LazyFrame sem as colunas totalmente nulas.
    """
    is_lazy = isinstance(df, pl.LazyFrame)
    df_eager = df.collect() if is_lazy else df

    # Caso não tenha linhas
    if df_eager.height == 0:
        if log_removal:
            st.info(f"⚠️ {source_name}: Nenhuma coluna removida — DataFrame vazio.")
        return df

    # Contar nulos por coluna
    null_counts = df_eager.null_count().row(0)
    total_rows = df_eager.height

    # Identificar colunas para remover (100% nulas)
    cols_to_remove = [
        col for col, n_nulls in zip(df_eager.columns, null_counts) if n_nulls == total_rows
    ]
    cols_to_keep = [col for col in df_eager.columns if col not in cols_to_remove]

    # Logar remoção
    if log_removal and cols_to_remove:
        st.warning(f"🧹 {source_name}: Removendo colunas nulas: {cols_to_remove}")
    elif log_removal and not cols_to_remove:
        st.toast(f"✅ {source_name}: Nenhuma coluna nula encontrada.")

    # Retornar no formato original
    result = df_eager.select(cols_to_keep)
    return result.lazy() if is_lazy else result



#======================#
# Tratamento dos Dados #
#======================#
def maisculas_acentos(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Transforma todas as letras em maiúsculas e remove acentos.

    Parâmetros
    ----------
    df : pl.DataFrame
        O DataFrame a ser processado.

    Retorna
    -------
    pl.DataFrame
        Cópia do DataFrame com todas as letras em maiúsculas e sem acentos.

    '''

    # Mapeamento de caracteres acentuados para não acentuados
    mapa_acentos = {
        "Á": "A", "À": "A", "Â": "A", "Ã": "A", "Ä": "A", "Å": "A",
        "É": "E", "È": "E", "Ê": "E", "Ë": "E",
        "Í": "I", "Ì": "I", "Î": "I", "Ï": "I",
        "Ó": "O", "Ò": "O", "Ô": "O", "Õ": "O", "Ö": "O",
        "Ú": "U", "Ù": "U", "Û": "U", "Ü": "U",
        "Ç": "C",
        "á": "A", "à": "A", "â": "A", "ã": "A", "ä": "A", "å": "A",
        "é": "E", "è": "E", "ê": "E", "ë": "E",
        "í": "I", "ì": "I", "î": "I", "ï": "I",
        "ó": "O", "ò": "O", "ô": "O", "õ": "O", "ö": "O",
        "ú": "U", "ù": "U", "û": "U", "ü": "U",
        "ç": "C"
    }

    colunas_texto = [col for col, dtype in zip(planilha.columns, planilha.dtypes) if dtype == pl.Utf8]

    exprs = [
        pl.col(col)
        .str.replace_many(list(mapa_acentos.keys()), list(mapa_acentos.values()))
        .str.to_uppercase()
        .alias(col)
        for col in colunas_texto
    ]

    return planilha.with_columns(exprs)

def corrigindo_data(
    planilha: pl.DataFrame,
    coluna_data: str,
    fmt: str = "%d/%m/%Y"
) -> pl.DataFrame:
    return planilha.with_columns(
        pl.col(coluna_data)
        .str.to_date(format=fmt, strict=False)
        .dt.to_string("%Y-%m-%d")  # 👈 força exibição sem hora
    )




def remover_linha_metadados_ecd(df: pl.DataFrame) -> pl.DataFrame:
    '''
    Remove a primeira linha do DataFrame se ela parecer ser uma linha de metadados do ECD.

    Parâmetros
    ----------
    df : pl.DataFrame
        O DataFrame a ser processado.

    Retorna
    -------
    pl.DataFrame
        Cópia do DataFrame sem a primeira linha se ela for uma linha de metadados do ECD.
    '''
    if df.height == 0:
        return df

    # pega a primeira linha e checa se "parece" linha ECD
    primeira = df.row(0)
    texto = " ".join([str(x) for x in primeira if x is not None])

    # padrão típico: [ ecd000 ] / [ ecd200, ecd350 ]
    if re.search(r"\[\s*ecd\d+", texto, flags=re.IGNORECASE):
        return df.slice(1)  # remove a 1ª linha de dados (metadados)
    return df



def filtrar_cfop_maior_que_5000(planilha: pl.DataFrame) -> pl.DataFrame:
    '''
    Filtra CFOP maior que 5000
    '''
    return planilha.filter(
        pl.col("CFOP").cast(pl.Int64, strict=False) >= 5000)