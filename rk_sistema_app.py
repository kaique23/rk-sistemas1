import os
import requests
from tkinter import messagebox
from customtkinter import *
from PIL import Image

set_appearance_mode("dark")
set_default_color_theme("blue")

COR_FUNDO = "#08111f"
COR_CARD = "#101b2d"
COR_CARD_2 = "#0c1524"
COR_BORDA = "#1f3552"
COR_TEXTO = "#eef6ff"
COR_SUBTEXTO = "#9eb6d3"

COR_AZUL = "#1478ff"
COR_AZUL_HOVER = "#0f63d0"
COR_VERDE = "#12b76a"
COR_VERDE_HOVER = "#0f9657"
COR_LARANJA = "#f59e0b"
COR_LARANJA_HOVER = "#d88706"
COR_VERMELHO = "#ef4444"
COR_VERMELHO_HOVER = "#d73737"
COR_CINZA = "#344054"
COR_CINZA_HOVER = "#445468"

PERMISSOES_COLABORADOR = [
    ("frente_caixa", "Frente de caixa"),
    ("estoque", "Estoque"),
    ("fiscal", "Fiscal"),
    ("financeiro", "Financeiro"),
    ("clientes", "Clientes"),
    ("fornecedores", "Fornecedores"),
    ("funcionarios", "Funcionários"),
    ("mesas", "Mesas"),
    ("comandas", "Comandas"),
    ("pedidos", "Pedidos"),
    ("kds_cozinha", "KDS Cozinha"),
    ("kds_bar", "KDS Bar"),
    ("delivery", "Delivery"),
    ("relatorios", "Relatórios"),
    ("whatsapp", "WhatsApp"),
    ("aiqfome", "aiqfome"),
    ("comer_aqui", "Comer Aqui"),
]


