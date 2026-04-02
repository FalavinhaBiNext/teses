import polars as pl
from utils.funcoes_pis_cofins import (
    remover_termos_descricao_conta_societario,
)

df_teste = pl.DataFrame({
    "Descrição Conta Societária": [        
        "(-) CREDITO COFINS LUCRO REAL",
        "(-) CREDITO ICMS",
        "(-) DEVOLUCAO DE COMPRAS - COMERCIO",
        "BENS DE PEQUENO VALOR - DESP ADM",
        "BONIFICACAO E BRINDES - COMERCIO",
        "BRINDES - DESP ADM",
        "COFINS SOBRE COMPRAS - COMERCIO",
        "COFINS SOBRE COMPRAS - INDUSTRIA",
        "COFINS SOBRE VENDAS E SERVICOS",
        "DESCONTOS CONCEDIDOS",
        "DESCONTOS INCONDICIONAIS",
        "DESCONTOS OBTIDOS",
        "FERIAS - DESP ADM",
        "FGTS - DESP ADM",
        "ICMS",
        "ICMS DIFAL - DESPESAS",
        "ICMS SOBRE COMPRAS - COMERCIO",
        "ICMS SOBRE COMPRAS - INDUSTRIA",
        "ICMS SOBRE VENDAS",
        "ICMS SUBST TRIBUTARIA S/VENDAS",
        "ICMS-ST - DESPESAS",
        "IMPOSTOS SOBRE COMPRAS - COMERCIO",
        "INSS - DESP ADM",
        "IOF",
        "IPI - DESPESA",
        "IPI SOBRE COMPRAS - COMERCIO",
        "IPI SOBRE COMPRAS - INDUSTRIA",
        "IPI SOBRE VENDAS E SERVICOS",
        "IR S/ APLIC FINANCEIRA",
        "ISS",
        "JUROS PAGOS",
        "LOCACAO DE BENS MOVEIS - DESP ADM",
        "MULTA POR INFRACAO DE TRANSITO",
        "MULTA RESCISORIA FGTS - DESP ADM",
        "MULTAS E JUROS S/ TRIBUTOS",
        "PIS SOBRE COMPRAS - COMERCIO",
        "PIS SOBRE COMPRAS - INDUSTRIA",
        "PIS SOBRE VENDAS E SERVICOS",
        "PRO-LABORE - DESP ADM",
        "PROVISAO P/ IRPJ",
        "REBECIMENTO DE BONIFICACAO, AMOSTRA GRATIS E BRINDES",
        "TARIFAS E TAXAS BANCARIAS",
        "TAXAS E EMOLUMENTOS"
    ]
})

df_filtrado, df_removido = remover_termos_descricao_conta_societario(df_teste)
print("Filtrados",df_filtrado)
print("Removidos",df_removido)



