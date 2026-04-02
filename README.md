# 📊 Sistema Tributário

Sistema web para processamento e análise de dados tributários, desenvolvido com Streamlit e Polars para alta performance.

## 🎯 Funcionalidades

### 📋 Processamento de Subvenções
- Upload de planilhas Excel (.xlsx, .xls)
- Processamento automático de códigos CST ICMS
- Cálculo de subvenções para investimentos
- Integração com alíquotas interestaduais de ICMS

### 🔍 Análise de Dados
- Filtros avançados por data
- Validação automática de colunas
- Processamento de UF origem/destino
- Cálculos tributários automatizados

### 📊 Relatórios e Exportação
- Visualização interativa dos dados
- Download em formato CSV
- Estatísticas de processamento
- Validação de integridade dos dados

## 🚀 Tecnologias Utilizadas

- **[Streamlit](https://streamlit.io/)**: Framework web para interface interativa
- **[Polars](https://pola.rs/)**: Processamento de dados de alta performance
- **[SQLAlchemy](https://sqlalchemy.org/)**: ORM para banco de dados
- **[SQLite](https://sqlite.org/)**: Banco de dados local
- **Python 3.8+**: Linguagem principal

## 📦 Instalação

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passos de Instalação

1. **Clone ou baixe o projeto**
   ```bash
   # Se usando Git
   git clone <url-do-repositorio>
   cd sistema-tributario
   ```

2. **Crie um ambiente virtual (recomendado)**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicialize o banco de dados**
   ```bash
   python seed.py
   ```

5. **Execute a aplicação**
   ```bash
   streamlit run app.py
   ```

6. **Acesse o sistema**
   - Abra o navegador em: `http://localhost:8501`

## 📁 Estrutura do Projeto

```
sistema-tributario/
├── app.py                 # Aplicação principal
├── config.py             # Configurações do sistema
├── requirements.txt      # Dependências Python
├── README.md            # Documentação
├── seed.py              # Script de inicialização do banco
├── tributario.db        # Banco de dados SQLite (gerado)
├── models/
│   └── database.py      # Modelos do banco de dados
├── pages_/
│   └── tributario.py    # Página de processamento tributário
└── utils/
    └── funcoes.py       # Funções utilitárias
```

## 🔧 Configuração

### Banco de Dados
O sistema utiliza SQLite com as seguintes tabelas:
- **Tributacao_icms**: Códigos e descrições de tributação ICMS
- **Origem**: Códigos e descrições de origem
- **TabelaICMS**: Alíquotas interestaduais de ICMS

### Configurações Personalizáveis
Edite o arquivo `config.py` para personalizar:
- Limites de tamanho de arquivo
- Configurações de interface
- Mensagens do sistema
- Validações de dados

## 📊 Como Usar

### 1. Processamento de Subvenções

1. **Acesse a página "Tributário"**
2. **Selecione "Subvenções para Investimentos"**
3. **Faça upload da planilha Excel**
   - Deve conter as colunas: `CST ICMS`, `UF Origem/Destino`
   - Para cálculos: `Vlr Operação`, `Alíquota ICMS`, `Vlr ICMS`

4. **Configure filtros (opcional)**
   - Selecione coluna de data para filtrar período
   - Defina data inicial e final

5. **Visualize os resultados**
   - Dados processados com códigos tributários
   - Cálculos de subvenção ICMS (quando aplicável)

6. **Exporte os dados**
   - Download em formato CSV
   - Nome do arquivo inclui data de processamento

### 2. Formato da Planilha

#### Colunas Obrigatórias:
- `CST ICMS`: Código de Situação Tributária
- `UF Origem/Destino`: No formato "SP/RJ"

#### Colunas para Cálculo (opcionais):
- `Vlr Operação`: Valor da operação
- `Alíquota ICMS`: Alíquota em percentual
- `Vlr ICMS`: Valor do ICMS

#### Exemplo de Dados:
| CST ICMS | UF Origem/Destino | Vlr Operação | Alíquota ICMS | Vlr ICMS |
|----------|-------------------|--------------|---------------|----------|
| 000      | SP/RJ            | 1000.00      | 12.00         | 120.00   |
| 010      | RJ/SP            | 2000.00      | 7.00          | 140.00   |

## 🔍 Funcionalidades Avançadas

### Processamento de CST ICMS
- **Primeiro dígito**: Identifica origem da mercadoria
- **Demais dígitos**: Código de situação tributária
- **Integração automática**: Com tabelas de tributação

### Cálculo de Subvenções
```
Subvenção ICMS = (Valor Operação × Alíquota ICMS) - Valor ICMS
```

### Validações Automáticas
- Verificação de colunas obrigatórias
- Validação de formato UF (XX/XX)
- Verificação de integridade do banco
- Controle de tamanho de arquivo

## 🛠️ Desenvolvimento

### Estrutura do Código
- **Modular**: Separação clara de responsabilidades
- **Tipagem**: Type hints para melhor manutenibilidade
- **Documentação**: Docstrings em todas as funções
- **Tratamento de Erros**: Exceções capturadas e tratadas

### Boas Práticas Implementadas
- Constantes centralizadas em `config.py`
- Funções pequenas e focadas
- Validação de entrada de dados
- Mensagens de erro informativas
- Interface responsiva e intuitiva

### Adicionando Novas Funcionalidades

1. **Nova tese tributária**:
   - Adicione função em `pages_/tributario.py`
   - Atualize `OPCOES_TESES` no arquivo
   - Implemente lógica específica

2. **Nova validação**:
   - Adicione regra em `config.py`
   - Implemente validação em `utils/funcoes.py`
   - Teste com dados reais

## 🐛 Solução de Problemas

### Problemas Comuns

**Erro: "Banco de dados não encontrado"**
- Execute: `python seed.py`
- Verifique se o arquivo `tributario.db` foi criado

**Erro: "Coluna não encontrada"**
- Verifique se a planilha contém as colunas obrigatórias
- Confira a grafia exata dos nomes das colunas

**Arquivo muito grande**
- Limite atual: 500MB
- Divida o arquivo em partes menores
- Ou ajuste `FILE_CONFIG["max_size_mb"]` em `config.py`

**Performance lenta**
- Verifique a quantidade de dados
- Considere usar filtros para reduzir o dataset
- Monitore uso de memória

### Logs e Debugging
- Mensagens de erro aparecem na interface
- Verifique o console do Streamlit para logs detalhados
- Use `st.write()` para debug durante desenvolvimento

## 📈 Performance

### Otimizações Implementadas
- **Polars**: Processamento vetorizado de dados
- **Lazy Loading**: Carregamento sob demanda
- **Chunking**: Processamento em lotes
- **Cache**: Reutilização de consultas ao banco

### Limites Recomendados
- **Arquivo**: Até 500MB
- **Registros**: Até 1 milhão por processamento
- **Memória**: Monitorar uso durante operações grandes

## 🔒 Segurança

### Medidas Implementadas
- Validação de tipos de arquivo
- Sanitização de entrada de dados
- Limite de tamanho de upload
- Tratamento seguro de exceções

### Recomendações
- Execute em ambiente isolado
- Mantenha backups do banco de dados
- Monitore logs de erro
- Atualize dependências regularmente

## 📞 Suporte

### Contato
- **E-mail**: tributario@empresa.com.br
- **Telefone**: (11) 1234-5678
- **Horário**: Segunda a Sexta, 8h às 18h

### Documentação Adicional
- Consulte os comentários no código
- Verifique as docstrings das funções
- Use a página "Sobre" no sistema

## 📄 Licença

Este projeto é de uso interno da empresa. Todos os direitos reservados.

---

**Versão**: 2.0.0  
**Última atualização**: Setembro 2025  
**Desenvolvido por**: Equipe Tributária