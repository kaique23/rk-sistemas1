from contextlib import asynccontextmanager
from typing import Literal

import bcrypt
import jwt
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

SECRET = "rk_sistemas_secret_2026"


import os
import psycopg2

def conectar():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.autocommit = True
    return conn


def gerar_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET, algorithm="HS256")


def verificar_admin(token: str) -> int:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        admin_id = data.get("admin")
        if not admin_id:
            raise ValueError("token admin inválido")
        return int(admin_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Apenas admin")


def verificar_empresa(token: str) -> int:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        empresa_id = data.get("empresa")
        if not empresa_id:
            raise ValueError("token empresa inválido")
        return int(empresa_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


def gerar_codigo_unico(cur: sqlite3.Cursor, prefixo: str = "P") -> str:
    while True:
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS proximo FROM produtos")
        proximo = int(cur.fetchone()["proximo"])
        codigo = f"{prefixo}{proximo:06d}"

        cur.execute("SELECT id FROM produtos WHERE codigo = ?", (codigo,))
        if not cur.fetchone():
            return codigo


def obter_assinatura_empresa(empresa_id: int) -> sqlite3.Row:
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            a.id AS assinatura_id,
            a.empresa_id,
            a.plano_id,
            a.status,
            a.vencimento,
            p.nome AS plano_nome,
            p.valor,
            p.whatsapp,
            p.delivery,
            p.relatorios,
            p.financeiro
        FROM assinaturas a
        INNER JOIN planos p ON p.id = a.plano_id
        WHERE a.empresa_id = ?
        ORDER BY a.id DESC
        LIMIT 1
    """, (empresa_id,))
    assinatura = cur.fetchone()
    conn.close()

    if not assinatura:
        raise HTTPException(status_code=403, detail="Empresa sem assinatura")

    return assinatura


def validar_empresa_ativa(empresa_id: int):
    assinatura = obter_assinatura_empresa(empresa_id)
    status = assinatura["status"]

    if status != "ativo":
        raise HTTPException(
            status_code=403,
            detail=f"Empresa com acesso bloqueado. Status atual: {status}"
        )


def verificar_recurso_plano(empresa_id: int, recurso: str):
    validar_empresa_ativa(empresa_id)
    assinatura = obter_assinatura_empresa(empresa_id)

    if recurso not in assinatura.keys():
        raise HTTPException(status_code=400, detail="Recurso inválido")

    if int(assinatura[recurso]) != 1:
        raise HTTPException(
            status_code=403,
            detail=f"Recurso '{recurso}' não disponível no plano atual"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        senha TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS planos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        valor REAL NOT NULL,
        whatsapp INTEGER DEFAULT 0,
        delivery INTEGER DEFAULT 0,
        relatorios INTEGER DEFAULT 1,
        financeiro INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assinaturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        plano_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'ativo',
        vencimento TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        codigo TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        preco REAL NOT NULL,
        estoque INTEGER NOT NULL DEFAULT 0,
        tipo TEXT NOT NULL DEFAULT 'produto'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS adicionais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        preco REAL NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER UNIQUE NOT NULL,

        whatsapp_numero TEXT DEFAULT '',
        whatsapp_token TEXT DEFAULT '',
        whatsapp_webhook TEXT DEFAULT '',

        ifood_token TEXT DEFAULT '',
        aiqfome_token TEXT DEFAULT '',
        uber_token TEXT DEFAULT '',

        pagamento_pix INTEGER DEFAULT 1,
        pagamento_qrcode INTEGER DEFAULT 1,
        pagamento_cartao_credito INTEGER DEFAULT 1,
        pagamento_cartao_debito INTEGER DEFAULT 1,
        pagamento_dinheiro INTEGER DEFAULT 1,

        impressora_nome TEXT DEFAULT '',
        impressora_porta TEXT DEFAULT '',
        impressora_largura TEXT DEFAULT '80mm',
        impressora_corta_papel INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        numero INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'livre'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS contas_financeiras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendente'
    )
    """)

    cur.execute("SELECT id FROM admin WHERE email = ?", ("admin@rksistemas.com",))
    if not cur.fetchone():
        senha_hash = bcrypt.hashpw("Admin@123".encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO admin (email, senha) VALUES (?, ?)",
            ("admin@rksistemas.com", senha_hash)
        )

    cur.execute("SELECT COUNT(*) AS total FROM planos")
    total_planos = int(cur.fetchone()["total"])
    if total_planos == 0:
        cur.execute("""
            INSERT INTO planos (nome, valor, whatsapp, delivery, relatorios, financeiro)
            VALUES
            ('Básico', 49.90, 0, 0, 1, 1),
            ('Intermediário', 79.90, 1, 0, 1, 1),
            ('Premium', 119.90, 1, 1, 1, 1)
        """)

    conn.commit()
    conn.close()
    yield


app = FastAPI(title="RK Sistemas", lifespan=lifespan)


class Login(BaseModel):
    email: EmailStr
    senha: str


class EmpresaCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class ProdutoCreate(BaseModel):
    token: str
    nome: str
    preco: float
    estoque: int
    tipo: Literal["produto", "lanche"] = "produto"


class AdicionalCreate(BaseModel):
    token: str
    nome: str
    preco: float


class VendaCreate(BaseModel):
    token: str
    itens: list[int]
    adicionais: list[int] = []
    desconto: float = 0.0
    metodo_pagamento: Literal[
        "dinheiro",
        "pix",
        "qr_code",
        "cartao_credito",
        "cartao_debito"
    ] = "dinheiro"


class ConfiguracoesCreate(BaseModel):
    token: str

    whatsapp_numero: str = ""
    whatsapp_token: str = ""
    whatsapp_webhook: str = ""

    ifood_token: str = ""
    aiqfome_token: str = ""
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


@app.get("/")
def home():
    return {"status": "ok", "sistema": "RK Sistemas"}


@app.post("/admin/login")
def login_admin(data: Login):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id, senha FROM admin WHERE email = ?", (data.email,))
    admin = cur.fetchone()
    conn.close()

    if not admin or not bcrypt.checkpw(data.senha.encode(), admin["senha"].encode()):
        raise HTTPException(status_code=401, detail="Login inválido")

    return {"token": gerar_token({"admin": admin["id"]})}


@app.post("/admin/empresa")
def criar_empresa(token: str, data: EmpresaCreate):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM empresas WHERE email = ?", (data.email,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    senha_hash = bcrypt.hashpw(data.senha.encode(), bcrypt.gensalt()).decode()
    cur.execute(
        "INSERT INTO empresas (nome, email, senha) VALUES (?, ?, ?)",
        (data.nome, data.email, senha_hash)
    )
    empresa_id = cur.lastrowid

    cur.execute("SELECT id FROM planos WHERE nome = 'Básico'")
    plano_basico = cur.fetchone()
    plano_id = int(plano_basico["id"])

    cur.execute("""
        INSERT INTO assinaturas (empresa_id, plano_id, status, vencimento)
        VALUES (?, ?, 'ativo', date('now', '+30 day'))
    """, (empresa_id, plano_id))

    cur.execute("""
        INSERT INTO configuracoes (
            empresa_id,
            pagamento_pix,
            pagamento_qrcode,
            pagamento_cartao_credito,
            pagamento_cartao_debito,
            pagamento_dinheiro,
            impressora_largura,
            impressora_corta_papel
        ) VALUES (?, 1, 1, 1, 1, 1, '80mm', 1)
    """, (empresa_id,))

    conn.commit()
    conn.close()

    return {"msg": "Empresa criada com sucesso"}


@app.get("/admin/empresas")
def listar_empresas_admin(token: str):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            e.id,
            e.nome,
            e.email,
            a.status,
            a.vencimento,
            p.nome AS plano_nome,
            p.valor
        FROM empresas e
        LEFT JOIN assinaturas a ON a.empresa_id = e.id
        LEFT JOIN planos p ON p.id = a.plano_id
        ORDER BY e.nome
    """)
    empresas = [dict(row) for row in cur.fetchall()]
    conn.close()

    return empresas


@app.get("/planos")
def listar_planos():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nome, valor, whatsapp, delivery, relatorios, financeiro
        FROM planos
        ORDER BY valor
    """)
    dados = [dict(row) for row in cur.fetchall()]
    conn.close()
    return dados


