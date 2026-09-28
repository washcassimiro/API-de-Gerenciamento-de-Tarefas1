from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API de Tarefas",
    description="API desenvolvida para o trabalho prático de Arquitetura e Desenvolvimento de APIs."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"mensagem": "A API de Tarefas está funcionando!"}

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------
# 1. BANCO DE DADOS E ORM (SQLAlchemy + SQLite)
# ---------------------------------------------------------
DATABASE_URL = "sqlite:///./tarefas.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TarefaModel(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    concluida = Column(Boolean, default=False)
    prioridade = Column(String, default="Média")

# Cria as tabelas no arquivo sqlite (tarefas.db)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 2. SCHEMAS E VALIDAÇÃO DE DADOS (Pydantic)
# ---------------------------------------------------------
class TarefaCreate(BaseModel):
    titulo: str = Field(..., min_length=3, description="Título da tarefa (mínimo 3 caracteres)")
    descricao: Optional[str] = Field(None, description="Descrição detalhada")
    prioridade: Optional[str] = Field("Média", description="Prioridade: Baixa, Média ou Alta")

class TarefaUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3)
    descricao: Optional[str] = None
    concluida: Optional[bool] = None
    prioridade: Optional[str] = None

class TarefaResponse(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str]
    concluida: bool
    prioridade: str

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# 3. INSTÂNCIA E CONFIGURAÇÕES DA API (FastAPI + CORS)
# ---------------------------------------------------------
app = FastAPI(
    title="API de Gerenciamento de Tarefas",
    description="API desenvolvida para o trabalho prático de Arquitetura e Desenvolvimento de APIs - UNINTER.",
    version="1.0.0"
)

# Configuração de CORS exigida no trabalho
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 4. AUTENTICAÇÃO / CONTROLE DE ACESSO (API Key)
# ---------------------------------------------------------
API_KEY_SECRET = "minha_chave_secreta_123"

def verificar_api_key(x_api_key: str = Header(..., description="Chave de autenticação no cabeçalho")):
    if x_api_key != API_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso não autorizado: API Key inválida ou ausente."
        )
    return x_api_key

# ---------------------------------------------------------
# 5. ENDPOINTS E OPERAÇÕES CRUD
# ---------------------------------------------------------

@app.get("/", summary="Rota Inicial")
def home():
    return {"status": "API rodando com sucesso!", "docs": "/docs"}

# 1. GET - Listar coleção com filtro opcional
@app.get("/tarefas", response_model=List[TarefaResponse], summary="Listar tarefas (GET)")
def listar_tarefas(concluida: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(TarefaModel)
    if concluida is not None:
        query = query.filter(TarefaModel.concluida == concluida)
    return query.all()

# 2. GET - Consultar item individual por ID
@app.get("/tarefas/{tarefa_id}", response_model=TarefaResponse, summary="Consultar tarefa por ID (GET)")
def buscar_tarefa(tarefa_id: int, db: Session = Depends(get_db)):
    tarefa = db.query(TarefaModel).filter(TarefaModel.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarefa com ID {tarefa_id} não encontrada."
        )
    return tarefa

# 3. POST - Criar novo recurso
@app.post("/tarefas", response_model=TarefaResponse, status_code=status.HTTP_201_CREATED, summary="Criar nova tarefa (POST)")
def criar_tarefa(tarefa: TarefaCreate, db: Session = Depends(get_db)):
    nova_tarefa = TarefaModel(
        titulo=tarefa.titulo,
        descricao=tarefa.descricao,
        prioridade=tarefa.prioridade
    )
    db.add(nova_tarefa)
    db.commit()
    db.refresh(nova_tarefa)
    return nova_tarefa

# 4. PUT - Atualizar recurso existente
@app.put("/tarefas/{tarefa_id}", response_model=TarefaResponse, summary="Atualizar tarefa (PUT)")
def atualizar_tarefa(tarefa_id: int, dados: TarefaUpdate, db: Session = Depends(get_db)):
    tarefa = db.query(TarefaModel).filter(TarefaModel.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarefa com ID {tarefa_id} não encontrada."
        )

    if dados.titulo is not None:
        tarefa.titulo = dados.titulo
    if dados.descricao is not None:
        tarefa.descricao = dados.descricao
    if dados.concluida is not None:
        tarefa.concluida = dados.concluida
    if dados.prioridade is not None:
        tarefa.prioridade = dados.prioridade

    db.commit()
    db.refresh(tarefa)
    return tarefa

# 5. DELETE - Excluir recurso (Endpoint Protegido por API Key)
@app.delete("/tarefas/{tarefa_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover tarefa (DELETE - Protegido)")
def excluir_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verificar_api_key)
):
    tarefa = db.query(TarefaModel).filter(TarefaModel.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarefa com ID {tarefa_id} não encontrada."
        )
    db.delete(tarefa)
    db.commit()
    return None