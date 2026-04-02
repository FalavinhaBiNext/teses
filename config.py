"""
Arquivo de configuração do Sistema Tributário.

Centraliza todas as constantes, configurações e parâmetros
utilizados em todo o sistema.
"""

from datetime import date
from pathlib import Path

# ===== CONFIGURAÇÕES DA APLICAÇÃO =====
APP_CONFIG = {
    "title": "Sistema Tributário",
    "icon": "📊",
    "version": "2.0.0",
    "author": "Geovani Santos",
    "description": "Sistema para processamento e análise de dados tributários",
    "logo": "assets/logo_falavinha-removebg.png"
}

# ===== CONFIGURAÇÕES DO BANCO DE DADOS =====
DATABASE_CONFIG = {
    "path": "tributario.db",
    "timeout": 30,  # segundos
    "check_same_thread": False
}

# ===== CONFIGURAÇÕES DE ARQUIVO =====
FILE_CONFIG = {
    "supported_types": ["xlsx", "xls"],
    "max_size_mb": 500,
    "encoding": "utf-8"
}

# ===== CONFIGURAÇÕES DE DATA =====
DATE_CONFIG = {
    "default_start_date": date(2024, 1, 1),
    "date_format": "%d/%m/%Y",
    "datetime_format": "%d/%m/%Y %H:%M"
}

# ===== CONFIGURAÇÕES DE INTERFACE =====
UI_CONFIG = {
    "layout": "wide",
    "sidebar_state": "expanded",
    "max_rows_display": 100,
    "decimal_places": 2
}

# ===== NOMES DAS TABELAS DO BANCO =====
TABLE_NAMES = {
    "tributacao_icms": "Tributacao_icms",
    "origem": "Origem", 
    "tabela_icms": "TabelaICMS"
}

# ===== COLUNAS OBRIGATÓRIAS POR FUNCIONALIDADE =====
REQUIRED_COLUMNS = {
    "subvencoes": ["CST ICMS"],
    "calculo_icms": ["Vlr Operação", "Alíquota ICMS", "Vlr ICMS"],
    "uf_split": ["UF Origem/Destino"]
}

# ===== MENSAGENS DO SISTEMA =====
MESSAGES = {
    "success": {
        "file_loaded": "✅ Arquivo carregado com sucesso",
        "data_processed": "✅ Dados processados com sucesso",
        "database_ok": "✅ Banco de dados: OK"
    },
    "error": {
        "file_too_large": "❌ Arquivo muito grande. Limite máximo: {max_size}MB",
        "column_not_found": "❌ Coluna '{column}' não encontrada",
        "database_error": "❌ Erro no banco de dados: {error}",
        "processing_error": "❌ Erro no processamento: {error}"
    },
    "warning": {
        "columns_missing": "⚠️ Colunas necessárias não encontradas: {columns}",
        "invalid_format": "⚠️ Formato inválido encontrado em {count} registros",
        "database_empty": "⚠️ Tabela '{table}' está vazia"
    },
    "info": {
        "calculation_skipped": "O cálculo será ignorado. Colunas necessárias: {columns}",
        "filter_applied": "📊 Filtro aplicado: {filtered} de {total} registros ({percent:.1f}%)",
        "records_processed": "📊 Total de registros processados: {count:,}"
    }
}

# ===== CONFIGURAÇÕES DE PERFORMANCE =====
PERFORMANCE_CONFIG = {
    "chunk_size": 10000,  # Tamanho do chunk para processamento
    "max_memory_usage": 0.8,  # 80% da memória disponível
    "parallel_processing": True
}

# ===== CONFIGURAÇÕES DE LOG =====
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "sistema_tributario.log",
    "max_size_mb": 10,
    "backup_count": 5
}

# ===== VALIDAÇÕES =====
VALIDATION_RULES = {
    "uf_format": r"^[A-Z]{2}/[A-Z]{2}$",  # Formato: SP/RJ
    "cst_format": r"^\d{2,3}$",  # 2 ou 3 dígitos
    "aliquota_range": (0, 100),  # Percentual entre 0 e 100
    "valor_min": 0  # Valores não podem ser negativos
}

# ===== PATHS DO SISTEMA =====
PATHS = {
    "root": Path(__file__).parent,
    "assets": Path(__file__).parent / "assets",
    "utils": Path(__file__).parent / "utils",
    "pages": Path(__file__).parent / "pages_",
    "models": Path(__file__).parent / "models"
}

# ===== CONFIGURAÇÕES DE EXPORTAÇÃO =====
EXPORT_CONFIG = {
    "csv_separator": ",",
    "csv_encoding": "utf-8-sig",  # Para compatibilidade com Excel
    "filename_pattern": "{type}_{date}.csv",
    "include_index": False
}

# ===== MENU DE NAVEGAÇÃO =====
NAVIGATION_MENU = {
    "Tributario": {
        "title": "📋 Tributário",
        "description": "Processamento de dados tributários",
        "icon": "📋"
    },
    "Sobre": {
        "title": "ℹ️ Sobre",
        "description": "Informações sobre o sistema",
        "icon": "ℹ️"
    },
    "Contato": {
        "title": "📞 Contato", 
        "description": "Informações de contato",
        "icon": "📞"
    }
}

# ===== CONFIGURAÇÕES DE CACHE =====
CACHE_CONFIG = {
    "ttl": 3600,  # Time to live em segundos (1 hora)
    "max_entries": 100,
    "clear_on_startup": False
}