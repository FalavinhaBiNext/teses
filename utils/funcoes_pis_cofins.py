import polars as pl
import re
from typing import Tuple


def filtragem_natureza_contas(planilha: pl.DataFrame):
    '''
    Filtrando apenas Natureza Conta == 04 - CONTAS DE RESULTADO e Tipo Conta == A- ANALITICA   

    '''
    return planilha.filter(
        (pl.col("Natureza Conta") == "04 - CONTAS DE RESULTADO") &
        (pl.col("Tipo Conta") == "A - ANALITICA")
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

def maior_que_zero(planilha: pl.DataFrame) -> pl.DataFrame:
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


def remover_termos_descricao_conta_societario(planilha: pl.DataFrame) -> Tuple[pl.DataFrame, pl.DataFrame]:
    """
    Remove linhas da planilha onde a coluna 'Descrição Conta Societária'
    contém termos relacionados a impostos, despesas, multas, deduções, etc.
    """

    # 🧾 Termos relacionados a impostos e contribuições
    termos_impostos = [
        r"\bICMS\b", r"\bCOFINS\b", r"\bFGTS\b", r"\bISS\b", r"\bIR\b", 
        r"\bCSRF\b", r"\bCSLL\b", r"\bIPI\b", r"\bPIS\b", r"\bIRPJ\b", 
        r"\bINSS\b", r"\bVOFINS\b", r"\bIOF\b"
    ]

    # 🧾 Siglas com pontos (formas alternativas)
    siglas_com_pontos = [r"\bI\.O\.F\b", r"\bI\.C\.M\.S\b", r"\bF\.G\.T\.S\b"]

    # ➖ Linhas que começam com "(-)", indicando deduções/descontos explícitos
    inicio_hifen = [r"^\(-\)"]

    # 📌 Frases e categorias gerais que indicam despesas que devem ser removidas
    termos_frases = [
        r"\b13\.?\s*SALARIO\b", r"\b13O\s*SALARIOS\b", r"\b13º\s*SALARIO\b",
        r"\bBRINDES\b", r"\bABONO\b", r"\bAMOSTRAS\b", r"\bPRO[-\s]LABORE\b",
        r"\bMULTAS?\b", r"\bTRIBUTOS\b", r"\bIMPOSTOS\b", r"\bTAXAS\b", r"\bDOACOES\b",
        r"\bINDENIZACAO\b", r"\bPREVIDENCIA\s*SOCIAL\b",
        r"\bDESCONTOS\b", r"\bJUROS\b", r"\bDEVOLUCAO\b", r"\bCANTINA\b",
        r"\bGRATIFICACAO\b", r"\bBENS\b", r"\bBAIXAS\b",
        r"\bGASTOS\b", r"\bSIMPLES\s*NACIONAL\b",
        r"\bRENDIMENTO\s*COM\s*APLICACOES\b", r"\bFERIAS\b",
        r"\bSALARIOS\s*E\s*ORDENADOS\b", r"\bIMPOSTO\s*DE\s*RENDA\b"
    ]

    # 🔄 Combina todos os padrões em uma única expressão regular (case-insensitive)
    todos_os_termos = termos_impostos + siglas_com_pontos + inicio_hifen + termos_frases
    padrao_regex = "(?i)" + "|".join(todos_os_termos)

    # 🎯 Cria máscara para identificar linhas que contêm os termos
    mascara_removidos = pl.col("Descrição Conta Societária").str.contains(padrao_regex, literal=False)
    
    # 📉 DataFrame com os dados removidos (que contêm os termos)
    dados_removidos = planilha.filter(mascara_removidos)
    
    # ✅ DataFrame filtrado (sem os termos indesejados)
    dados_filtrados = planilha.filter(~mascara_removidos)
    
    return dados_filtrados, dados_removidos
