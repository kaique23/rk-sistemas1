import os
import uuid
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Literal, Optional

import bcrypt
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

SECRET = os.getenv("SECRET", "rk_sistemas_secret_2026")
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
    "configuracoes",
    "whatsapp",
    "aiqfome",
    "comer_aqui",
}


def conectar():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def gerar_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET, algorithm="HS256")


def hash_senha(texto: str) -> str:
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt()).decode()


def confere_senha(texto: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(texto.encode(), senha_hash.encode())


def gerar_codigo(prefixo: str) -> str:
    return f"{prefixo}-{uuid.uuid4().hex[:10].upper()}"


def verificar_admin(token: str) -> int:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        admin_id = data.get("admin")
        if not admin_id:
            raise ValueError
        return int(admin_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Apenas admin")


def verificar_empresa(token: str) -> int:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        empresa_id = data.get("empresa")
        if not empresa_id:
            raise ValueError
        return int(empresa_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


def verificar_colaborador(token: str) -> int:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        colaborador_id = data.get("colaborador")
        if not colaborador_id:
            raise ValueError
        return int(colaborador_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Token do colaborador inválido")


def obter_modulos_empresa(empresa_id: int) -> set[str]:
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT modulo
            FROM modulos_empresa
            WHERE empresa_id = %s AND ativo = TRUE
        """, (empresa_id,))
        return {row["modulo"] for row in cur.fetchall()}
    finally:
        cur.close()
        conn.close()


def exigir_modulo(empresa_id: int, modulo: str):
    if modulo not in MODULOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Módulo inválido")
    modulos = obter_modulos_empresa(empresa_id)
    if modulo not in modulos:
        raise HTTPException(status_code=403, detail=f"Módulo '{modulo}' não ativo para esta empresa")


def obter_assinatura_empresa(empresa_id: int):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
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
        """, (empresa_id,))
        row = cur.fetchone()
        if not row:
            return {
                "status": "ativo",
                "plano_nome": "Sem plano",
                "valor": 0,
                "vencimento": None
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
            detail=f"Empresa com acesso bloqueado. Status atual: {assinatura['status']}"
        )


def obter_colaborador(colaborador_id: int):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, empresa_id, nome, cargo, email, ativo, permissoes_json
            FROM funcionarios
            WHERE id = %s
        """, (colaborador_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Colaborador não encontrado")
        return row
    finally:
        cur.close()
        conn.close()


def obter_permissoes_colaborador(colaborador_id: int) -> dict:
    row = obter_colaborador(colaborador_id)
    raw = row.get("permissoes_json") or "{}"
    try:
        perms = json.loads(raw)
    except Exception:
        perms = {}

    final = {}
    for p in PERMISSOES_VALIDAS:
        final[p] = bool(perms.get(p, False))
    return final


def exigir_permissao_colaborador(token: str, permissao: str):
    if permissao not in PERMISSOES_VALIDAS:
        raise HTTPException(status_code=400, detail="Permissão inválida")

    colaborador_id = verificar_colaborador(token)
    col = obter_colaborador(colaborador_id)

    if not col["ativo"]:
        raise HTTPException(status_code=403, detail="Colaborador inativo")

    validar_empresa_ativa(int(col["empresa_id"]))

    permissoes = obter_permissoes_colaborador(colaborador_id)
    if not permissoes.get(permissao, False):
        raise HTTPException(status_code=403, detail=f"Sem permissão: {permissao}")

    return int(col["empresa_id"])


def numero_proxima_comanda(cur, empresa_id: int) -> int:
    cur.execute("""
        SELECT COALESCE(MAX(numero), 0) + 1 AS proximo
        FROM comandas
        WHERE empresa_id = %s
    """, (empresa_id,))
    return int(cur.fetchone()["proximo"])


def semaforo_preparo(created_at: datetime, status: str) -> str:
    if status in ("pronto", "entregue", "cancelado"):
        return "ok"
    minutos = (datetime.utcnow() - created_at).total_seconds() / 60
    if minutos >= 30:
        return "atrasado"
    if minutos >= 15:
        return "atencao"
    return "normal"


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            senha VARCHAR(255) NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            senha VARCHAR(255) NOT NULL,
            ativa BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS planos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) UNIQUE NOT NULL,
            valor NUMERIC(10,2) NOT NULL,
            whatsapp BOOLEAN DEFAULT FALSE,
            delivery BOOLEAN DEFAULT FALSE,
            relatorios BOOLEAN DEFAULT TRUE,
            financeiro BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS assinaturas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            plano_id INTEGER REFERENCES planos(id),
            status VARCHAR(30) NOT NULL DEFAULT 'ativo',
            vencimento DATE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS modulos_empresa (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            modulo VARCHAR(100) NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT FALSE,
            UNIQUE (empresa_id, modulo)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            setor VARCHAR(20) NOT NULL DEFAULT 'cozinha',
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            categoria_id INTEGER REFERENCES categorias(id),
            codigo VARCHAR(30) UNIQUE NOT NULL,
            nome VARCHAR(255) NOT NULL,
            preco NUMERIC(10,2) NOT NULL,
            estoque INTEGER NOT NULL DEFAULT 0,
            tipo VARCHAR(20) NOT NULL DEFAULT 'produto',
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS adicionais (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            preco NUMERIC(10,2) NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            telefone VARCHAR(50) DEFAULT '',
            email VARCHAR(255) DEFAULT '',
            documento VARCHAR(50) DEFAULT '',
            observacoes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        cur.execute("""
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
        """)

        cur.execute("""
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
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS mesas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            numero INTEGER NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'livre',
            qr_code TEXT DEFAULT '',
            UNIQUE (empresa_id, numero)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS comandas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            numero INTEGER NOT NULL,
            mesa_id INTEGER REFERENCES mesas(id),
            cliente_id INTEGER REFERENCES clientes(id),
            origem VARCHAR(30) NOT NULL DEFAULT 'balcao',
            status VARCHAR(30) NOT NULL DEFAULT 'aberta',
            observacoes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            comanda_id INTEGER REFERENCES comandas(id) ON DELETE CASCADE,
            mesa_id INTEGER REFERENCES mesas(id),
            cliente_id INTEGER REFERENCES clientes(id),
            origem VARCHAR(30) NOT NULL DEFAULT 'balcao',
            setor VARCHAR(20) NOT NULL DEFAULT 'cozinha',
            status VARCHAR(30) NOT NULL DEFAULT 'recebido',
            observacoes TEXT DEFAULT '',
            qr_entrega TEXT DEFAULT '',
            nome_entregador VARCHAR(255) DEFAULT '',
            status_entrega VARCHAR(30) DEFAULT 'aguardando',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pedido_itens (
            id SERIAL PRIMARY KEY,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
            produto_id INTEGER NOT NULL REFERENCES produtos(id),
            nome_produto VARCHAR(255) NOT NULL,
            preco NUMERIC(10,2) NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            observacoes TEXT DEFAULT ''
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pedido_adicionais (
            id SERIAL PRIMARY KEY,
            pedido_item_id INTEGER NOT NULL REFERENCES pedido_itens(id) ON DELETE CASCADE,
            adicional_id INTEGER NOT NULL REFERENCES adicionais(id),
            nome_adicional VARCHAR(255) NOT NULL,
            preco NUMERIC(10,2) NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS entregadores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            nome VARCHAR(255) NOT NULL,
            telefone VARCHAR(50) DEFAULT '',
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS chamados_mesa (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            mesa_id INTEGER REFERENCES mesas(id),
            tipo VARCHAR(30) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'aberto',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER UNIQUE NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            whatsapp_numero TEXT DEFAULT '',
            whatsapp_token TEXT DEFAULT '',
            whatsapp_webhook TEXT DEFAULT '',
            aiqfome_token TEXT DEFAULT '',
            aiqfome_loja TEXT DEFAULT '',
            comer_aqui_token TEXT DEFAULT '',
            comer_aqui_loja TEXT DEFAULT '',
            ifood_token TEXT DEFAULT '',
            uber_token TEXT DEFAULT '',
            pagamento_pix BOOLEAN DEFAULT TRUE,
            pagamento_qrcode BOOLEAN DEFAULT TRUE,
            pagamento_cartao_credito BOOLEAN DEFAULT TRUE,
            pagamento_cartao_debito BOOLEAN DEFAULT TRUE,
            pagamento_dinheiro BOOLEAN DEFAULT TRUE,
            impressora_nome TEXT DEFAULT '',
            impressora_porta TEXT DEFAULT '',
            impressora_largura TEXT DEFAULT '80mm',
            impressora_corta_papel BOOLEAN DEFAULT TRUE
        )
        """)

        cur.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS cargo VARCHAR(80) NOT NULL DEFAULT 'Colaborador'")
        cur.execute("ALTER TABLE funcionarios ADD COLUMN IF NOT EXISTS permissoes_json TEXT DEFAULT '{}'")
        cur.execute("ALTER TABLE assinaturas ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'ativo'")
        cur.execute("ALTER TABLE assinaturas ADD COLUMN IF NOT EXISTS vencimento DATE")
        cur.execute("ALTER TABLE planos ADD COLUMN IF NOT EXISTS whatsapp BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE planos ADD COLUMN IF NOT EXISTS delivery BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE planos ADD COLUMN IF NOT EXISTS relatorios BOOLEAN DEFAULT TRUE")
        cur.execute("ALTER TABLE planos ADD COLUMN IF NOT EXISTS financeiro BOOLEAN DEFAULT TRUE")

        cur.execute("SELECT id FROM admin WHERE email = %s", ("admin@rksistemas.com",))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO admin (email, senha) VALUES (%s, %s)",
                ("admin@rksistemas.com", hash_senha("Admin@123"))
            )

        cur.execute("SELECT COUNT(*) AS total FROM planos")
        if int(cur.fetchone()["total"]) == 0:
            cur.execute("""
                INSERT INTO planos (nome, valor, whatsapp, delivery, relatorios, financeiro)
                VALUES
                ('Básico', 49.90, FALSE, FALSE, TRUE, TRUE),
                ('Intermediário', 79.90, TRUE, FALSE, TRUE, TRUE),
                ('Premium', 119.90, TRUE, TRUE, TRUE, TRUE)
            """)

        conn.commit()
    finally:
        cur.close()
        conn.close()

    yield


app = FastAPI(title="RK Sistemas Completo", lifespan=lifespan)


class Login(BaseModel):
    email: EmailStr
    senha: str


class EmpresaCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class ModuloBulkUpdate(BaseModel):
    token: str
    empresa_id: int
    modulos: dict[str, bool]


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


class CategoriaCreate(BaseModel):
    token: str
    nome: str
    setor: Literal["cozinha", "bar"]


class ProdutoCreate(BaseModel):
    token: str
    categoria_id: int
    nome: str
    preco: float
    estoque: int = 0
    tipo: Literal["produto", "lanche"] = "produto"


class ClienteCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""
    email: str = ""
    documento: str = ""
    observacoes: str = ""


class FornecedorCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""
    email: str = ""
    documento: str = ""
    observacoes: str = ""


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
    adicionais_ids: list[int] = []


class PedidoCreate(BaseModel):
    token: str
    comanda_id: int
    itens: list[ItemPedidoIn]
    origem: Literal["balcao", "qr", "app_entrega", "garcom"] = "balcao"
    observacoes: str = ""


class PedidoStatusUpdate(BaseModel):
    token: str
    status: Literal["recebido", "em_preparo", "pronto", "entregue", "cancelado"]


class EntregadorCreate(BaseModel):
    token: str
    nome: str
    telefone: str = ""


class SaidaEntregaCreate(BaseModel):
    token: str
    nome_entregador: str


class ConfiguracoesCreate(BaseModel):
    token: str
    whatsapp_numero: str = ""
    whatsapp_token: str = ""
    whatsapp_webhook: str = ""
    aiqfome_token: str = ""
    aiqfome_loja: str = ""
    comer_aqui_token: str = ""
    comer_aqui_loja: str = ""
    ifood_token: str = ""
    uber_token: str = ""
    pagamento_pix: bool = True
    pagamento_qrcode: bool = True
    pagamento_cartao_credito: bool = True
    pagamento_cartao_debito: bool = True
    pagamento_dinheiro: bool = True
    impressora_nome: str = ""
    impressora_porta: str = ""
    impressora_largura: str = "80mm"
    impressora_corta_papel: bool = True


# ROOT

@app.get("/")
def home():
    return {"status": "ok", "sistema": "RK Sistemas Completo"}


# ADMIN GLOBAL

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


@app.post("/admin/empresa")
def criar_empresa(token: str, data: EmpresaCreate):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM empresas WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email já cadastrado")

        cur.execute("""
            INSERT INTO empresas (nome, email, senha)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (data.nome, data.email, hash_senha(data.senha)))
        empresa_id = int(cur.fetchone()["id"])

        cur.execute("SELECT id FROM planos WHERE nome = 'Básico'")
        plano = cur.fetchone()
        plano_id = int(plano["id"]) if plano else None

        cur.execute("""
            INSERT INTO assinaturas (empresa_id, plano_id, status, vencimento)
            VALUES (%s, %s, 'ativo', %s)
        """, (empresa_id, plano_id, (datetime.utcnow() + timedelta(days=30)).date()))

        cur.execute("INSERT INTO configuracoes (empresa_id) VALUES (%s)", (empresa_id,))

        for modulo in sorted(MODULOS_VALIDOS):
            cur.execute("""
                INSERT INTO modulos_empresa (empresa_id, modulo, ativo)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (empresa_id, modulo) DO NOTHING
            """, (empresa_id, modulo))

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
        cur.execute("""
            SELECT
                e.id,
                e.nome,
                e.email,
                COALESCE(a.status, 'sem_assinatura') AS status,
                a.vencimento,
                COALESCE(p.nome, '-') AS plano_nome,
                COALESCE(p.valor, 0) AS valor
            FROM empresas e
            LEFT JOIN assinaturas a ON a.empresa_id = e.id
            LEFT JOIN planos p ON p.id = a.plano_id
            ORDER BY e.nome
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/planos")
def listar_planos():
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nome, valor, whatsapp, delivery, relatorios, financeiro
            FROM planos
            ORDER BY valor
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/admin/empresa/plano")
def trocar_plano_admin(token: str, empresa_id: int, plano_id: int):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM empresas WHERE id = %s", (empresa_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        cur.execute("SELECT id FROM planos WHERE id = %s", (plano_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Plano não encontrado")

        cur.execute("""
            UPDATE assinaturas
            SET plano_id = %s, vencimento = %s
            WHERE empresa_id = %s
        """, (plano_id, (datetime.utcnow() + timedelta(days=30)).date(), empresa_id))

        conn.commit()
        return {"msg": "Plano alterado com sucesso"}
    finally:
        cur.close()
        conn.close()


@app.post("/admin/empresa/status")
def alterar_status_empresa(token: str, empresa_id: int, status: str):
    verificar_admin(token)

    if status not in {"ativo", "pausado", "bloqueado", "cancelado"}:
        raise HTTPException(status_code=400, detail="Status inválido")

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE assinaturas SET status = %s WHERE empresa_id = %s", (status, empresa_id))
        conn.commit()
        return {"msg": f"Status alterado para {status}"}
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
            cur.execute("""
                INSERT INTO modulos_empresa (empresa_id, modulo, ativo)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (empresa_id, modulo) DO NOTHING
            """, (empresa_id, modulo))

        conn.commit()

        cur.execute("""
            SELECT modulo, ativo
            FROM modulos_empresa
            WHERE empresa_id = %s
            ORDER BY modulo
        """, (empresa_id,))
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
            cur.execute("""
                INSERT INTO modulos_empresa (empresa_id, modulo, ativo)
                VALUES (%s, %s, %s)
                ON CONFLICT (empresa_id, modulo)
                DO UPDATE SET ativo = EXCLUDED.ativo
            """, (data.empresa_id, modulo, bool(ativo)))

        conn.commit()
        return {"msg": "Módulos atualizados com sucesso"}
    finally:
        cur.close()
        conn.close()


# EMPRESA / COLABORADORES

@app.post("/empresa/login")
def login_empresa(data: Login):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, senha, nome FROM empresas WHERE email = %s", (data.email,))
        empresa = cur.fetchone()
        if not empresa:
            raise HTTPException(status_code=401, detail="Empresa não encontrada")
        if not confere_senha(data.senha, empresa["senha"]):
            raise HTTPException(status_code=401, detail="Senha inválida")

        validar_empresa_ativa(int(empresa["id"]))

        return {
            "token": gerar_token({"empresa": int(empresa["id"])}),
            "nome": empresa["nome"],
            "cargo": "Administrador do Estabelecimento"
        }
    finally:
        cur.close()
        conn.close()


@app.post("/colaborador/login")
def login_colaborador(data: Login):
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, empresa_id, nome, cargo, senha, ativo
            FROM funcionarios
            WHERE email = %s
        """, (data.email,))
        col = cur.fetchone()
        if not col:
            raise HTTPException(status_code=401, detail="Colaborador não encontrado")
        if not col["ativo"]:
            raise HTTPException(status_code=403, detail="Colaborador inativo")
        if not col["senha"]:
            raise HTTPException(status_code=401, detail="Colaborador sem senha")
        if not confere_senha(data.senha, col["senha"]):
            raise HTTPException(status_code=401, detail="Senha inválida")

        validar_empresa_ativa(int(col["empresa_id"]))

        return {
            "token": gerar_token({"colaborador": int(col["id"])}),
            "nome": col["nome"],
            "cargo": col["cargo"],
            "permissoes": obter_permissoes_colaborador(int(col["id"]))
        }
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
    exigir_modulo(empresa_id, "cadastro_funcionarios")

    permissoes_filtradas = {}
    for p in PERMISSOES_VALIDAS:
        permissoes_filtradas[p] = bool(data.permissoes.get(p, False))

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO funcionarios (
                empresa_id, nome, telefone, email, senha, cargo, ativo, permissoes_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
            RETURNING id
        """, (
            empresa_id,
            data.nome,
            data.telefone,
            data.email,
            hash_senha(data.senha) if data.senha else "",
            data.cargo,
            json.dumps(permissoes_filtradas)
        ))
        colaborador_id = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Colaborador cadastrado", "id": colaborador_id}
    finally:
        cur.close()
        conn.close()


@app.get("/colaboradores")
def listar_colaboradores(token: str):
    empresa_id = verificar_empresa(token)
    exigir_modulo(empresa_id, "cadastro_funcionarios")

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nome, telefone, email, cargo, ativo, permissoes_json
            FROM funcionarios
            WHERE empresa_id = %s
            ORDER BY nome
        """, (empresa_id,))
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
    exigir_modulo(empresa_id, "cadastro_funcionarios")

    permissoes_filtradas = {}
    for p in PERMISSOES_VALIDAS:
        permissoes_filtradas[p] = bool(data.permissoes.get(p, False))

    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE funcionarios
            SET cargo = %s,
                ativo = %s,
                permissoes_json = %s
            WHERE id = %s AND empresa_id = %s
        """, (
            data.cargo,
            data.ativo,
            json.dumps(permissoes_filtradas),
            data.colaborador_id,
            empresa_id
        ))
        conn.commit()
        return {"msg": "Permissões do colaborador atualizadas"}
    finally:
        cur.close()
        conn.close()


# CATEGORIAS / PRODUTOS / CADASTROS

@app.post("/categorias")
def criar_categoria(data: CategoriaCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO categorias (empresa_id, nome, setor)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (empresa_id, data.nome, data.setor))
        categoria_id = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Categoria criada", "id": categoria_id}
    finally:
        cur.close()
        conn.close()


@app.get("/categorias")
def listar_categorias(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nome, setor, ativo
            FROM categorias
            WHERE empresa_id = %s
            ORDER BY nome
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/produto")
def criar_produto(data: ProdutoCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id FROM categorias
            WHERE id = %s AND empresa_id = %s
        """, (data.categoria_id, empresa_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Categoria não encontrada")

        codigo = gerar_codigo("P")

        cur.execute("""
            INSERT INTO produtos (empresa_id, categoria_id, codigo, nome, preco, estoque, tipo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (empresa_id, data.categoria_id, codigo, data.nome, data.preco, data.estoque, data.tipo))
        conn.commit()
        return {"msg": "Item cadastrado", "codigo": codigo}
    finally:
        cur.close()
        conn.close()


@app.get("/produtos")
def listar_produtos(token: str, tipo: Literal["produto", "lanche"] = "produto"):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                p.id, p.codigo, p.nome, p.preco, p.estoque, p.tipo, p.ativo,
                c.id AS categoria_id,
                c.nome AS categoria_nome,
                c.setor
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.empresa_id = %s AND p.tipo = %s
            ORDER BY p.nome
        """, (empresa_id, tipo))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/clientes")
def criar_cliente(data: ClienteCreate):
    empresa_id = verificar_empresa(data.token)
    exigir_modulo(empresa_id, "cadastro_clientes")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO clientes (empresa_id, nome, telefone, email, documento, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (empresa_id, data.nome, data.telefone, data.email, data.documento, data.observacoes))
        cid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Cliente cadastrado", "id": cid}
    finally:
        cur.close()
        conn.close()


@app.get("/clientes")
def listar_clientes(token: str):
    empresa_id = verificar_empresa(token)
    exigir_modulo(empresa_id, "cadastro_clientes")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nome, telefone, email, documento, observacoes
            FROM clientes
            WHERE empresa_id = %s
            ORDER BY nome
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/fornecedores")
def criar_fornecedor(data: FornecedorCreate):
    empresa_id = verificar_empresa(data.token)
    exigir_modulo(empresa_id, "cadastro_fornecedores")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fornecedores (empresa_id, nome, telefone, email, documento, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (empresa_id, data.nome, data.telefone, data.email, data.documento, data.observacoes))
        fid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Fornecedor cadastrado", "id": fid}
    finally:
        cur.close()
        conn.close()


@app.get("/fornecedores")
def listar_fornecedores(token: str):
    empresa_id = verificar_empresa(token)
    exigir_modulo(empresa_id, "cadastro_fornecedores")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nome, telefone, email, documento, observacoes
            FROM fornecedores
            WHERE empresa_id = %s
            ORDER BY nome
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# MESAS / CHAMADOS

@app.post("/mesas")
def criar_mesa(data: MesaCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id FROM mesas
            WHERE empresa_id = %s AND numero = %s
        """, (empresa_id, data.numero))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Já existe uma mesa com esse número")

        qr_code = gerar_codigo("MESA")
        cur.execute("""
            INSERT INTO mesas (empresa_id, numero, status, qr_code)
            VALUES (%s, %s, 'livre', %s)
            RETURNING id
        """, (empresa_id, data.numero, qr_code))
        mesa_id = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Mesa criada", "id": mesa_id, "qr_code": qr_code}
    finally:
        cur.close()
        conn.close()


@app.get("/mesas")
def listar_mesas(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, numero, status, qr_code
            FROM mesas
            WHERE empresa_id = %s
            ORDER BY numero
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/mesas-colaborador")
def listar_mesas_colaborador(token: str):
    empresa_id = exigir_permissao_colaborador(token, "mesas")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, numero, status, qr_code
            FROM mesas
            WHERE empresa_id = %s
            ORDER BY numero
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/chamados")
def listar_chamados(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.id, c.tipo, c.status, c.created_at, m.numero AS mesa_numero
            FROM chamados_mesa c
            LEFT JOIN mesas m ON m.id = c.mesa_id
            WHERE c.empresa_id = %s
            ORDER BY c.created_at DESC
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/chamados-colaborador")
def listar_chamados_colaborador(token: str):
    empresa_id = exigir_permissao_colaborador(token, "mesas")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.id, c.tipo, c.status, c.created_at, m.numero AS mesa_numero
            FROM chamados_mesa c
            LEFT JOIN mesas m ON m.id = c.mesa_id
            WHERE c.empresa_id = %s
            ORDER BY c.created_at DESC
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# COMANDAS / PEDIDOS

@app.post("/comandas")
def criar_comanda(data: ComandaCreate):
    empresa_id = verificar_empresa(data.token)

    conn = conectar()
    cur = conn.cursor()
    try:
        numero = numero_proxima_comanda(cur, empresa_id)

        if data.mesa_id:
            cur.execute("SELECT id FROM mesas WHERE id = %s AND empresa_id = %s", (data.mesa_id, empresa_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Mesa não encontrada")
            cur.execute("UPDATE mesas SET status = 'ocupada' WHERE id = %s", (data.mesa_id,))

        if data.cliente_id:
            cur.execute("SELECT id FROM clientes WHERE id = %s AND empresa_id = %s", (data.cliente_id, empresa_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Cliente não encontrado")

        cur.execute("""
            INSERT INTO comandas (empresa_id, numero, mesa_id, cliente_id, origem, status, observacoes)
            VALUES (%s, %s, %s, %s, %s, 'aberta', %s)
            RETURNING id
        """, (empresa_id, numero, data.mesa_id, data.cliente_id, data.origem, data.observacoes))
        comanda_id = int(cur.fetchone()["id"])

        conn.commit()
        return {"msg": "Comanda criada", "id": comanda_id, "numero": numero}
    finally:
        cur.close()
        conn.close()


@app.get("/comandas")
def listar_comandas(token: str, status: Optional[str] = None):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        base = """
            SELECT c.*, m.numero AS mesa_numero, cl.nome AS cliente_nome
            FROM comandas c
            LEFT JOIN mesas m ON m.id = c.mesa_id
            LEFT JOIN clientes cl ON cl.id = c.cliente_id
            WHERE c.empresa_id = %s
        """
        params = [empresa_id]
        if status:
            base += " AND c.status = %s"
            params.append(status)
        base += " ORDER BY c.created_at DESC"
        cur.execute(base, tuple(params))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.get("/comandas-colaborador")
def listar_comandas_colaborador(token: str, status: Optional[str] = None):
    empresa_id = exigir_permissao_colaborador(token, "comandas")
    conn = conectar()
    cur = conn.cursor()
    try:
        base = """
            SELECT c.*, m.numero AS mesa_numero, cl.nome AS cliente_nome
            FROM comandas c
            LEFT JOIN mesas m ON m.id = c.mesa_id
            LEFT JOIN clientes cl ON cl.id = c.cliente_id
            WHERE c.empresa_id = %s
        """
        params = [empresa_id]
        if status:
            base += " AND c.status = %s"
            params.append(status)
        base += " ORDER BY c.created_at DESC"
        cur.execute(base, tuple(params))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/pedidos")
def criar_pedido(data: PedidoCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, mesa_id, cliente_id, status
            FROM comandas
            WHERE id = %s AND empresa_id = %s
        """, (data.comanda_id, empresa_id))
        comanda = cur.fetchone()
        if not comanda:
            raise HTTPException(status_code=404, detail="Comanda não encontrada")
        if comanda["status"] != "aberta":
            raise HTTPException(status_code=400, detail="Comanda não está aberta")
        if not data.itens:
            raise HTTPException(status_code=400, detail="Pedido sem itens")

        setores_map = {"cozinha": [], "bar": []}

        for item in data.itens:
            cur.execute("""
                SELECT p.id, p.nome, p.preco, c.setor
                FROM produtos p
                LEFT JOIN categorias c ON c.id = p.categoria_id
                WHERE p.id = %s AND p.empresa_id = %s
            """, (item.produto_id, empresa_id))
            prod = cur.fetchone()
            if not prod:
                raise HTTPException(status_code=404, detail=f"Produto {item.produto_id} não encontrado")
            setor = prod["setor"] or "cozinha"
            setores_map[setor].append(item)

        pedidos_criados = []

        for setor, itens_setor in setores_map.items():
            if not itens_setor:
                continue

            qr_entrega = gerar_codigo("ENTR") if data.origem in ("qr", "app_entrega") else ""

            cur.execute("""
                INSERT INTO pedidos (
                    empresa_id, comanda_id, mesa_id, cliente_id, origem, setor, status,
                    observacoes, qr_entrega, nome_entregador, status_entrega
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'recebido', %s, %s, '', 'aguardando')
                RETURNING id
            """, (
                empresa_id,
                data.comanda_id,
                comanda["mesa_id"],
                comanda["cliente_id"],
                data.origem,
                setor,
                data.observacoes,
                qr_entrega
            ))
            pedido_id = int(cur.fetchone()["id"])

            for item in itens_setor:
                cur.execute("""
                    SELECT id, nome, preco
                    FROM produtos
                    WHERE id = %s AND empresa_id = %s
                """, (item.produto_id, empresa_id))
                prod = cur.fetchone()

                cur.execute("""
                    INSERT INTO pedido_itens (
                        pedido_id, produto_id, nome_produto, preco, quantidade, observacoes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    pedido_id,
                    prod["id"],
                    prod["nome"],
                    prod["preco"],
                    item.quantidade,
                    item.observacoes
                ))
                pedido_item_id = int(cur.fetchone()["id"])

                cur.execute("""
                    UPDATE produtos
                    SET estoque = GREATEST(estoque - %s, 0)
                    WHERE id = %s
                """, (item.quantidade, item.produto_id))

                for adicional_id in item.adicionais_ids:
                    cur.execute("""
                        SELECT id, nome, preco
                        FROM adicionais
                        WHERE id = %s AND empresa_id = %s
                    """, (adicional_id, empresa_id))
                    add = cur.fetchone()
                    if add:
                        cur.execute("""
                            INSERT INTO pedido_adicionais (pedido_item_id, adicional_id, nome_adicional, preco)
                            VALUES (%s, %s, %s, %s)
                        """, (pedido_item_id, add["id"], add["nome"], add["preco"]))

            pedidos_criados.append({"pedido_id": pedido_id, "setor": setor, "qr_entrega": qr_entrega})

        conn.commit()
        return {"msg": "Pedidos criados", "pedidos": pedidos_criados}
    finally:
        cur.close()
        conn.close()


@app.get("/pedidos")
def listar_pedidos(token: str, status: Optional[str] = None, setor: Optional[str] = None):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        query = """
            SELECT
                p.*,
                c.numero AS comanda_numero,
                m.numero AS mesa_numero,
                cl.nome AS cliente_nome
            FROM pedidos p
            LEFT JOIN comandas c ON c.id = p.comanda_id
            LEFT JOIN mesas m ON m.id = p.mesa_id
            LEFT JOIN clientes cl ON cl.id = p.cliente_id
            WHERE p.empresa_id = %s
        """
        params = [empresa_id]

        if status:
            query += " AND p.status = %s"
            params.append(status)
        if setor:
            query += " AND p.setor = %s"
            params.append(setor)

        query += " ORDER BY p.created_at ASC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        for pedido in rows:
            created_at = pedido["created_at"]
            pedido["semaforo"] = semaforo_preparo(created_at, pedido["status"]) if isinstance(created_at, datetime) else "normal"
            pedido["minutos_aberto"] = int((datetime.utcnow() - created_at).total_seconds() / 60) if isinstance(created_at, datetime) else 0

        return rows
    finally:
        cur.close()
        conn.close()


@app.get("/pedidos-colaborador")
def listar_pedidos_colaborador(token: str, status: Optional[str] = None, setor: Optional[str] = None):
    empresa_id = exigir_permissao_colaborador(token, "pedidos")
    conn = conectar()
    cur = conn.cursor()
    try:
        query = """
            SELECT
                p.*,
                c.numero AS comanda_numero,
                m.numero AS mesa_numero,
                cl.nome AS cliente_nome
            FROM pedidos p
            LEFT JOIN comandas c ON c.id = p.comanda_id
            LEFT JOIN mesas m ON m.id = p.mesa_id
            LEFT JOIN clientes cl ON cl.id = p.cliente_id
            WHERE p.empresa_id = %s
        """
        params = [empresa_id]

        if status:
            query += " AND p.status = %s"
            params.append(status)
        if setor:
            query += " AND p.setor = %s"
            params.append(setor)

        query += " ORDER BY p.created_at ASC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        for pedido in rows:
            created_at = pedido["created_at"]
            pedido["semaforo"] = semaforo_preparo(created_at, pedido["status"]) if isinstance(created_at, datetime) else "normal"
            pedido["minutos_aberto"] = int((datetime.utcnow() - created_at).total_seconds() / 60) if isinstance(created_at, datetime) else 0

        return rows
    finally:
        cur.close()
        conn.close()


@app.get("/pedidos/{pedido_id}/itens")
def detalhes_itens_pedido(pedido_id: int, token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT empresa_id FROM pedidos WHERE id = %s", (pedido_id,))
        ped = cur.fetchone()
        if not ped or int(ped["empresa_id"]) != empresa_id:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

        cur.execute("""
            SELECT id, produto_id, nome_produto, preco, quantidade, observacoes
            FROM pedido_itens
            WHERE pedido_id = %s
            ORDER BY id
        """, (pedido_id,))
        itens = cur.fetchall()

        for item in itens:
            cur.execute("""
                SELECT nome_adicional, preco
                FROM pedido_adicionais
                WHERE pedido_item_id = %s
                ORDER BY id
            """, (item["id"],))
            item["adicionais"] = cur.fetchall()

        return itens
    finally:
        cur.close()
        conn.close()


@app.post("/pedidos/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: int, data: PedidoStatusUpdate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT empresa_id FROM pedidos WHERE id = %s", (pedido_id,))
        ped = cur.fetchone()
        if not ped or int(ped["empresa_id"]) != empresa_id:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

        cur.execute("UPDATE pedidos SET status = %s WHERE id = %s", (data.status, pedido_id))
        conn.commit()
        return {"msg": "Status atualizado com sucesso"}
    finally:
        cur.close()
        conn.close()


# KDS / DELIVERY / CONFIG

@app.get("/kds/cozinha")
def kds_cozinha(token: str):
    empresa_id = verificar_empresa(token)
    exigir_modulo(empresa_id, "kds_cozinha")
    return listar_pedidos(token, setor="cozinha")


@app.get("/kds/bar")
def kds_bar(token: str):
    empresa_id = verificar_empresa(token)
    exigir_modulo(empresa_id, "kds_bar")
    return listar_pedidos(token, setor="bar")


@app.post("/entregadores")
def criar_entregador(data: EntregadorCreate):
    empresa_id = verificar_empresa(data.token)
    exigir_modulo(empresa_id, "delivery")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO entregadores (empresa_id, nome, telefone)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (empresa_id, data.nome, data.telefone))
        eid = int(cur.fetchone()["id"])
        conn.commit()
        return {"msg": "Entregador cadastrado", "id": eid}
    finally:
        cur.close()
        conn.close()


@app.get("/entregadores")
def listar_entregadores(token: str):
    empresa_id = verificar_empresa(token)
    exigir_modulo(empresa_id, "delivery")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, nome, telefone, ativo
            FROM entregadores
            WHERE empresa_id = %s
            ORDER BY nome
        """, (empresa_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@app.post("/pedidos/{pedido_id}/sair-entrega")
def sair_para_entrega(pedido_id: int, data: SaidaEntregaCreate):
    empresa_id = verificar_empresa(data.token)
    exigir_modulo(empresa_id, "delivery")
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, qr_entrega
            FROM pedidos
            WHERE id = %s AND empresa_id = %s
        """, (pedido_id, empresa_id))
        pedido = cur.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

        codigo = pedido["qr_entrega"] or gerar_codigo("ENTR")

        cur.execute("""
            UPDATE pedidos
            SET status_entrega = 'saiu_entrega',
                nome_entregador = %s,
                qr_entrega = %s
            WHERE id = %s
        """, (data.nome_entregador, codigo, pedido_id))

        conn.commit()
        return {"msg": "Pedido saiu para entrega", "codigo_bip": codigo}
    finally:
        cur.close()
        conn.close()


@app.get("/configuracoes")
def obter_configuracoes(token: str):
    empresa_id = verificar_empresa(token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM configuracoes WHERE empresa_id = %s", (empresa_id,))
        row = cur.fetchone()
        return row if row else {}
    finally:
        cur.close()
        conn.close()


@app.post("/configuracoes/salvar")
def salvar_configuracoes(data: ConfiguracoesCreate):
    empresa_id = verificar_empresa(data.token)
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM configuracoes WHERE empresa_id = %s", (empresa_id,))
        existe = cur.fetchone()

        valores = (
            data.whatsapp_numero,
            data.whatsapp_token,
            data.whatsapp_webhook,
            data.aiqfome_token,
            data.aiqfome_loja,
            data.comer_aqui_token,
            data.comer_aqui_loja,
            data.ifood_token,
            data.uber_token,
            data.pagamento_pix,
            data.pagamento_qrcode,
            data.pagamento_cartao_credito,
            data.pagamento_cartao_debito,
            data.pagamento_dinheiro,
            data.impressora_nome,
            data.impressora_porta,
            data.impressora_largura,
            data.impressora_corta_papel,
        )

        if existe:
            cur.execute("""
                UPDATE configuracoes SET
                    whatsapp_numero = %s,
                    whatsapp_token = %s,
                    whatsapp_webhook = %s,
                    aiqfome_token = %s,
                    aiqfome_loja = %s,
                    comer_aqui_token = %s,
                    comer_aqui_loja = %s,
                    ifood_token = %s,
                    uber_token = %s,
                    pagamento_pix = %s,
                    pagamento_qrcode = %s,
                    pagamento_cartao_credito = %s,
                    pagamento_cartao_debito = %s,
                    pagamento_dinheiro = %s,
                    impressora_nome = %s,
                    impressora_porta = %s,
                    impressora_largura = %s,
                    impressora_corta_papel = %s
                WHERE empresa_id = %s
            """, valores + (empresa_id,))
        else:
            cur.execute("""
                INSERT INTO configuracoes (
                    whatsapp_numero, whatsapp_token, whatsapp_webhook,
                    aiqfome_token, aiqfome_loja,
                    comer_aqui_token, comer_aqui_loja,
                    ifood_token, uber_token,
                    pagamento_pix, pagamento_qrcode,
                    pagamento_cartao_credito, pagamento_cartao_debito, pagamento_dinheiro,
                    impressora_nome, impressora_porta, impressora_largura, impressora_corta_papel,
                    empresa_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, valores + (empresa_id,))

        conn.commit()
        return {"msg": "Configurações salvas com sucesso"}
    finally:
        cur.close()
        conn.close()