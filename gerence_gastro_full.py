import os
from contextlib import asynccontextmanager
from typing import Literal

import bcrypt
import jwt
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

SECRET = os.getenv("SECRET", "rk_sistemas_secret_2026")
DATABASE_URL = os.getenv("DATABASE_URL")


def conectar():
    return psycopg2.connect(DATABASE_URL)


def gerar_token(payload: dict):
    return jwt.encode(payload, SECRET, algorithm="HS256")


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = conectar()
    cur = conn.cursor()

    # ADMIN
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE,
        senha TEXT
    )
    """)

    # EMPRESAS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id SERIAL PRIMARY KEY,
        nome TEXT,
        email TEXT UNIQUE,
        senha TEXT
    )
    """)

    # PLANOS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS planos (
        id SERIAL PRIMARY KEY,
        nome TEXT,
        valor REAL,
        whatsapp BOOLEAN,
        delivery BOOLEAN
    )
    """)

    # ASSINATURAS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assinaturas (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER,
        plano_id INTEGER,
        status TEXT
    )
    """)

    # PRODUTOS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER,
        codigo TEXT,
        nome TEXT,
        preco REAL,
        tipo TEXT
    )
    """)

    # ADMIN PADRÃO
    cur.execute("SELECT id FROM admin WHERE email = %s", ("admin@rksistemas.com",))
    if not cur.fetchone():
        senha = bcrypt.hashpw("Admin@123".encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO admin (email, senha) VALUES (%s, %s)",
            ("admin@rksistemas.com", senha)
        )

    # PLANOS PADRÃO
    cur.execute("SELECT COUNT(*) FROM planos")
    total = cur.fetchone()[0]

    if total == 0:
        cur.execute("""
        INSERT INTO planos (nome, valor, whatsapp, delivery)
        VALUES
        ('Básico', 49.9, false, false),
        ('Intermediário', 79.9, true, false),
        ('Premium', 119.9, true, true)
        """)

    conn.commit()
    cur.close()
    conn.close()

    yield


app = FastAPI(lifespan=lifespan)


# ---------------- LOGIN ----------------

class Login(BaseModel):
    email: EmailStr
    senha: str


@app.post("/admin/login")
def login_admin(data: Login):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id, senha FROM admin WHERE email = %s", (data.email,))
    admin = cur.fetchone()

    cur.close()
    conn.close()

    if not admin or not bcrypt.checkpw(data.senha.encode(), admin[1].encode()):
        raise HTTPException(status_code=401, detail="Login inválido")

    return {"token": gerar_token({"admin": admin[0]})}


# ---------------- EMPRESA ----------------

class Empresa(BaseModel):
    nome: str
    email: EmailStr
    senha: str


@app.post("/admin/empresa")
def criar_empresa(token: str, data: Empresa):
    conn = conectar()
    cur = conn.cursor()

    senha = bcrypt.hashpw(data.senha.encode(), bcrypt.gensalt()).decode()

    cur.execute("""
    INSERT INTO empresas (nome, email, senha)
    VALUES (%s, %s, %s) RETURNING id
    """, (data.nome, data.email, senha))

    empresa_id = cur.fetchone()[0]

    # plano básico automático
    cur.execute("SELECT id FROM planos WHERE nome = 'Básico'")
    plano_id = cur.fetchone()[0]

    cur.execute("""
    INSERT INTO assinaturas (empresa_id, plano_id, status)
    VALUES (%s, %s, 'ativo')
    """, (empresa_id, plano_id))

    conn.commit()
    cur.close()
    conn.close()

    return {"msg": "Empresa criada"}


# ---------------- PRODUTOS ----------------

class Produto(BaseModel):
    token: str
    nome: str
    preco: float
    tipo: Literal["produto", "lanche"]


@app.post("/produto")
def criar_produto(data: Produto):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO produtos (empresa_id, codigo, nome, preco, tipo)
    VALUES (1, 'AUTO', %s, %s, %s)
    """, (data.nome, data.preco, data.tipo))

    conn.commit()
    cur.close()
    conn.close()

    return {"msg": "Produto criado"}


@app.get("/")
def home():
    return {"status": "ok"}