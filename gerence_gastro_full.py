import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import bcrypt
import jwt
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from psycopg2.extras import RealDictCursor

SECRET = os.getenv("SECRET", "gsi_secret_2026")
DATABASE_URL = os.getenv("DATABASE_URL")

MODULOS_VALIDOS = {
    "whatsapp",
    "fiscal",
    "delivery",
    "cardapio_digital",
    "app_garcom",
    "kds_cozinha",
    "kds_bar",
    "financeiro",
    "relatorios",
    "cadastro_clientes",
    "cadastro_fornecedores",
    "cadastro_funcionarios",
    "aiqfome",
    "comer_aqui",
}

PERMISSOES_VALIDAS = {
    "frente_caixa",
    "estoque",
    "fiscal",
    "financeiro",
    "clientes",
    "fornecedores",
    "funcionarios",
    "mesas",
    "comandas",
    "pedidos",
    "kds_cozinha",
    "kds_bar",
    "delivery",
    "relatorios",
    "whatsapp",
    "aiqfome",
    "comer_aqui",
}

TIPOS_IMPRESSORA = {"cozinha", "bar", "balcao", "entrega", "fiscal"}
SETORES_IMPRESSAO = {"cozinha", "bar", "balcao", "nenhum"}


def conectar():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def utcnow():
    return datetime.now(timezone.utc)


def gerar_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


def hash_senha(texto: str) -> str:
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt()).decode()


def confere_senha(texto: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(texto.encode(), senha_hash.encode())


def gerar_codigo(prefixo: str) -> str:
    return f"{prefixo}-{uuid.uuid4().hex[:10].upper()}"


def gerar_sid() -> str:
    return uuid.uuid4().hex


def verificar_admin(token: str) -> int:
    data = decodificar_token(token)
    admin_id = data.get("admin")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Apenas admin")
    return int(admin_id)


def verificar_empresa(token: str) -> int:
    data = decodificar_token(token)
    empresa_id = data.get("empresa")
    if not empresa_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    return int(empresa_id)


def verificar_colaborador(token: str) -> int:
    data = decodificar_token(token)
    colaborador_id = data.get("colaborador")
    if not colaborador_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    return int(colaborador_id)


def obter_assinatura_empresa(empresa_id: int):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                a.id AS assinatura_id,
                a.empresa_id,
                a.plano_id,
                COALESCE(a.status, 'ativo') AS status,
                a.vencimento,
                p.nome AS plano_nome,
                p.valor
            FROM assinaturas a
            LEFT JOIN planos p ON p.id = a.plano_id
            WHERE a.empresa_id = %s
            ORDER BY a.id DESC
            LIMIT 1
            """,
            (empresa_id,),
        )
        row = cur.fetchone()
        if not row:
            return {
                "status": "ativo",
                "plano_nome": "Sem plano",
                "valor": 0,
                "vencimento": None,
            }
        return row
    finally:
        cur.close()
        conn.close()


def validar_empresa_ativa(empresa_id: int):
    assinatura = obter_assinatura_empresa(empresa_id)
    if assinatura["status"] != "ativo":
        raise HTTPException(
            status_code=403,
            detail=f"Empresa com acesso bloqueado. Status atual: {assinatura['status']}",
        )


def obter_modulos_empresa(empresa_id: int) -> set[str]:
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT modulo
            FROM modulos_empresa
            WHERE empresa_id = %s AND ativo = TRUE
            """,
            (empresa_id,),
        )
        return {row["modulo"] for row in cur.fetchall()}
    finally:
        cur.close()
        conn.close()


def obter_permissoes_colaborador(colaborador_id: int) -> dict:
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT permissoes_json
            FROM funcionarios
            WHERE id = %s
            """,
            (colaborador_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Colaborador não encontrado")
        raw = row.get("permissoes_json") or "{}"
        try:
            perms = json.loads(raw)
        except Exception:
            perms = {}
        final = {}
        for p in PERMISSOES_VALIDAS:
            final[p] = bool(perms.get(p, False))
        return final
    finally:
        cur.close()
        conn.close()


def registrar_sessao(cur, empresa_id: int, tipo: str, referencia_id: int) -> str:
    sid = gerar_sid()
    cur.execute(
        """
        INSERT INTO sessoes_ativas (
            empresa_id, tipo_usuario, referencia_id, session_id, ativa, ultimo_ping
        )
        VALUES (%s, %s, %s, %s, TRUE, NOW())
        """,
        (empresa_id, tipo, referencia_id, sid),
    )
    return sid


def contar_sessoes_ativas(cur, empresa_id: int) -> int:
    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM sessoes_ativas
        WHERE empresa_id = %s AND ativa = TRUE
        """,
        (empresa_id,),
    )
    return int(cur.fetchone()["total"])


