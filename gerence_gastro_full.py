import os
from contextlib import asynccontextmanager
from typing import Literal

import bcrypt
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

SECRET = os.getenv("SECRET", "rk_sistemas_secret_2026")
DATABASE_URL = os.getenv("DATABASE_URL")


def conectar():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
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


def gerar_codigo_unico(cur, prefixo: str = "P") -> str:
    while True:
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS proximo FROM produtos")
        proximo = int(cur.fetchone()["proximo"])
        codigo = f"{prefixo}{proximo:06d}"

        cur.execute("SELECT id FROM produtos WHERE codigo = %s", (codigo,))
        if not cur.fetchone():
            return codigo


def obter_assinatura_empresa(empresa_id: int):
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
        WHERE a.empresa_id = %s
        ORDER BY a.id DESC
        LIMIT 1
    """, (empresa_id,))
    assinatura = cur.fetchone()

    cur.close()
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

    if recurso not in assinatura:
        raise HTTPException(status_code=400, detail="Recurso inválido")

    if not bool(assinatura[recurso]):
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
        senha VARCHAR(255) NOT NULL
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
        plano_id INTEGER NOT NULL REFERENCES planos(id),
        status VARCHAR(30) NOT NULL DEFAULT 'ativo',
        vencimento DATE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
        codigo VARCHAR(20) UNIQUE NOT NULL,
        nome VARCHAR(255) NOT NULL,
        preco NUMERIC(10,2) NOT NULL,
        estoque INTEGER NOT NULL DEFAULT 0,
        tipo VARCHAR(20) NOT NULL DEFAULT 'produto'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS adicionais (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
        nome VARCHAR(255) NOT NULL,
        preco NUMERIC(10,2) NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER UNIQUE NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,

        whatsapp_numero TEXT DEFAULT '',
        whatsapp_token TEXT DEFAULT '',
        whatsapp_webhook TEXT DEFAULT '',

        ifood_token TEXT DEFAULT '',
        aiqfome_token TEXT DEFAULT '',
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mesas (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
        numero INTEGER NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'livre'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS contas_financeiras (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
        tipo VARCHAR(30) NOT NULL,
        descricao VARCHAR(255) NOT NULL,
        valor NUMERIC(10,2) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'pendente'
    )
    """)

    cur.execute("SELECT id FROM admin WHERE email = %s", ("admin@rksistemas.com",))
    if not cur.fetchone():
        senha_hash = bcrypt.hashpw("Admin@123".encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO admin (email, senha) VALUES (%s, %s)",
            ("admin@rksistemas.com", senha_hash)
        )

    cur.execute("SELECT COUNT(*) AS total FROM planos")
    total_planos = int(cur.fetchone()["total"])
    if total_planos == 0:
        cur.execute("""
            INSERT INTO planos (nome, valor, whatsapp, delivery, relatorios, financeiro)
            VALUES
            (%s, %s, %s, %s, %s, %s),
            (%s, %s, %s, %s, %s, %s),
            (%s, %s, %s, %s, %s, %s)
        """, (
            "Básico", 49.90, False, False, True, True,
            "Intermediário", 79.90, True, False, True, True,
            "Premium", 119.90, True, True, True, True,
        ))

    conn.commit()
    cur.close()
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

    cur.execute("SELECT id, senha FROM admin WHERE email = %s", (data.email,))
    admin = cur.fetchone()

    cur.close()
    conn.close()

    if not admin or not bcrypt.checkpw(data.senha.encode(), admin["senha"].encode()):
        raise HTTPException(status_code=401, detail="Login inválido")

    return {"token": gerar_token({"admin": admin["id"]})}


@app.post("/admin/empresa")
def criar_empresa(token: str, data: EmpresaCreate):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM empresas WHERE email = %s", (data.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    senha_hash = bcrypt.hashpw(data.senha.encode(), bcrypt.gensalt()).decode()
    cur.execute(
        "INSERT INTO empresas (nome, email, senha) VALUES (%s, %s, %s) RETURNING id",
        (data.nome, data.email, senha_hash)
    )
    empresa_id = int(cur.fetchone()["id"])

    cur.execute("SELECT id FROM planos WHERE nome = %s", ("Básico",))
    plano_basico = cur.fetchone()
    plano_id = int(plano_basico["id"])

    cur.execute("""
        INSERT INTO assinaturas (empresa_id, plano_id, status, vencimento)
        VALUES (%s, %s, 'ativo', CURRENT_DATE + INTERVAL '30 days')
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
        ) VALUES (%s, TRUE, TRUE, TRUE, TRUE, TRUE, '80mm', TRUE)
    """, (empresa_id,))

    conn.commit()
    cur.close()
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
    empresas = cur.fetchall()

    cur.close()
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
    dados = cur.fetchall()

    cur.close()
    conn.close()
    return dados


