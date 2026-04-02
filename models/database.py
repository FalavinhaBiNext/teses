from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker

# Conexão com o banco (usando SQLite)
engine = create_engine("sqlite:///tributario.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Modelo de dados: aliqotas por UF
class aliquotasUF(Base):
    __tablename__ = "Aliquotas_UF"
    id = Column(Integer, primary_key=True, index=True)
    sigla = Column(String(2), nullable=False)
    aliquota_antiga = Column(Float, nullable=False)
    aliquota_nova = Column(Float, nullable=False)
    data_vigencia = Column(Date, nullable=True)  # Data de vigência da alíquota

# Modelo de dados: origem
class Origem(Base):
    __tablename__ = "origem"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(Integer, nullable=False)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=False)

# Modelo de dados: tributação ICMS
class TributacaoICMS(Base):
    __tablename__ = "Tributacao_icms"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(Integer, nullable=False)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=False)

# Modelo de dados: tributação ISS
class TabelaICMS(Base):
    __tablename__ = "Tabela_ICMS"
    id = Column(Integer, primary_key=True, index=True)
    origem = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    aliquota = Column(Float, nullable=False)
    data_vigencia = Column(Date, nullable=True)  # Data de vigência da alíquota
    aliquota_antiga = Column(Float, nullable=True)

class TabelaCFOP(Base):
    __tablename__ = "Tabela_CFOP"
    id = Column(Integer, primary_key=True, index=True)
    cfop = Column(String, nullable=False)
    descricao = Column(String, nullable=False)

# Cria as tabelas no banco, se ainda não existirem
Base.metadata.create_all(bind=engine)