class App(CTk):
    def __init__(self):
        super().__init__()
        self.title("GSI Sistemas")
        self.geometry("1550x920")
        self.configure(fg_color=COR_FUNDO)

        self.api = "https://rk-sistemas1.onrender.com"
        self.token = None
        self.tipo_login = StringVar(value="empresa")

        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"
        self.permissoes_colaborador = {}

        self.sidebar = None
        self.content = None
        self._current_screen = None
        self._current_empresa_admin = None

        self.logo_top = None
        self.logo_login = None
        self.logo_bg = None
        self.bg_label = None
        self._carregar_logo()

        self.login_screen()

    # ================= VISUAL =================

    def _gerar_logo_transparente(self, img_rgba, alpha=35):
        nova = img_rgba.copy().convert("RGBA")
        pixels = []
        for r, g, b, a in nova.getdata():
            pixels.append((r, g, b, 0 if a == 0 else alpha))
        nova.putdata(pixels)
        return nova

    def _carregar_logo(self):
        if os.path.exists("logo.png"):
            img = Image.open("logo.png").convert("RGBA")
            img_bg = self._gerar_logo_transparente(img, 35)
            self.logo_top = CTkImage(light_image=img, dark_image=img, size=(110, 55))
            self.logo_login = CTkImage(light_image=img, dark_image=img, size=(180, 90))
            self.logo_bg = CTkImage(light_image=img_bg, dark_image=img_bg, size=(900, 450))

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _marca_dagua(self, parent, relx=0.50, rely=0.50):
        if self.logo_bg:
            self.bg_label = CTkLabel(parent, text="", image=self.logo_bg, fg_color="transparent")
            self.bg_label.place(relx=relx, rely=rely, anchor="center")
            self.bg_label.lower()

    def _card(self, parent):
        return CTkFrame(parent, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)

    def _botao(self, parent, text, command, color=COR_AZUL, hover=COR_AZUL_HOVER, **kwargs):
        return CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=color,
            hover_color=hover,
            text_color="white",
            corner_radius=10,
            **kwargs,
        )

    def _titulo(self, parent, texto):
        CTkLabel(parent, text=texto, font=("Arial", 22, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=14, pady=(14, 8))

    # ================= API =================

    def request_json(self, method, url, **kwargs):
        r = requests.request(method, url, timeout=30, **kwargs)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        return r, data

    def api_error(self, title, data, fallback="Erro"):
        if isinstance(data, dict):
            msg = data.get("detail") or data.get("raw") or fallback
        else:
            msg = str(data)
        messagebox.showerror(title, msg)

    def refresh_screen(self):
        if callable(self._current_screen):
            self._current_screen()

    def load_empresa_context(self):
        if self.usuario_tipo != "empresa" or not self.token:
            return
        r, data = self.request_json("GET", f"{self.api}/empresa/plano", params={"token": self.token})
        if r.status_code == 200:
            self.plano_nome = data.get("plano_nome", "—")

    def has_colab_perm(self, perm):
        if self.usuario_tipo != "colaborador":
            return True
        return bool(self.permissoes_colaborador.get(perm, False))

    def logout(self):
        if self.token:
            try:
                self.request_json("POST", f"{self.api}/empresa/logout", json={"token": self.token})
            except Exception:
                pass
        self.login_screen()

    # ================= LOGIN =================

    def login_screen(self):
        self.clear()
        self.token = None
        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"
        self.permissoes_colaborador = {}

        base = CTkFrame(self, fg_color=COR_FUNDO)
        base.pack(fill="both", expand=True)
        self._marca_dagua(base, 0.5, 0.5)

        box = CTkFrame(base, fg_color=COR_CARD, corner_radius=18, border_width=1, border_color=COR_BORDA)
        box.pack(expand=True, padx=20, pady=20)

        if self.logo_login:
            CTkLabel(box, text="", image=self.logo_login).pack(pady=(20, 6))

        CTkLabel(box, text="GSI Sistemas", font=("Arial", 30, "bold"), text_color=COR_TEXTO).pack(pady=(0, 4))
        CTkLabel(box, text="Acesso ao sistema", font=("Arial", 16), text_color=COR_SUBTEXTO).pack(pady=(0, 15))

        tipo_frame = CTkFrame(box, fg_color=COR_CARD_2, corner_radius=12)
        tipo_frame.pack(fill="x", padx=20, pady=10)

        CTkLabel(tipo_frame, text="Tipo de login", font=("Arial", 15, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 5))
        CTkRadioButton(tipo_frame, text="Empresa", variable=self.tipo_login, value="empresa").pack(anchor="w", padx=15, pady=3)
        CTkRadioButton(tipo_frame, text="Colaborador", variable=self.tipo_login, value="colaborador").pack(anchor="w", padx=15, pady=(3, 10))

        self.login_email = CTkEntry(box, width=360, placeholder_text="Email")
        self.login_email.pack(pady=8)

        self.login_senha = CTkEntry(box, width=360, placeholder_text="Senha", show="*")
        self.login_senha.pack(pady=8)

        self.login_api = CTkEntry(box, width=360)
        self.login_api.insert(0, self.api)
        self.login_api.pack(pady=8)

        self._botao(box, "Entrar", self.do_login, COR_AZUL, COR_AZUL_HOVER, width=220, height=42).pack(pady=18)

    def do_login(self):
        self.api = self.login_api.get().strip()
        email = self.login_email.get().strip()
        senha = self.login_senha.get().strip()
        tipo = self.tipo_login.get()

        rota = {
            "empresa": "/empresa/login",
            "colaborador": "/colaborador/login",
        }[tipo]

        r, data = self.request_json("POST", f"{self.api}{rota}", json={"email": email, "senha": senha})

        if r.status_code != 200:
            r_admin, data_admin = self.request_json("POST", f"{self.api}/admin/login", json={"email": email, "senha": senha})
            if r_admin.status_code == 200:
                self.token = data_admin["token"]
                self.usuario_tipo = "admin"
                self.usuario_nome = "Admin Global"
                self.usuario_cargo = "Administrador"
                self.admin_empresas_screen()
                return

            self.api_error("Erro de login", data, "Não foi possível entrar")
            return

        self.token = data["token"]
        self.usuario_tipo = tipo
        self.usuario_nome = data.get("nome", "")
        self.usuario_cargo = data.get("cargo", "")

        if tipo == "empresa":
            self.load_empresa_context()
            if not self.usuario_nome:
                self.usuario_nome = "Admin do Estabelecimento"
                self.usuario_cargo = "Administrador"
            self.dashboard_screen()
        else:
            self.permissoes_colaborador = data.get("permissoes", {})
            self.colaborador_dashboard_screen()

    # ================= LAYOUT =================

    def build_shell(self, title):
        self.clear()

        fundo = CTkFrame(self, fg_color=COR_FUNDO)
        fundo.pack(fill="both", expand=True)

        top = CTkFrame(fundo, height=76, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        top.pack(fill="x", padx=10, pady=10)

        left_top = CTkFrame(top, fg_color="transparent")
        left_top.pack(side="left", padx=12)

        if self.logo_top:
            CTkLabel(left_top, text="", image=self.logo_top).pack(side="left", padx=(4, 8), pady=8)

        CTkLabel(left_top, text=title, font=("Arial", 24, "bold"), text_color=COR_TEXTO).pack(side="left", padx=8)

        right = CTkFrame(top, fg_color="transparent")
        right.pack(side="right", padx=12)

        if self.usuario_tipo == "empresa":
            CTkLabel(right, text=f"Plano: {self.plano_nome}", font=("Arial", 12), text_color=COR_SUBTEXTO).pack(side="left", padx=8)

        if self.usuario_nome:
            CTkLabel(right, text=f"{self.usuario_nome} | {self.usuario_cargo}", font=("Arial", 13, "bold"), text_color=COR_TEXTO).pack(side="left", padx=10)

        self._botao(right, "Atualizar", self.refresh_screen, COR_LARANJA, COR_LARANJA_HOVER, width=96).pack(side="left", padx=4)
        self._botao(right, "Sair", self.logout, COR_VERMELHO, COR_VERMELHO_HOVER, width=80).pack(side="left", padx=4)

        main = CTkFrame(fundo, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.sidebar = CTkFrame(main, width=270, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)

        self.content = CTkFrame(main, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)

        self._marca_dagua(self.content, 0.50, 0.50)

    # ================= SIDEBARS =================

    def admin_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()
        CTkLabel(self.sidebar, text="Painel Admin", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(pady=15)
        self._botao(self.sidebar, "Empresas", self.admin_empresas_screen).pack(fill="x", padx=12, pady=5)

    def empresa_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Empresa", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(pady=15)
        self._botao(self.sidebar, "Dashboard", self.dashboard_screen, COR_AZUL, COR_AZUL_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Frente de Caixa", self.frente_caixa_screen, COR_VERDE, COR_VERDE_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Cadastro", self.cadastro_screen, COR_AZUL, COR_AZUL_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Operação", self.operacao_screen, COR_LARANJA, COR_LARANJA_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Relatórios", lambda: self.placeholder_screen("Relatórios"), COR_CINZA, COR_CINZA_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "WhatsApp", lambda: self.placeholder_screen("WhatsApp"), COR_VERDE, COR_VERDE_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "aiqfome", lambda: self.placeholder_screen("aiqfome"), COR_AZUL, COR_AZUL_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Comer Aqui", lambda: self.placeholder_screen("Comer Aqui"), COR_AZUL, COR_AZUL_HOVER).pack(fill="x", padx=12, pady=4)

    def colaborador_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()
        CTkLabel(self.sidebar, text="Colaborador", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(pady=15)
        self._botao(self.sidebar, "Dashboard", self.colaborador_dashboard_screen, COR_AZUL, COR_AZUL_HOVER).pack(fill="x", padx=12, pady=4)

        cores = [COR_AZUL, COR_VERDE, COR_LARANJA, COR_CINZA]
        hovers = [COR_AZUL_HOVER, COR_VERDE_HOVER, COR_LARANJA_HOVER, COR_CINZA_HOVER]
        idx = 0
        for key, label in PERMISSOES_COLABORADOR:
            if self.has_colab_perm(key):
                cor = cores[idx % len(cores)]
                hov = hovers[idx % len(hovers)]
                self._botao(self.sidebar, label, lambda l=label: self.placeholder_screen(l), cor, hov).pack(fill="x", padx=12, pady=4)
                idx += 1

    # ================= HELPERS CRUD =================

    def _crud_simples(self, titulo, rota_post, rota_get, campos, sidebar="empresa"):
        self._current_screen = lambda: self._crud_simples(titulo, rota_post, rota_get, campos, sidebar)
        self.build_shell(titulo)

        if sidebar == "empresa":
            self.empresa_sidebar()
        else:
            self.admin_sidebar()

        left = self._card(self.content)
        left.configure(width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self._titulo(left, f"Novo {titulo[:-1] if titulo.endswith('s') else titulo}")

        entries = {}
        for chave, label in campos:
            ent = CTkEntry(left, placeholder_text=label, width=320)
            ent.pack(pady=6)
            entries[chave] = ent

        def salvar():
            payload = {"token": self.token}
            for chave in entries:
                valor = entries[chave].get().strip()
                if chave == "numero":
                    try:
                        payload[chave] = int(valor)
                    except Exception:
                        messagebox.showwarning("Aviso", "Número inválido")
                        return
                else:
                    payload[chave] = valor

            r, data = self.request_json("POST", f"{self.api}{rota_post}", json=payload)
            if r.status_code != 200:
                self.api_error("Erro", data)
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Salvo com sucesso"))
            self._crud_simples(titulo, rota_post, rota_get, campos, sidebar)

        self._botao(left, "Salvar", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}{rota_get}", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for row in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            texto = " | ".join([f"{k}: {row.get(k, '')}" for k, _ in campos if k in row])
            CTkLabel(card, text=texto or str(row), text_color=COR_TEXTO, wraplength=900, justify="left").pack(anchor="w", padx=10, pady=10)

    # ================= EMPRESA =================

    def dashboard_screen(self):
        self._current_screen = self.dashboard_screen
        self.load_empresa_context()
        self.build_shell("Dashboard")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo(box, "Dashboard")
        CTkLabel(box, text=f"Plano: {self.plano_nome}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=14, pady=4)

    def frente_caixa_screen(self):
        self._current_screen = self.frente_caixa_screen
        self.build_shell("Frente de Caixa")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        self._titulo(box, "Frente de Caixa")

        topo = CTkFrame(box, fg_color="transparent")
        topo.pack(fill="x", padx=14, pady=10)

        self._botao(topo, "Abrir Comanda", self.placeholder_screen_comandas, COR_AZUL, COR_AZUL_HOVER, width=150).pack(
            side="left", padx=5)
        self._botao(topo, "Lançar Pedido", self.placeholder_screen_pedidos, COR_LARANJA, COR_LARANJA_HOVER,
                    width=150).pack(side="left", padx=5)
        self._botao(topo, "Mesas", self.mesas_screen, COR_VERDE, COR_VERDE_HOVER, width=150).pack(side="left", padx=5)
        self._botao(topo, "Clientes", self.clientes_screen, COR_CINZA, COR_CINZA_HOVER, width=150).pack(side="left",
                                                                                                        padx=5)

        info = CTkFrame(box, fg_color=COR_CARD_2, corner_radius=12)
        info.pack(fill="x", padx=14, pady=10)

        CTkLabel(info, text="Resumo do Caixa", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(anchor="w",
                                                                                                      padx=12,
                                                                                                      pady=(12, 6))
        CTkLabel(info, text="Pedidos do balcão, fechamento de conta e cupom fiscal ficarão centralizados aqui.",
                 text_color=COR_SUBTEXTO).pack(anchor="w", padx=12, pady=(0, 12))

        grade = CTkFrame(box, fg_color="transparent")
        grade.pack(fill="both", expand=True, padx=14, pady=10)

        card1 = self._card(grade)
        card1.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        CTkLabel(card1, text="Comandas em aberto", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w",
                                                                                                          padx=12,
                                                                                                          pady=(12, 6))
        CTkLabel(card1, text="Aqui você vai listar comandas abertas do caixa.", text_color=COR_SUBTEXTO).pack(
            anchor="w", padx=12, pady=(0, 12))

        card2 = self._card(grade)
        card2.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        CTkLabel(card2, text="Fechamento / pagamento", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(
            anchor="w", padx=12, pady=(12, 6))
        CTkLabel(card2, text="Aqui entra pix, cartão, dinheiro e emissão fiscal.", text_color=COR_SUBTEXTO).pack(
            anchor="w", padx=12, pady=(0, 12))

    def cadastro_screen(self):
        self._current_screen = self.cadastro_screen
        self.build_shell("Cadastro")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo(box, "Cadastro")

        linha = CTkFrame(box, fg_color="transparent")
        linha.pack(pady=20)

        self._botao(linha, "Cliente", self.clientes_screen, COR_VERDE, COR_VERDE_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Fornecedor", self.fornecedores_screen, COR_VERDE, COR_VERDE_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Colabora", self.colaboradores_screen, COR_AZUL, COR_AZUL_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Entregadores", self.entregadores_screen, COR_LARANJA, COR_LARANJA_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Empresa", self.placeholder_screen_empresa, COR_CINZA, COR_CINZA_HOVER, width=160).pack(side="left", padx=6)

    def operacao_screen(self):
        self._current_screen = self.operacao_screen
        self.build_shell("Operação")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo(box, "Operação")

        linha = CTkFrame(box, fg_color="transparent")
        linha.pack(pady=20)

        self._botao(linha, "Mesa", self.mesas_screen, COR_VERDE, COR_VERDE_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Pedido", self.placeholder_screen_pedidos, COR_LARANJA, COR_LARANJA_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Comandas", self.placeholder_screen_comandas, COR_AZUL, COR_AZUL_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "KDS Cozinha", lambda: self.placeholder_screen("KDS Cozinha"), COR_CINZA, COR_CINZA_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "KDS Bar", lambda: self.placeholder_screen("KDS Bar"), COR_CINZA, COR_CINZA_HOVER, width=160).pack(side="left", padx=6)

    def clientes_screen(self):
        self._crud_simples(
            titulo="Clientes",
            rota_post="/clientes",
            rota_get="/clientes",
            campos=[
                ("nome", "Nome"),
                ("telefone", "Telefone"),
                ("email", "Email"),
                ("documento", "Documento"),
                ("endereco", "Endereço"),
                ("observacoes", "Observações"),
            ],
        )

    def fornecedores_screen(self):
        self._crud_simples(
            titulo="Fornecedores",
            rota_post="/fornecedores",
            rota_get="/fornecedores",
            campos=[
                ("nome", "Nome"),
                ("telefone", "Telefone"),
                ("email", "Email"),
                ("documento", "Documento"),
                ("observacoes", "Observações"),
            ],
        )

    def entregadores_screen(self):
        self._crud_simples(
            titulo="Entregadores",
            rota_post="/entregadores",
            rota_get="/entregadores",
            campos=[
                ("nome", "Nome"),
                ("telefone", "Telefone"),
            ],
        )

    def mesas_screen(self):
        self._crud_simples(
            titulo="Mesas",
            rota_post="/mesas",
            rota_get="/mesas",
            campos=[("numero", "Número da mesa")],
        )

    def colaboradores_screen(self):
        self._current_screen = self.colaboradores_screen
        self.build_shell("Colaboradores")
        self.empresa_sidebar()

        left = self._card(self.content)
        left.configure(width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self._titulo(left, "Novo colaborador")

        self.col_nome = CTkEntry(left, placeholder_text="Nome", width=320)
        self.col_nome.pack(pady=6)

        self.col_tel = CTkEntry(left, placeholder_text="Telefone", width=320)
        self.col_tel.pack(pady=6)

        self.col_email = CTkEntry(left, placeholder_text="Email", width=320)
        self.col_email.pack(pady=6)

        self.col_senha = CTkEntry(left, placeholder_text="Senha", width=320)
        self.col_senha.pack(pady=6)

        self.col_cargo = CTkEntry(left, placeholder_text="Cargo", width=320)
        self.col_cargo.pack(pady=6)

        CTkLabel(left, text="Permissões", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(pady=(12, 8))

        self.col_vars = {}
        perms_frame = CTkScrollableFrame(left, width=340, height=300, fg_color=COR_CARD_2)
        perms_frame.pack(pady=5)

        for key, label in PERMISSOES_COLABORADOR:
            var = BooleanVar(value=False)
            CTkCheckBox(perms_frame, text=label, variable=var, onvalue=True, offvalue=False).pack(anchor="w", pady=4)
            self.col_vars[key] = var

        def salvar():
            permissoes = {k: bool(v.get()) for k, v in self.col_vars.items()}
            r, data = self.request_json(
                "POST",
                f"{self.api}/colaboradores",
                json={
                    "token": self.token,
                    "nome": self.col_nome.get().strip(),
                    "telefone": self.col_tel.get().strip(),
                    "email": self.col_email.get().strip(),
                    "senha": self.col_senha.get().strip(),
                    "cargo": self.col_cargo.get().strip() or "Colaborador",
                    "permissoes": permissoes,
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Colaborador criado"))
            self.colaboradores_screen()

        self._botao(left, "Salvar Colaborador", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/colaboradores", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for col in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{col['nome']} | {col['cargo']}", font=("Arial", 15, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 3))
            CTkLabel(card, text=f"{col['email']} | {'Ativo' if col['ativo'] else 'Inativo'}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 10))

    # ================= ADMIN =================

    def admin_empresas_screen(self):
        self._current_screen = self.admin_empresas_screen
        self.build_shell("Admin - Empresas")
        self.admin_sidebar()

        left = self._card(self.content)
        left.configure(width=390)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self._titulo(left, "Criar empresa")

        self.admin_nome = CTkEntry(left, placeholder_text="Nome da empresa", width=300)
        self.admin_nome.pack(pady=6)
        self.admin_email = CTkEntry(left, placeholder_text="Email", width=300)
        self.admin_email.pack(pady=6)
        self.admin_senha = CTkEntry(left, placeholder_text="Senha", width=300)
        self.admin_senha.pack(pady=6)

        def criar():
            r, data = self.request_json(
                "POST",
                f"{self.api}/admin/empresa",
                params={"token": self.token},
                json={
                    "nome": self.admin_nome.get().strip(),
                    "email": self.admin_email.get().strip(),
                    "senha": self.admin_senha.get().strip(),
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Empresa criada"))
            self.admin_empresas_screen()

        self._botao(left, "Criar Empresa", criar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, empresas = self.request_json("GET", f"{self.api}/admin/empresas", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", empresas)
            return

        for emp in empresas:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=6)

            CTkLabel(card, text=f"{emp['nome']} | ID {emp['id']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Email: {emp['email']}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10)
            CTkLabel(card, text=f"Plano: {emp.get('plano_nome', '-')} | Status: {emp.get('status', '-')}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10)
            CTkLabel(card, text=f"Limite de terminais: {emp.get('limite_terminais', 1)} | Limite de impressoras: {emp.get('limite_impressoras', 0)}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 8))

            btns = CTkFrame(card, fg_color="transparent")
            btns.pack(anchor="e", padx=10, pady=(0, 10))

            self._botao(btns, "Ver módulos", lambda eid=emp["id"]: self.admin_modulos_popup(eid), COR_AZUL, COR_AZUL_HOVER, width=120).pack(side="left", padx=4)
            self._botao(btns, "Terminais", lambda e=emp: self.admin_limites_popup(e), COR_LARANJA, COR_LARANJA_HOVER, width=120).pack(side="left", padx=4)
            self._botao(btns, "Impressoras", lambda e=emp: self.admin_impressoras_popup(e), COR_CINZA, COR_CINZA_HOVER, width=120).pack(side="left", padx=4)

    def admin_modulos_popup(self, empresa_id):
        top = CTkToplevel(self)
        top.title(f"Módulos da empresa {empresa_id}")
        top.geometry("520x620")
        top.configure(fg_color=COR_FUNDO)

        frame = CTkScrollableFrame(top, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        r, modulos = self.request_json("GET", f"{self.api}/admin/empresa/modulos", params={"token": self.token, "empresa_id": empresa_id})
        if r.status_code != 200:
            self.api_error("Erro", modulos)
            return

        checks = {}
        for mod in modulos:
            var = BooleanVar(value=bool(mod["ativo"]))
            CTkCheckBox(frame, text=mod["modulo"], variable=var, onvalue=True, offvalue=False).pack(anchor="w", padx=12, pady=5)
            checks[mod["modulo"]] = var

        def salvar():
            payload = {nome: bool(var.get()) for nome, var in checks.items()}
            r2, data2 = self.request_json(
                "POST",
                f"{self.api}/admin/empresa/modulos/salvar",
                json={"token": self.token, "empresa_id": empresa_id, "modulos": payload},
            )
            if r2.status_code != 200:
                self.api_error("Erro", data2)
                return
            messagebox.showinfo("Sucesso", data2.get("msg", "Módulos atualizados"))
            top.destroy()

        self._botao(frame, "Salvar módulos", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=15)

    def admin_limites_popup(self, empresa):
        top = CTkToplevel(self)
        top.title(f"Terminais e Impressoras - {empresa['nome']}")
        top.geometry("460x330")
        top.configure(fg_color=COR_FUNDO)

        frame = self._card(top)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        self._titulo(frame, empresa["nome"])

        CTkLabel(frame, text="Quantidade de terminais liberados", text_color=COR_TEXTO).pack(anchor="w", padx=20, pady=(6, 2))
        terminais = CTkOptionMenu(frame, values=[str(i) for i in range(1, 21)], width=260)
        terminais.set(str(empresa.get("limite_terminais", 1)))
        terminais.pack(padx=20, pady=4, anchor="w")

        CTkLabel(frame, text="Quantidade de impressoras liberadas", text_color=COR_TEXTO).pack(anchor="w", padx=20, pady=(12, 2))
        impressoras = CTkOptionMenu(frame, values=[str(i) for i in range(0, 21)], width=260)
        impressoras.set(str(empresa.get("limite_impressoras", 0)))
        impressoras.pack(padx=20, pady=4, anchor="w")

        def salvar():
            r, data = self.request_json(
                "POST",
                f"{self.api}/admin/empresa/limites",
                json={
                    "token": self.token,
                    "empresa_id": empresa["id"],
                    "limite_terminais": int(terminais.get()),
                    "limite_impressoras": int(impressoras.get()),
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Limites atualizados"))
            top.destroy()
            self.admin_empresas_screen()

        self._botao(frame, "Salvar limites", salvar, COR_VERDE, COR_VERDE_HOVER, width=260).pack(pady=20)

    def admin_impressoras_popup(self, empresa):
        top = CTkToplevel(self)
        top.title(f"Impressoras - {empresa['nome']}")
        top.geometry("760x620")
        top.configure(fg_color=COR_FUNDO)

        left = self._card(top)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        right = CTkScrollableFrame(top, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self._titulo(left, "Nova impressora")

        nome = CTkEntry(left, placeholder_text="Nome", width=260)
        nome.pack(pady=6)
        tipo = CTkOptionMenu(left, values=["cozinha", "bar", "balcao", "entrega", "fiscal"], width=260)
        tipo.pack(pady=6)
        conexao = CTkEntry(left, placeholder_text="Conexão / IP / USB", width=260)
        conexao.pack(pady=6)
        modelo = CTkEntry(left, placeholder_text="Modelo", width=260)
        modelo.pack(pady=6)

        def salvar():
            r, data = self.request_json(
                "POST",
                f"{self.api}/admin/impressoras",
                json={
                    "token": self.token,
                    "empresa_id": empresa["id"],
                    "nome": nome.get().strip(),
                    "tipo": tipo.get(),
                    "conexao": conexao.get().strip(),
                    "modelo": modelo.get().strip(),
                    "ativa": True,
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Impressora cadastrada"))
            top.destroy()
            self.admin_impressoras_popup(empresa)

        self._botao(left, "Salvar Impressora", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/admin/impressoras", params={"token": self.token, "empresa_id": empresa["id"]})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for imp in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{imp['nome']} | {imp['tipo']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Conexão: {imp.get('conexao', '')} | Modelo: {imp.get('modelo', '')}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 10))

    # ================= COLABORADOR =================

    def colaborador_dashboard_screen(self):
        self._current_screen = self.colaborador_dashboard_screen
        self.build_shell("Colaborador - Dashboard")
        self.colaborador_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo(box, f"Bem-vindo, {self.usuario_nome}")
        CTkLabel(box, text=f"Cargo: {self.usuario_cargo}", font=("Arial", 18), text_color=COR_SUBTEXTO).pack(anchor="w", padx=14, pady=6)

    # ================= PLACEHOLDERS =================

    def placeholder_screen(self, titulo):
        self._current_screen = lambda: self.placeholder_screen(titulo)
        self.build_shell(titulo)
        if self.usuario_tipo == "colaborador":
            self.colaborador_sidebar()
        else:
            self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo(box, titulo)

    def placeholder_screen_empresa(self):
        self.placeholder_screen("Empresa")

    def placeholder_screen_comandas(self):
        self.placeholder_screen("Comandas")

    def placeholder_screen_pedidos(self):
        self.placeholder_screen("Pedidos")


if __name__ == "__main__":
    app = App()
    app.mainloop()