@app.post("/admin/empresa/plano")
def trocar_plano_admin(token: str, empresa_id: int, plano_id: int):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM empresas WHERE id = ?", (empresa_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    cur.execute("SELECT id FROM planos WHERE id = ?", (plano_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    cur.execute("""
        UPDATE assinaturas
        SET plano_id = ?, vencimento = date('now', '+30 day')
        WHERE empresa_id = ?
    """, (plano_id, empresa_id))

    conn.commit()
    conn.close()

    return {"msg": "Plano alterado com sucesso"}


@app.post("/admin/empresa/status")
def alterar_status_empresa(token: str, empresa_id: int, status: str):
    verificar_admin(token)

    status_permitido = {"ativo", "pausado", "cancelado", "bloqueado"}
    if status not in status_permitido:
        raise HTTPException(status_code=400, detail="Status inválido")

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM empresas WHERE id = ?", (empresa_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    cur.execute("""
        UPDATE assinaturas
        SET status = ?
        WHERE empresa_id = ?
    """, (status, empresa_id))

    conn.commit()
    conn.close()

    return {"msg": f"Status alterado para {status}"}


@app.get("/empresa/plano")
def plano_da_empresa(token: str):
    empresa_id = verificar_empresa(token)
    assinatura = obter_assinatura_empresa(empresa_id)
    return dict(assinatura)


@app.post("/empresa/login")
def login_empresa(data: Login):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id, senha FROM empresas WHERE email = ?", (data.email,))
    empresa = cur.fetchone()

    if not empresa or not bcrypt.checkpw(data.senha.encode(), empresa["senha"].encode()):
        conn.close()
        raise HTTPException(status_code=401, detail="Login inválido")

    empresa_id = int(empresa["id"])
    conn.close()

    validar_empresa_ativa(empresa_id)

    return {"token": gerar_token({"empresa": empresa_id})}


@app.post("/produto")
def criar_produto(data: ProdutoCreate):
    empresa_id = verificar_empresa(data.token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()

    codigo = gerar_codigo_unico(cur, "P" if data.tipo == "produto" else "L")

    cur.execute("""
        INSERT INTO produtos (empresa_id, codigo, nome, preco, estoque, tipo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (empresa_id, codigo, data.nome, data.preco, data.estoque, data.tipo))

    conn.commit()
    conn.close()

    return {"msg": "Item cadastrado", "codigo": codigo}