@app.post("/admin/empresa/plano")
def trocar_plano_admin(token: str, empresa_id: int, plano_id: int):
    verificar_admin(token)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM empresas WHERE id = %s", (empresa_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    cur.execute("SELECT id FROM planos WHERE id = %s", (plano_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    cur.execute("""
        UPDATE assinaturas
        SET plano_id = %s, vencimento = CURRENT_DATE + INTERVAL '30 days'
        WHERE empresa_id = %s
    """, (plano_id, empresa_id))

    conn.commit()
    cur.close()
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

    cur.execute("SELECT id FROM empresas WHERE id = %s", (empresa_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    cur.execute("""
        UPDATE assinaturas
        SET status = %s
        WHERE empresa_id = %s
    """, (status, empresa_id))

    conn.commit()
    cur.close()
    conn.close()

    return {"msg": f"Status alterado para {status}"}


@app.get("/empresa/plano")
def plano_da_empresa(token: str):
    empresa_id = verificar_empresa(token)
    return obter_assinatura_empresa(empresa_id)


@app.post("/empresa/login")
def login_empresa(data: Login):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id, senha FROM empresas WHERE email = %s", (data.email,))
    empresa = cur.fetchone()

    cur.close()
    conn.close()

    if not empresa or not bcrypt.checkpw(data.senha.encode(), empresa["senha"].encode()):
        raise HTTPException(status_code=401, detail="Login inválido")

    empresa_id = int(empresa["id"])
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
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (empresa_id, codigo, data.nome, data.preco, data.estoque, data.tipo))

    conn.commit()
    cur.close()
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
        WHERE empresa_id = %s AND tipo = %s
        ORDER BY nome
    """, (empresa_id, tipo))
    dados = cur.fetchall()

    cur.close()
    conn.close()
    return dados


@app.get("/produtos/buscar")
def buscar_produtos(token: str, nome: str, tipo: Literal["produto", "lanche"] = "produto"):
    empresa_id = verificar_empresa(token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, codigo, nome, preco, estoque, tipo
        FROM produtos
        WHERE empresa_id = %s AND tipo = %s AND nome ILIKE %s
        ORDER BY nome
    """, (empresa_id, tipo, f"%{nome}%"))
    dados = cur.fetchall()

    cur.close()
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
        VALUES (%s, %s, %s)
    """, (empresa_id, data.nome, data.preco))

    conn.commit()
    cur.close()
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
        WHERE empresa_id = %s
        ORDER BY nome
    """, (empresa_id,))
    dados = cur.fetchall()

    cur.close()
    conn.close()
    return dados


@app.post("/configuracoes/salvar")
def salvar_configuracoes(data: ConfiguracoesCreate):
    empresa_id = verificar_empresa(data.token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id FROM configuracoes WHERE empresa_id = %s", (empresa_id,))
    existe = cur.fetchone()

    valores = (
        data.whatsapp_numero,
        data.whatsapp_token,
        data.whatsapp_webhook,
        data.ifood_token,
        data.aiqfome_token,
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
                ifood_token = %s,
                aiqfome_token = %s,
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
                ifood_token, aiqfome_token, uber_token,
                pagamento_pix, pagamento_qrcode,
                pagamento_cartao_credito, pagamento_cartao_debito, pagamento_dinheiro,
                impressora_nome, impressora_porta, impressora_largura, impressora_corta_papel,
                empresa_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, valores + (empresa_id,))

    conn.commit()
    cur.close()
    conn.close()

    return {"msg": "Configurações salvas com sucesso"}


@app.get("/configuracoes")
def obter_configuracoes(token: str):
    empresa_id = verificar_empresa(token)
    validar_empresa_ativa(empresa_id)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM configuracoes WHERE empresa_id = %s", (empresa_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return {}

    return row


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

    cur.execute("SELECT * FROM configuracoes WHERE empresa_id = %s", (empresa_id,))
    cfg = cur.fetchone()

    if cfg:
        permitidos = {
            "pix": bool(cfg["pagamento_pix"]),
            "qr_code": bool(cfg["pagamento_qrcode"]),
            "cartao_credito": bool(cfg["pagamento_cartao_credito"]),
            "cartao_debito": bool(cfg["pagamento_cartao_debito"]),
            "dinheiro": bool(cfg["pagamento_dinheiro"]),
        }
        if not permitidos.get(data.metodo_pagamento, False):
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Método de pagamento desabilitado nas configurações"
            )

    total = 0.0

    for item_id in data.itens:
        cur.execute("SELECT preco FROM produtos WHERE id = %s", (item_id,))
        row = cur.fetchone()
        if row:
            total += float(row["preco"])

    for adicional_id in data.adicionais:
        cur.execute("SELECT preco FROM adicionais WHERE id = %s", (adicional_id,))
        row = cur.fetchone()
        if row:
            total += float(row["preco"])

    total -= float(data.desconto)
    if total < 0:
        total = 0.0

    cur.close()
    conn.close()

    return {
        "msg": "Venda finalizada",
        "metodo_pagamento": data.metodo_pagamento,
        "total": round(total, 2)
    }