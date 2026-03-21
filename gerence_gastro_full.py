import os
import json
import uuid
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
    if modulo not in obter_modulos_empresa(empresa_id):
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


def exigir_permissao_colaborador(token: str, permissao: str) -> int:
    if permissao not in PERMISSOES_VALIDAS:
        raise HTTPException(status_code=400, detail="Permissão inválida")

    colaborador_id = verificar_colaborador(token)
    colaborador = obter_colaborador(colaborador_id)

    if not colaborador["ativo"]:
        raise HTTPException(status_code=403, detail="Colaborador inativo")

    empresa_id = int(colaborador["empresa_id"])
    validar_empresa_ativa(empresa_id)

    permissoes = obter_permissoes_colaborador(colaborador_id)
    if not permissoes.get(permissao, False):
        raise HTTPException(status_code=403, detail=f"Sem permissão: {permissao}")

    return empresa_id


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


# rotas principais

@app.get("/")
def home():
    return {"status": "ok", "sistema": "RK Sistemas Completo"}


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


@app.get("/empresa/plano")
def plano_da_empresa(token: str):
    empresa_id = verificar_empresa(token)
    assinatura = obter_assinatura_empresa(empresa_id)
    assinatura["modulos_ativos"] = sorted(list(obter_modulos_empresa(empresa_id)))
    return assinatura


@app.post("/colaboradores")
def criar_colaborador(data: ColaboradorCreate):
    empresa_id = verificar_empresa(data.token)

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