def numero_proxima_comanda(cur, empresa_id: int) -> int:
    cur.execute(
        """
        SELECT COALESCE(MAX(numero), 0) + 1 AS proximo
        FROM comandas
        WHERE empresa_id = %s
        """,
        (empresa_id,),
    )
    return int(cur.fetchone()["proximo"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS empresas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL,
                ativa BOOLEAN DEFAULT TRUE,
                limite_terminais INTEGER NOT NULL DEFAULT 1,
                limite_impressoras INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS planos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                valor NUMERIC(10,2) NOT NULL,
                whatsapp BOOLEAN DEFAULT FALSE,
                delivery BOOLEAN DEFAULT FALSE,
                relatorios BOOLEAN DEFAULT TRUE,
                financeiro BOOLEAN DEFAULT TRUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS assinaturas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                plano_id INTEGER REFERENCES planos(id),
                status VARCHAR(30) NOT NULL DEFAULT 'ativo',
                vencimento DATE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS modulos_empresa (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                modulo VARCHAR(100) NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT FALSE,
                UNIQUE (empresa_id, modulo)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessoes_ativas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                tipo_usuario VARCHAR(30) NOT NULL,
                referencia_id INTEGER NOT NULL,
                session_id VARCHAR(80) UNIQUE NOT NULL,
                ativa BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                ultimo_ping TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS funcionarios (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                telefone VARCHAR(50) DEFAULT '',
                email VARCHAR(255) DEFAULT '',
                senha VARCHAR(255) DEFAULT '',
                cargo VARCHAR(80) NOT NULL DEFAULT 'Colaborador',
                ativo BOOLEAN DEFAULT TRUE,
                permissoes_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                telefone VARCHAR(50) DEFAULT '',
                email VARCHAR(255) DEFAULT '',
                documento VARCHAR(50) DEFAULT '',
                endereco TEXT DEFAULT '',
                observacoes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fornecedores (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                telefone VARCHAR(50) DEFAULT '',
                email VARCHAR(255) DEFAULT '',
                documento VARCHAR(50) DEFAULT '',
                observacoes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entregadores (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                telefone VARCHAR(50) DEFAULT '',
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS impressoras (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                tipo VARCHAR(30) NOT NULL,
                conexao VARCHAR(255) DEFAULT '',
                modelo VARCHAR(100) DEFAULT '',
                ativa BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                setor VARCHAR(20) NOT NULL DEFAULT 'cozinha',
                ativo BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                categoria_id INTEGER REFERENCES categorias(id),
                codigo VARCHAR(30) UNIQUE NOT NULL,
                nome VARCHAR(255) NOT NULL,
                preco NUMERIC(10,2) NOT NULL,
                estoque INTEGER NOT NULL DEFAULT 0,
                tipo VARCHAR(20) NOT NULL DEFAULT 'produto',
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                setor_impressao VARCHAR(20) NOT NULL DEFAULT 'nenhum',
                impressora_id INTEGER REFERENCES impressoras(id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mesas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                numero INTEGER NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'livre',
                qr_code TEXT DEFAULT '',
                UNIQUE (empresa_id, numero)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS comandas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                numero INTEGER NOT NULL,
                mesa_id INTEGER REFERENCES mesas(id),
                cliente_id INTEGER REFERENCES clientes(id),
                origem VARCHAR(30) NOT NULL DEFAULT 'balcao',
                status VARCHAR(30) NOT NULL DEFAULT 'aberta',
                observacoes TEXT DEFAULT '',
                valor_total NUMERIC(10,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                comanda_id INTEGER REFERENCES comandas(id) ON DELETE CASCADE,
                mesa_id INTEGER REFERENCES mesas(id),
                cliente_id INTEGER REFERENCES clientes(id),
                origem VARCHAR(30) NOT NULL DEFAULT 'balcao',
                status VARCHAR(30) NOT NULL DEFAULT 'recebido',
                observacoes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
                produto_id INTEGER NOT NULL REFERENCES produtos(id),
                nome_produto VARCHAR(255) NOT NULL,
                preco NUMERIC(10,2) NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                observacoes TEXT DEFAULT '',
                setor_impressao VARCHAR(20) NOT NULL DEFAULT 'nenhum',
                impressora_id INTEGER REFERENCES impressoras(id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracoes (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER UNIQUE NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                impressora_fiscal_id INTEGER REFERENCES impressoras(id),
                impressora_entrega_id INTEGER REFERENCES impressoras(id),
                pagamento_pix BOOLEAN DEFAULT TRUE,
                pagamento_qrcode BOOLEAN DEFAULT TRUE,
                pagamento_cartao_credito BOOLEAN DEFAULT TRUE,
                pagamento_cartao_debito BOOLEAN DEFAULT TRUE,
                pagamento_dinheiro BOOLEAN DEFAULT TRUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fila_impressao (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                impressora_id INTEGER NOT NULL REFERENCES impressoras(id),
                tipo VARCHAR(30) NOT NULL,
                conteudo TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'pendente',
                pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
                comanda_id INTEGER REFERENCES comandas(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )

        cur.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS limite_terminais INTEGER NOT NULL DEFAULT 1")
        cur.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS limite_impressoras INTEGER NOT NULL DEFAULT 0")
        cur.execute("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS setor_impressao VARCHAR(20) NOT NULL DEFAULT 'nenhum'")
        cur.execute("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS impressora_id INTEGER REFERENCES impressoras(id)")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS endereco TEXT DEFAULT ''")
        cur.execute("ALTER TABLE comandas ADD COLUMN IF NOT EXISTS valor_total NUMERIC(10,2) DEFAULT 0")
        cur.execute("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS impressora_fiscal_id INTEGER REFERENCES impressoras(id)")
        cur.execute("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS impressora_entrega_id INTEGER REFERENCES impressoras(id)")

        cur.execute("SELECT id FROM admin WHERE email = %s", ("admin@rksistemas.com",))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO admin (email, senha) VALUES (%s, %s)",
                ("admin@rksistemas.com", hash_senha("Admin@123")),
            )

        cur.execute("SELECT COUNT(*) AS total FROM planos")
        if int(cur.fetchone()["total"]) == 0:
            cur.execute(
                """
                INSERT INTO planos (nome, valor, whatsapp, delivery, relatorios, financeiro)
                VALUES
                ('Básico', 49.90, FALSE, FALSE, TRUE, TRUE),
                ('Intermediário', 79.90, TRUE, FALSE, TRUE, TRUE),
                ('Premium', 119.90, TRUE, TRUE, TRUE, TRUE)
                """
            )

        conn.commit()
    finally:
        cur.close()
        conn.close()

    yield


app = FastAPI(title="GSI Sistemas API", lifespan=lifespan)


class Login(BaseModel):
    email: EmailStr
    senha: str


class LogoutIn(BaseModel):
    token: str


class EmpresaCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class ModuloBulkUpdate(BaseModel):
    token: str
    empresa_id: int
    modulos: dict[str, bool]


class LimitesEmpresaUpdate(BaseModel):
    token: str
    empresa_id: int
    limite_terminais: int
    limite_impressoras: int


class ColaboradorCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""
    email: str = ""
    senha: str = ""
    cargo: str = "Colaborador"
    permissoes: dict[str, bool]


class ColaboradorPermissoesUpdate(BaseModel):
    token: str
    colaborador_id: int
    cargo: str
    permissoes: dict[str, bool]
    ativo: bool = True


class ImpressoraCreate(BaseModel):
    token: str
    empresa_id: int
    nome: str
    tipo: Literal["cozinha", "bar", "balcao", "entrega", "fiscal"]
    conexao: str = ""
    modelo: str = ""
    ativa: bool = True


class ProdutoCreate(BaseModel):
    token: str
    categoria_id: Optional[int] = None
    nome: str
    preco: float
    estoque: int = 0
    tipo: Literal["produto", "lanche"] = "produto"
    setor_impressao: Literal["cozinha", "bar", "balcao", "nenhum"] = "nenhum"
    impressora_id: Optional[int] = None


class ClienteCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""
    email: str = ""
    documento: str = ""
    endereco: str = ""
    observacoes: str = ""


class FornecedorCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""
    email: str = ""
    documento: str = ""
    observacoes: str = ""


class EntregadorCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""


class MesaCreate(BaseModel):
    token: str
    numero: int


class ComandaCreate(BaseModel):
    token: str
    mesa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    origem: Literal["balcao", "qr", "app_entrega", "garcom"] = "balcao"
    observacoes: str = ""


class ItemPedidoIn(BaseModel):
    produto_id: int
    quantidade: int = 1
    observacoes: str = ""


class PedidoCreate(BaseModel):
    token: str
    comanda_id: int
    itens: list[ItemPedidoIn]
    origem: Literal["balcao", "qr", "app_entrega", "garcom"] = "balcao"
    observacoes: str = ""


@app.get("/")
def home():
    return {"status": "ok", "sistema": "GSI Sistemas API"}


@app.post("/admin/login")
def login_admin(data: Login):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, senha FROM admin WHERE email = %s", (data.email,))
        admin = cur.fetchone()
        if not admin:
            raise HTTPException(status_code=401, detail="Admin não encontrado")
        if not confere_senha(data.senha, admin["senha"]):
            raise HTTPException(status_code=401, detail="Senha inválida")
        return {"token": gerar_token({"admin": int(admin["id"])})}
    finally:
        cur.close()
        conn.close()


@app.post("/empresa/logout")
def logout(data: LogoutIn):
    payload = decodificar_token(data.token)
    sid = payload.get("sid")
    if not sid:
        return {"msg": "Logout concluído"}
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE sessoes_ativas SET ativa = FALSE WHERE session_id = %s", (sid,))
        conn.commit()
        return {"msg": "Logout concluído"}
    finally:
        cur.close()
        conn.close()


@app.post("/empresa/login")
def login_empresa(data: Login):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, senha, nome, limite_terminais
            FROM empresas
            WHERE email = %s
            """,
            (data.email,),
        )
        empresa = cur.fetchone()
        if not empresa:
            raise HTTPException(status_code=401, detail="Empresa não encontrada")
        if not confere_senha(data.senha, empresa["senha"]):
            raise HTTPException(status_code=401, detail="Senha inválida")

        empresa_id = int(empresa["id"])
        validar_empresa_ativa(empresa_id)

        ativos = contar_sessoes_ativas(cur, empresa_id)
        if ativos >= int(empresa["limite_terminais"]):
            raise HTTPException(status_code=403, detail="Logins excedidos")

        sid = registrar_sessao(cur, empresa_id, "empresa", empresa_id)
        conn.commit()

        return {
            "token": gerar_token({"empresa": empresa_id, "sid": sid}),
            "nome": empresa["nome"],
            "cargo": "Administrador do Estabelecimento",
        }
    finally:
        cur.close()
        conn.close()


@app.post("/colaborador/login")
def login_colaborador(data: Login):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, empresa_id, nome, cargo, senha, ativo
            FROM funcionarios
            WHERE email = %s
            """,
            (data.email,),
        )
        col = cur.fetchone()
        if not col:
            raise HTTPException(status_code=401, detail="Colaborador não encontrado")
        if not col["ativo"]:
            raise HTTPException(status_code=403, detail="Colaborador inativo")
        if not col["senha"]:
            raise HTTPException(status_code=401, detail="Colaborador sem senha")
        if not confere_senha(data.senha, col["senha"]):
            raise HTTPException(status_code=401, detail="Senha inválida")

        empresa_id = int(col["empresa_id"])
        validar_empresa_ativa(empresa_id)

        cur.execute("SELECT limite_terminais FROM empresas WHERE id = %s", (empresa_id,))
        limite = int(cur.fetchone()["limite_terminais"])
        ativos = contar_sessoes_ativas(cur, empresa_id)
        if ativos >= limite:
            raise HTTPException(status_code=403, detail="Logins excedidos")

        sid = registrar_sessao(cur, empresa_id, "colaborador", int(col["id"]))
        conn.commit()

        return {
            "token": gerar_token({"colaborador": int(col["id"]), "empresa_id": empresa_id, "sid": sid}),
            "nome": col["nome"],
            "cargo": col["cargo"],
            "permissoes": obter_permissoes_colaborador(int(col["id"])),
        }
    finally:
        cur.close()
        conn.close()


@app.post("/admin/empresa")
def criar_empresa(token: str, data: EmpresaCreate):
    verificar_admin(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM empresas WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email já cadastrado")

        cur.execute(
            """
            INSERT INTO empresas (nome, email, senha, limite_terminais, limite_impressoras)
            VALUES (%s, %s, %s, 1, 0)
            RETURNING id
            """,
            (data.nome, data.email, hash_senha(data.senha)),
        )
        empresa_id = int(cur.fetchone()["id"])

        cur.execute("SELECT id FROM planos WHERE nome = 'Básico'")
        plano = cur.fetchone()
        plano_id = int(plano["id"]) if plano else None

        cur.execute(
            """
            INSERT INTO assinaturas (empresa_id, plano_id, status, vencimento)
            VALUES (%s, %s, 'ativo', %s)
            """,
            (empresa_id, plano_id, (utcnow() + timedelta(days=30)).date()),
        )

        cur.execute("INSERT INTO configuracoes (empresa_id) VALUES (%s)", (empresa_id,))

        for modulo in sorted(MODULOS_VALIDOS):
            cur.execute(
                """
                INSERT INTO modulos_empresa (empresa_id, modulo, ativo)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (empresa_id, modulo) DO NOTHING
                """,
                (empresa_id, modulo),
            )

        conn.commit()
        return {"msg": "Empresa criada com sucesso", "empresa_id": empresa_id}
    finally:
        cur.close()
        conn.close()


@app.get("/admin/empresas")
def listar_empresas_admin(token: str):
    verificar_admin(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                e.id,
                e.nome,
                e.email,
                e.limite_terminais,
                e.limite_impressoras,
                COALESCE(a.status, 'sem_assinatura') AS status,
                a.vencimento,
                COALESCE(p.nome, '-') AS plano_nome,
                COALESCE(p.valor, 0) AS valor
            FROM empresas e
            LEFT JOIN assinaturas a ON a.empresa_id = e.id
            LEFT JOIN planos p ON p.id = a.plano_id
            ORDER BY e.nome
            """
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/admin/empresa/limites")
def salvar_limites_empresa(data: LimitesEmpresaUpdate):
    verificar_admin(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE empresas
            SET limite_terminais = %s,
                limite_impressoras = %s
            WHERE id = %s
            """,
            (data.limite_terminais, data.limite_impressoras, data.empresa_id),
        )
        conn.commit()
        return {"msg": "Limites atualizados com sucesso"}
    finally:
        cur.close()
        conn.close()


@app.get("/admin/empresa/modulos")
def listar_modulos_empresa_admin(token: str, empresa_id: int):
    verificar_admin(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        for modulo in MODULOS_VALIDOS:
            cur.execute(
                """
                INSERT INTO modulos_empresa (empresa_id, modulo, ativo)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (empresa_id, modulo) DO NOTHING
                """,
                (empresa_id, modulo),
            )
        conn.commit()

        cur.execute(
            """
            SELECT modulo, ativo
            FROM modulos_empresa
            WHERE empresa_id = %s
            ORDER BY modulo
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/admin/empresa/modulos/salvar")
def salvar_modulos_empresa(data: ModuloBulkUpdate):
    verificar_admin(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        for modulo, ativo in data.modulos.items():
            if modulo not in MODULOS_VALIDOS:
                continue
            cur.execute(
                """
                INSERT INTO modulos_empresa (empresa_id, modulo, ativo)
                VALUES (%s, %s, %s)
                ON CONFLICT (empresa_id, modulo)
                DO UPDATE SET ativo = EXCLUDED.ativo
                """,
                (data.empresa_id, modulo, bool(ativo)),
            )
        conn.commit()
        return {"msg": "Módulos atualizados com sucesso"}
    finally:
        cur.close()
        conn.close()


@app.get("/empresa/plano")
def plano_da_empresa(token: str):
    empresa_id = verificar_empresa(token)
    assinatura = obter_assinatura_empresa(empresa_id)
    assinatura["modulos_ativos"] = sorted(list(obter_modulos_empresa(empresa_id)))
    return assinatura


@app.post("/colaboradores")
def criar_colaborador(data: ColaboradorCreate):
    empresa_id = verificar_empresa(data.token)
    permissoes_filtradas = {p: bool(data.permissoes.get(p, False)) for p in PERMISSOES_VALIDAS}

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO funcionarios (
                empresa_id, nome, telefone, email, senha, cargo, ativo, permissoes_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
            RETURNING id
            """,
            (
                empresa_id,
                data.nome,
                data.telefone,
                data.email,
                hash_senha(data.senha) if data.senha else "",
                data.cargo,
                json.dumps(permissoes_filtradas),
            ),
        )
        colaborador_id = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Colaborador cadastrado", "id": colaborador_id}
    finally:
        cur.close()
        conn.close()


@app.get("/colaboradores")
def listar_colaboradores(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, nome, telefone, email, cargo, ativo, permissoes_json
            FROM funcionarios
            WHERE empresa_id = %s
            ORDER BY nome
            """,
            (empresa_id,),
        )
        rows = cur.fetchall()
        for row in rows:
            try:
                row["permissoes"] = json.loads(row.get("permissoes_json") or "{}")
            except Exception:
                row["permissoes"] = {}
        return rows
    finally:
        cur.close()
        conn.close()


@app.post("/colaboradores/permissoes/salvar")
def salvar_permissoes_colaborador(data: ColaboradorPermissoesUpdate):
    empresa_id = verificar_empresa(data.token)
    permissoes_filtradas = {p: bool(data.permissoes.get(p, False)) for p in PERMISSOES_VALIDAS}
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE funcionarios
            SET cargo = %s,
                ativo = %s,
                permissoes_json = %s
            WHERE id = %s AND empresa_id = %s
            """,
            (
                data.cargo,
                data.ativo,
                json.dumps(permissoes_filtradas),
                data.colaborador_id,
                empresa_id,
            ),
        )
        conn.commit()
        return {"msg": "Permissões do colaborador atualizadas"}
    finally:
        cur.close()
        conn.close()


@app.post("/admin/impressoras")
def criar_impressora(data: ImpressoraCreate):
    verificar_admin(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        if data.tipo not in TIPOS_IMPRESSORA:
            raise HTTPException(status_code=400, detail="Tipo de impressora inválido")

        cur.execute(
            "SELECT limite_impressoras FROM empresas WHERE id = %s",
            (data.empresa_id,),
        )
        emp = cur.fetchone()
        if not emp:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        cur.execute(
            "SELECT COUNT(*) AS total FROM impressoras WHERE empresa_id = %s",
            (data.empresa_id,),
        )
        total = int(cur.fetchone()["total"])
        if total >= int(emp["limite_impressoras"]):
            raise HTTPException(status_code=403, detail="Limite de impressoras atingido")

        cur.execute(
            """
            INSERT INTO impressoras (empresa_id, nome, tipo, conexao, modelo, ativa)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (data.empresa_id, data.nome, data.tipo, data.conexao, data.modelo, data.ativa),
        )
        iid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Impressora cadastrada", "id": iid}
    finally:
        cur.close()
        conn.close()


@app.get("/admin/impressoras")
def listar_impressoras_admin(token: str, empresa_id: int):
    verificar_admin(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, nome, tipo, conexao, modelo, ativa
            FROM impressoras
            WHERE empresa_id = %s
            ORDER BY nome
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/clientes")
def criar_cliente(data: ClienteCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO clientes (empresa_id, nome, telefone, email, documento, endereco, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                empresa_id,
                data.nome,
                data.telefone,
                data.email,
                data.documento,
                data.endereco,
                data.observacoes,
            ),
        )
        cid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Cliente cadastrado", "id": cid}
    finally:
        cur.close()
        conn.close()


@app.get("/clientes")
def listar_clientes(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, nome, telefone, email, documento, endereco, observacoes
            FROM clientes
            WHERE empresa_id = %s
            ORDER BY nome
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/fornecedores")
def criar_fornecedor(data: FornecedorCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO fornecedores (empresa_id, nome, telefone, email, documento, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                empresa_id,
                data.nome,
                data.telefone,
                data.email,
                data.documento,
                data.observacoes,
            ),
        )
        fid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Fornecedor cadastrado", "id": fid}
    finally:
        cur.close()
        conn.close()


@app.get("/fornecedores")
def listar_fornecedores(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, nome, telefone, email, documento, observacoes
            FROM fornecedores
            WHERE empresa_id = %s
            ORDER BY nome
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/entregadores")
def criar_entregador(data: EntregadorCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO entregadores (empresa_id, nome, telefone)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (empresa_id, data.nome, data.telefone),
        )
        eid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Entregador cadastrado", "id": eid}
    finally:
        cur.close()
        conn.close()


@app.get("/entregadores")
def listar_entregadores(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, nome, telefone, ativo
            FROM entregadores
            WHERE empresa_id = %s
            ORDER BY nome
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/produto")
def criar_produto(data: ProdutoCreate):
    empresa_id = verificar_empresa(data.token)
    if data.setor_impressao not in SETORES_IMPRESSAO:
        raise HTTPException(status_code=400, detail="Setor de impressão inválido")

    conn = conectar()
    cur = conn.cursor()
    try:
        if data.impressora_id:
            cur.execute(
                "SELECT id FROM impressoras WHERE id = %s AND empresa_id = %s",
                (data.impressora_id, empresa_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Impressora não encontrada")

        codigo = gerar_codigo("P")
        cur.execute(
            """
            INSERT INTO produtos (
                empresa_id, categoria_id, codigo, nome, preco, estoque, tipo, setor_impressao, impressora_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                empresa_id,
                data.categoria_id,
                codigo,
                data.nome,
                data.preco,
                data.estoque,
                data.tipo,
                data.setor_impressao,
                data.impressora_id,
            ),
        )
        pid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Produto cadastrado", "id": pid, "codigo": codigo}
    finally:
        cur.close()
        conn.close()


@app.get("/produtos")
def listar_produtos(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                p.id, p.codigo, p.nome, p.preco, p.estoque, p.tipo, p.ativo,
                p.setor_impressao, p.impressora_id,
                i.nome AS impressora_nome
            FROM produtos p
            LEFT JOIN impressoras i ON i.id = p.impressora_id
            WHERE p.empresa_id = %s
            ORDER BY p.nome
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/mesas")
def criar_mesa(data: MesaCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        qr_code = gerar_codigo("MESA")
        cur.execute(
            """
            INSERT INTO mesas (empresa_id, numero, status, qr_code)
            VALUES (%s, %s, 'livre', %s)
            RETURNING id
            """,
            (empresa_id, data.numero, qr_code),
        )
        mid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Mesa criada", "id": mid}
    finally:
        cur.close()
        conn.close()


@app.get("/mesas")
def listar_mesas(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, numero, status, qr_code
            FROM mesas
            WHERE empresa_id = %s
            ORDER BY numero
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/comandas")
def criar_comanda(data: ComandaCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        numero = numero_proxima_comanda(cur, empresa_id)

        if data.mesa_id:
            cur.execute(
                "UPDATE mesas SET status = 'ocupada' WHERE id = %s AND empresa_id = %s",
                (data.mesa_id, empresa_id),
            )

        cur.execute(
            """
            INSERT INTO comandas (empresa_id, numero, mesa_id, cliente_id, origem, status, observacoes)
            VALUES (%s, %s, %s, %s, %s, 'aberta', %s)
            RETURNING id
            """,
            (
                empresa_id,
                numero,
                data.mesa_id,
                data.cliente_id,
                data.origem,
                data.observacoes,
            ),
        )
        comanda_id = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Comanda criada", "id": comanda_id, "numero": numero}
    finally:
        cur.close()
        conn.close()