@app.get("/produtos")
def listar_produtos(token: str, tipo: Literal["produto", "lanche"] = "produto"):
    empresa_id = verificar_empresa(token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, codigo, nome, preco, estoque, tipo
        FROM produtos
        WHERE empresa_id = ? AND tipo = ?
        ORDER BY nome
    """, (empresa_id, tipo))
    dados = [dict(row) for row in cur.fetchall()]
    conn.close()
    return dados


@app.get("/produtos/buscar")
def buscar_produtos(
    token: str,
    nome: str,
    tipo: Literal["produto", "lanche"] = "produto"
):
    empresa_id = verificar_empresa(token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, codigo, nome, preco, estoque, tipo
        FROM produtos
        WHERE empresa_id = ? AND tipo = ? AND nome LIKE ?
        ORDER BY nome
    """, (empresa_id, tipo, f"%{nome}%"))
    dados = [dict(row) for row in cur.fetchall()]
    conn.close()
    return dados


@app.post("/adicionais")
def criar_adicional(data: AdicionalCreate):
    empresa_id = verificar_empresa(data.token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO adicionais (empresa_id, nome, preco)
        VALUES (?, ?, ?)
    """, (empresa_id, data.nome, data.preco))
    conn.commit()
    conn.close()

    return {"msg": "Adicional cadastrado"}


@app.get("/adicionais")
def listar_adicionais(token: str):
    empresa_id = verificar_empresa(token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nome, preco
        FROM adicionais
        WHERE empresa_id = ?
        ORDER BY nome
    """, (empresa_id,))
    dados = [dict(row) for row in cur.fetchall()]
    conn.close()
    return dados


@app.post("/configuracoes/salvar")
def salvar_configuracoes(data: ConfiguracoesCreate):
    empresa_id = verificar_empresa(data.token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM configuracoes WHERE empresa_id = ?", (empresa_id,))
    existe = cur.fetchone()

    valores = (
        data.whatsapp_numero,
        data.whatsapp_token,
        data.whatsapp_webhook,
        data.ifood_token,
        data.aiqfome_token,
        data.uber_token,
        int(data.pagamento_pix),
        int(data.pagamento_qrcode),
        int(data.pagamento_cartao_credito),
        int(data.pagamento_cartao_debito),
        int(data.pagamento_dinheiro),
        data.impressora_nome,
        data.impressora_porta,
        data.impressora_largura,
        int(data.impressora_corta_papel),
    )

    if existe:
        cur.execute("""
            UPDATE configuracoes SET
                whatsapp_numero = ?,
                whatsapp_token = ?,
                whatsapp_webhook = ?,
                ifood_token = ?,
                aiqfome_token = ?,
                uber_token = ?,
                pagamento_pix = ?,
                pagamento_qrcode = ?,
                pagamento_cartao_credito = ?,
                pagamento_cartao_debito = ?,
                pagamento_dinheiro = ?,
                impressora_nome = ?,
                impressora_porta = ?,
                impressora_largura = ?,
                impressora_corta_papel = ?
            WHERE empresa_id = ?
        """, valores + (empresa_id,))
    else:
        cur.execute("""
            INSERT INTO configuracoes (
                whatsapp_numero, whatsapp_token, whatsapp_webhook,
                ifood_token, aiqfome_token, uber_token,
                pagamento_pix, pagamento_qrcode,
                pagamento_cartao_credito, pagamento_cartao_debito, pagamento_dinheiro,
                impressora_nome, impressora_porta, impressora_largura, impressora_corta_papel,
                empresa_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, valores + (empresa_id,))

    conn.commit()
    conn.close()

    return {"msg": "Configurações salvas com sucesso"}


@app.get("/configuracoes")
def obter_configuracoes(token: str):
    empresa_id = verificar_empresa(token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT * FROM configuracoes WHERE empresa_id = ?", (empresa_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {}

    return dict(row)


@app.post("/whatsapp/teste")
def teste_whatsapp(token: str):
    empresa_id = verificar_empresa(token)
    verificar_recurso_plano(empresa_id, "whatsapp")
    return {"msg": "WhatsApp liberado neste plano"}


@app.post("/delivery/teste")
def teste_delivery(token: str):
    empresa_id = verificar_empresa(token)
    verificar_recurso_plano(empresa_id, "delivery")
    return {"msg": "Delivery liberado neste plano"}


@app.post("/venda")
def finalizar_venda(data: VendaCreate):
    empresa_id = verificar_empresa(data.token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM configuracoes WHERE empresa_id = ?", (empresa_id,))
    cfg = cur.fetchone()

    if cfg:
        permitidos = {
            "pix": int(cfg["pagamento_pix"]) == 1,
            "qr_code": int(cfg["pagamento_qrcode"]) == 1,
            "cartao_credito": int(cfg["pagamento_cartao_credito"]) == 1,
            "cartao_debito": int(cfg["pagamento_cartao_debito"]) == 1,
            "dinheiro": int(cfg["pagamento_dinheiro"]) == 1,
        }
        if not permitidos.get(data.metodo_pagamento, False):
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Método de pagamento desabilitado nas configurações"
            )

    total = 0.0

    for item_id in data.itens:
        cur.execute("SELECT preco FROM produtos WHERE id = ?", (item_id,))
        row = cur.fetchone()
        if row:
            total += float(row["preco"])

    for adicional_id in data.adicionais:
        cur.execute("SELECT preco FROM adicionais WHERE id = ?", (adicional_id,))
        row = cur.fetchone()
        if row:
            total += float(row["preco"])

    total -= float(data.desconto)
    if total < 0:
        total = 0.0

    conn.close()

    return {
        "msg": "Venda finalizada",
        "metodo_pagamento": data.metodo_pagamento,
        "total": round(total, 2)
    }