import os
import requests
from tkinter import messagebox
from customtkinter import *
from PIL import Image

set_appearance_mode("dark")
set_default_color_theme("blue")

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
    ("configuracoes", "Configurações"),
    ("whatsapp", "WhatsApp"),
    ("aiqfome", "aiqfome"),
    ("comer_aqui", "Comer Aqui"),
]

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


class App(CTk):
    def __init__(self):
        super().__init__()

        self.title("GSI Sistemas")
        self.geometry("1500x880")
        self.configure(fg_color=COR_FUNDO)

        self.api = "https://rk-sistemas1.onrender.com"
        self.token = None
        self.tipo_login = StringVar(value="empresa")

        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"
        self.modulos_ativos = []
        self.permissoes_colaborador = {}

        self.sidebar = None
        self.content = None
        self._current_screen = None

        self.logo_top = None
        self.logo_login = None
        self.logo_bg = None
        self._carregar_logo()

        self.login_screen()

    # =========================================================
    # VISUAL
    # =========================================================

    def _carregar_logo(self):
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                self.logo_top = CTkImage(light_image=img, dark_image=img, size=(110, 55))
                self.logo_login = CTkImage(light_image=img, dark_image=img, size=(180, 90))
                self.logo_bg = CTkImage(light_image=img, dark_image=img, size=(650, 320))
            except Exception:
                self.logo_top = None
                self.logo_login = None
                self.logo_bg = None

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _marca_dagua(self, parent, relx=0.60, rely=0.50):
        if self.logo_bg:
            lbl = CTkLabel(parent, text="", image=self.logo_bg)
            lbl.place(relx=relx, rely=rely, anchor="center")

    def _card(self, parent):
        return CTkFrame(
            parent,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )

    def _titulo_card(self, parent, text):
        CTkLabel(
            parent,
            text=text,
            font=("Arial", 20, "bold"),
            text_color=COR_TEXTO
        ).pack(anchor="w", padx=14, pady=(14, 8))

    def _botao(self, parent, text, command, color=COR_AZUL, hover=COR_AZUL_HOVER, **kwargs):
        return CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=color,
            hover_color=hover,
            text_color="white",
            corner_radius=10,
            **kwargs
        )

    # =========================================================
    # API
    # =========================================================

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
            self.modulos_ativos = data.get("modulos_ativos", [])
        else:
            self.plano_nome = "—"
            self.modulos_ativos = []

    def has_colab_perm(self, perm):
        if self.usuario_tipo != "colaborador":
            return True
        return bool(self.permissoes_colaborador.get(perm, False))

    # =========================================================
    # LOGIN
    # =========================================================

    def login_screen(self):
        self.clear()
        self.token = None
        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"
        self.modulos_ativos = []
        self.permissoes_colaborador = {}

        base = CTkFrame(self, fg_color=COR_FUNDO)
        base.pack(fill="both", expand=True)

        self._marca_dagua(base, relx=0.5, rely=0.5)

        box = CTkFrame(
            base,
            fg_color=COR_CARD,
            corner_radius=18,
            border_width=1,
            border_color=COR_BORDA
        )
        box.pack(expand=True, padx=20, pady=20)

        if self.logo_login:
            CTkLabel(box, text="", image=self.logo_login).pack(pady=(20, 6))
        else:
            CTkLabel(box, text="GSI", font=("Arial", 30, "bold"), text_color=COR_AZUL).pack(pady=(24, 6))

        CTkLabel(box, text="GSI Sistemas", font=("Arial", 30, "bold"), text_color=COR_TEXTO).pack(pady=(0, 4))
        CTkLabel(box, text="Acesso ao sistema", font=("Arial", 16), text_color=COR_SUBTEXTO).pack(pady=(0, 15))

        tipo_frame = CTkFrame(box, fg_color=COR_CARD_2, corner_radius=12)
        tipo_frame.pack(fill="x", padx=20, pady=10)

        CTkLabel(tipo_frame, text="Tipo de login", font=("Arial", 15, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 5))
        CTkRadioButton(tipo_frame, text="Empresa", variable=self.tipo_login, value="empresa").pack(anchor="w", padx=15, pady=3)
        CTkRadioButton(tipo_frame, text="Admin Global", variable=self.tipo_login, value="admin").pack(anchor="w", padx=15, pady=3)
        CTkRadioButton(tipo_frame, text="Colaborador", variable=self.tipo_login, value="colaborador").pack(anchor="w", padx=15, pady=(3, 10))

        self.login_email = CTkEntry(box, width=360, placeholder_text="Email")
        self.login_email.pack(pady=8)

        self.login_senha = CTkEntry(box, width=360, placeholder_text="Senha", show="*")
        self.login_senha.pack(pady=8)

        self.login_api = CTkEntry(box, width=360)
        self.login_api.insert(0, self.api)
        self.login_api.pack(pady=8)

        self._botao(
            box,
            "Entrar",
            self.do_login,
            color=COR_AZUL,
            hover=COR_AZUL_HOVER,
            width=220,
            height=42
        ).pack(pady=18)

    def do_login(self):
        self.api = self.login_api.get().strip()
        email = self.login_email.get().strip()
        senha = self.login_senha.get().strip()

        rota = {
            "empresa": "/empresa/login",
            "admin": "/admin/login",
            "colaborador": "/colaborador/login",
        }[self.tipo_login.get()]

        r, data = self.request_json("POST", f"{self.api}{rota}", json={"email": email, "senha": senha})
        if r.status_code != 200:
            self.api_error("Erro de login", data, "Não foi possível entrar")
            return

        self.token = data["token"]
        self.usuario_tipo = self.tipo_login.get()
        self.usuario_nome = data.get("nome", "")
        self.usuario_cargo = data.get("cargo", "")

        if self.usuario_tipo == "empresa":
            self.load_empresa_context()
            if not self.usuario_nome:
                self.usuario_nome = "Admin do Estabelecimento"
                self.usuario_cargo = "Administrador"
            self.dashboard_screen()
        elif self.usuario_tipo == "admin":
            self.usuario_nome = "Admin Global"
            self.usuario_cargo = "Administrador"
            self.admin_empresas_screen()
        else:
            self.permissoes_colaborador = data.get("permissoes", {})
            self.colaborador_dashboard_screen()

    # =========================================================
    # SHELL
    # =========================================================

    def build_shell(self, title):
        self.clear()

        fundo = CTkFrame(self, fg_color=COR_FUNDO)
        fundo.pack(fill="both", expand=True)

        top = CTkFrame(
            fundo,
            height=76,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )
        top.pack(fill="x", padx=10, pady=10)

        left_top = CTkFrame(top, fg_color="transparent")
        left_top.pack(side="left", padx=12)

        if self.logo_top:
            CTkLabel(left_top, text="", image=self.logo_top).pack(side="left", padx=(4, 8), pady=8)
        else:
            CTkLabel(left_top, text="GSI", font=("Arial", 22, "bold"), text_color=COR_AZUL).pack(side="left", padx=(4, 8))

        CTkLabel(left_top, text=title, font=("Arial", 24, "bold"), text_color=COR_TEXTO).pack(side="left", padx=8)

        right = CTkFrame(top, fg_color="transparent")
        right.pack(side="right", padx=12)

        if self.usuario_tipo == "empresa":
            CTkLabel(right, text=f"Plano: {self.plano_nome}", font=("Arial", 12), text_color=COR_SUBTEXTO).pack(side="left", padx=8)

        if self.usuario_nome:
            CTkLabel(
                right,
                text=f"{self.usuario_nome} | {self.usuario_cargo}",
                font=("Arial", 13, "bold"),
                text_color=COR_TEXTO
            ).pack(side="left", padx=10)

        # botão 3 barras no lugar de configurações
        self._botao(right, "☰", self.config_popup, color=COR_CINZA, hover=COR_CINZA_HOVER, width=42).pack(side="left", padx=4)
        self._botao(right, "Atualizar", self.refresh_screen, color=COR_LARANJA, hover=COR_LARANJA_HOVER, width=96).pack(side="left", padx=4)
        self._botao(right, "Sair", self.login_screen, color=COR_VERMELHO, hover=COR_VERMELHO_HOVER, width=80).pack(side="left", padx=4)

        main = CTkFrame(fundo, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.sidebar = CTkFrame(
            main,
            width=270,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)

        self.content = CTkFrame(main, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)

        self._marca_dagua(self.content, relx=0.68, rely=0.55)

    # =========================================================
    # SIDEBARS
    # =========================================================

    def admin_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Painel Admin", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(pady=15)
        self._botao(self.sidebar, "Empresas", self.admin_empresas_screen, color=COR_AZUL, hover=COR_AZUL_HOVER).pack(fill="x", padx=12, pady=5)

    def empresa_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Empresa", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(pady=15)

        botoes = [
            ("Dashboard", self.dashboard_screen, COR_AZUL, COR_AZUL_HOVER),
            ("Cadastro", self.cadastro_screen, COR_VERDE, COR_VERDE_HOVER),
            ("Operação", self.operacao_screen, COR_LARANJA, COR_LARANJA_HOVER),
            ("Relatórios", lambda: self.placeholder_screen("Relatórios"), COR_CINZA, COR_CINZA_HOVER),
            ("WhatsApp", lambda: self.placeholder_screen("WhatsApp"), COR_VERDE, COR_VERDE_HOVER),
            ("aiqfome", lambda: self.placeholder_screen("aiqfome"), COR_AZUL, COR_AZUL_HOVER),
            ("Comer Aqui", lambda: self.placeholder_screen("Comer Aqui"), COR_AZUL, COR_AZUL_HOVER),
        ]

        for texto, cmd, cor, hover in botoes:
            self._botao(self.sidebar, texto, cmd, color=cor, hover=hover).pack(fill="x", padx=12, pady=4)

    def colaborador_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Colaborador", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(pady=15)
        self._botao(self.sidebar, "Dashboard", self.colaborador_dashboard_screen, color=COR_AZUL, hover=COR_AZUL_HOVER).pack(fill="x", padx=12, pady=4)

        cores = [COR_AZUL, COR_VERDE, COR_LARANJA, COR_CINZA]
        hovers = [COR_AZUL_HOVER, COR_VERDE_HOVER, COR_LARANJA_HOVER, COR_CINZA_HOVER]

        idx = 0
        for key, label in PERMISSOES_COLABORADOR:
            if self.has_colab_perm(key):
                cor = cores[idx % len(cores)]
                hov = hovers[idx % len(hovers)]
                self._botao(
                    self.sidebar,
                    label,
                    lambda l=label: self.colab_perm_screen(l),
                    color=cor,
                    hover=hov
                ).pack(fill="x", padx=12, pady=4)
                idx += 1

    # =========================================================
    # POPUP CONFIG
    # =========================================================

    def config_popup(self):
        top = CTkToplevel(self)
        top.title("Configurações")
        top.geometry("360x360")
        top.configure(fg_color=COR_FUNDO)

        frame = self._card(top)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        CTkLabel(frame, text="Configurações", font=("Arial", 20, "bold"), text_color=COR_TEXTO).pack(pady=14)

        self._botao(frame, "Empresa", lambda: self.placeholder_screen("Empresa"), color=COR_AZUL, hover=COR_AZUL_HOVER, width=240).pack(pady=6)
        self._botao(frame, "Impressora", lambda: self.placeholder_screen("Impressora"), color=COR_CINZA, hover=COR_CINZA_HOVER, width=240).pack(pady=6)
        self._botao(frame, "Pagamentos", lambda: self.placeholder_screen("Pagamentos"), color=COR_VERDE, hover=COR_VERDE_HOVER, width=240).pack(pady=6)
        self._botao(frame, "Integrações", lambda: self.placeholder_screen("Integrações"), color=COR_LARANJA, hover=COR_LARANJA_HOVER, width=240).pack(pady=6)
        self._botao(frame, "Fechar", top.destroy, color=COR_VERMELHO, hover=COR_VERMELHO_HOVER, width=240).pack(pady=14)

    # =========================================================
    # ADMIN
    # =========================================================

    def admin_empresas_screen(self):
        self._current_screen = self.admin_empresas_screen
        self.build_shell("Admin - Empresas")
        self.admin_sidebar()

        left = self._card(self.content)
        left.configure(width=390)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(
            self.content,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self._titulo_card(left, "Criar empresa")

        self.admin_nome = CTkEntry(left, placeholder_text="Nome da empresa", width=300)
        self.admin_nome.pack(pady=6)

        self.admin_email = CTkEntry(left, placeholder_text="Email", width=300)
        self.admin_email.pack(pady=6)

        self.admin_senha = CTkEntry(left, placeholder_text="Senha", width=300)
        self.admin_senha.pack(pady=6)

        self._botao(left, "Criar Empresa", self.admin_criar_empresa, color=COR_VERDE, hover=COR_VERDE_HOVER).pack(pady=12)

        r, empresas = self.request_json("GET", f"{self.api}/admin/empresas", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", empresas, "Falha ao carregar empresas")
            return

        for emp in empresas:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=6)

            CTkLabel(card, text=f"{emp['nome']} | ID {emp['id']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Email: {emp['email']}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10)
            CTkLabel(
                card,
                text=f"Plano: {emp.get('plano_nome', '-')} | Status: {emp.get('status', '-')}",
                text_color=COR_SUBTEXTO
            ).pack(anchor="w", padx=10, pady=(2, 10))

            self._botao(card, "Ver módulos", lambda eid=emp["id"]: self.admin_modulos_popup(eid), color=COR_AZUL, hover=COR_AZUL_HOVER, width=130).pack(anchor="e", padx=10, pady=(0, 10))

    def admin_criar_empresa(self):
        r, data = self.request_json(
            "POST",
            f"{self.api}/admin/empresa",
            params={"token": self.token},
            json={
                "nome": self.admin_nome.get().strip(),
                "email": self.admin_email.get().strip(),
                "senha": self.admin_senha.get().strip()
            }
        )
        if r.status_code != 200:
            self.api_error("Erro", data, "Falha ao criar empresa")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Empresa criada"))
        self.admin_empresas_screen()

    def admin_modulos_popup(self, empresa_id):
        top = CTkToplevel(self)
        top.title(f"Módulos da empresa {empresa_id}")
        top.geometry("520x620")
        top.configure(fg_color=COR_FUNDO)

        frame = CTkScrollableFrame(
            top,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(frame, text=f"Módulos - Empresa {empresa_id}", font=("Arial", 20, "bold"), text_color=COR_TEXTO).pack(pady=10)

        r, modulos = self.request_json(
            "GET",
            f"{self.api}/admin/empresa/modulos",
            params={"token": self.token, "empresa_id": empresa_id}
        )
        if r.status_code != 200:
            self.api_error("Erro", modulos, "Falha ao carregar módulos")
            return

        checks = {}
        for mod in modulos:
            var = BooleanVar(value=bool(mod["ativo"]))
            ck = CTkCheckBox(frame, text=mod["modulo"], variable=var, onvalue=True, offvalue=False)
            ck.pack(anchor="w", padx=12, pady=5)
            checks[mod["modulo"]] = var

        def salvar():
            payload = {nome: bool(var.get()) for nome, var in checks.items()}
            r2, data2 = self.request_json(
                "POST",
                f"{self.api}/admin/empresa/modulos/salvar",
                json={"token": self.token, "empresa_id": empresa_id, "modulos": payload}
            )
            if r2.status_code != 200:
                self.api_error("Erro", data2, "Falha ao salvar módulos")
                return
            messagebox.showinfo("Sucesso", data2.get("msg", "Módulos atualizados"))
            top.destroy()

        self._botao(frame, "Salvar módulos", salvar, color=COR_VERDE, hover=COR_VERDE_HOVER).pack(pady=15)

    # =========================================================
    # EMPRESA
    # =========================================================

    def dashboard_screen(self):
        self._current_screen = self.dashboard_screen
        self.load_empresa_context()
        self.build_shell("Dashboard")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        self._titulo_card(box, "Dashboard")

        CTkLabel(box, text=f"Plano: {self.plano_nome}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=14, pady=4)
        CTkLabel(
            box,
            text=f"Módulos ativos: {', '.join(self.modulos_ativos) if self.modulos_ativos else 'Nenhum'}",
            wraplength=1000,
            justify="left",
            text_color=COR_SUBTEXTO
        ).pack(anchor="w", padx=14, pady=4)

        resumo = CTkFrame(box, fg_color="transparent")
        resumo.pack(fill="x", padx=14, pady=18)

        self._botao(resumo, "Cadastro", self.cadastro_screen, color=COR_VERDE, hover=COR_VERDE_HOVER, width=180, height=46).pack(side="left", padx=6)
        self._botao(resumo, "Operação", self.operacao_screen, color=COR_LARANJA, hover=COR_LARANJA_HOVER, width=180, height=46).pack(side="left", padx=6)
        self._botao(resumo, "Relatórios", lambda: self.placeholder_screen("Relatórios"), color=COR_CINZA, hover=COR_CINZA_HOVER, width=180, height=46).pack(side="left", padx=6)

    # =========================================================
    # CADASTRO
    # =========================================================

    def cadastro_screen(self):
        self._current_screen = self.cadastro_screen
        self.build_shell("Cadastro")
        self.empresa_sidebar()

        self._render_submenu(
            titulo="Cadastro",
            botoes=[
                ("Cliente", self.clientes_screen, COR_VERDE, COR_VERDE_HOVER),
                ("Fornecedor", self.fornecedores_screen, COR_VERDE, COR_VERDE_HOVER),
                ("Colabora", self.colaboradores_screen, COR_AZUL, COR_AZUL_HOVER),
                ("Entregadores", self.entregadores_screen, COR_LARANJA, COR_LARANJA_HOVER),
                ("Empresa", self.empresa_cadastro_screen, COR_CINZA, COR_CINZA_HOVER),
            ]
        )

    def clientes_screen(self):
        self._current_screen = self.clientes_screen
        self.build_shell("Cadastro - Cliente")
        self.empresa_sidebar()
        self._simple_box("Clientes", "Tela de cliente mantida dentro de Cadastro.")

    def fornecedores_screen(self):
        self._current_screen = self.fornecedores_screen
        self.build_shell("Cadastro - Fornecedor")
        self.empresa_sidebar()
        self._simple_box("Fornecedores", "Tela de fornecedor mantida dentro de Cadastro.")

    def empresa_cadastro_screen(self):
        self._current_screen = self.empresa_cadastro_screen
        self.build_shell("Cadastro - Empresa")
        self.empresa_sidebar()
        self._simple_box("Empresa", "Dados da empresa ficam aqui.")

    def entregadores_screen(self):
        self._current_screen = self.entregadores_screen
        self.build_shell("Cadastro - Entregadores")
        self.empresa_sidebar()
        self._simple_box("Entregadores", "Tela de entregadores mantida dentro de Cadastro.")

    def colaboradores_screen(self):
        self._current_screen = self.colaboradores_screen
        self.build_shell("Cadastro - Colaboradores")
        self.empresa_sidebar()

        left = self._card(self.content)
        left.configure(width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(
            self.content,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self._titulo_card(left, "Novo colaborador")

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
            ck = CTkCheckBox(perms_frame, text=label, variable=var, onvalue=True, offvalue=False)
            ck.pack(anchor="w", pady=4)
            self.col_vars[key] = var

        self._botao(left, "Salvar Colaborador", self.criar_colaborador, color=COR_VERDE, hover=COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/colaboradores", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data, "Falha ao carregar colaboradores")
            return

        for col in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)

            CTkLabel(card, text=f"{col['nome']} | {col['cargo']}", font=("Arial", 15, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 3))
            CTkLabel(card, text=f"{col['email']} | {'Ativo' if col['ativo'] else 'Inativo'}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10)

            perms = col.get("permissoes", {})
            ativas = [label for key, label in PERMISSOES_COLABORADOR if perms.get(key)]
            CTkLabel(
                card,
                text="Permissões: " + (", ".join(ativas) if ativas else "Nenhuma"),
                wraplength=850,
                justify="left",
                text_color=COR_SUBTEXTO
            ).pack(anchor="w", padx=10, pady=(3, 8))

            self._botao(card, "Editar permissões", lambda c=col: self.editar_permissoes_popup(c), color=COR_AZUL, hover=COR_AZUL_HOVER, width=150).pack(anchor="e", padx=10, pady=(0, 10))

    def criar_colaborador(self):
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
                "permissoes": permissoes
            }
        )
        if r.status_code != 200:
            self.api_error("Erro", data, "Falha ao criar colaborador")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Colaborador criado"))
        self.colaboradores_screen()

    def editar_permissoes_popup(self, colaborador):
        top = CTkToplevel(self)
        top.title(f"Permissões - {colaborador['nome']}")
        top.geometry("560x700")
        top.configure(fg_color=COR_FUNDO)

        frame = CTkScrollableFrame(
            top,
            fg_color=COR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COR_BORDA
        )
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(frame, text=colaborador["nome"], font=("Arial", 20, "bold"), text_color=COR_TEXTO).pack(pady=8)

        cargo = CTkEntry(frame, width=320)
        cargo.insert(0, colaborador.get("cargo", "Colaborador"))
        cargo.pack(pady=8)

        ativo_var = BooleanVar(value=bool(colaborador.get("ativo", True)))
        CTkCheckBox(frame, text="Colaborador ativo", variable=ativo_var, onvalue=True, offvalue=False).pack(anchor="w", padx=12, pady=8)

        current = colaborador.get("permissoes", {})
        checks = {}
        for key, label in PERMISSOES_COLABORADOR:
            var = BooleanVar(value=bool(current.get(key, False)))
            ck = CTkCheckBox(frame, text=label, variable=var, onvalue=True, offvalue=False)
            ck.pack(anchor="w", padx=12, pady=4)
            checks[key] = var

        def salvar():
            payload = {k: bool(v.get()) for k, v in checks.items()}
            r, data = self.request_json(
                "POST",
                f"{self.api}/colaboradores/permissoes/salvar",
                json={
                    "token": self.token,
                    "colaborador_id": colaborador["id"],
                    "cargo": cargo.get().strip() or "Colaborador",
                    "ativo": bool(ativo_var.get()),
                    "permissoes": payload
                }
            )
            if r.status_code != 200:
                self.api_error("Erro", data, "Falha ao salvar permissões")
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Permissões salvas"))
            top.destroy()
            self.colaboradores_screen()

        self._botao(frame, "Salvar permissões", salvar, color=COR_VERDE, hover=COR_VERDE_HOVER).pack(pady=15)

    # =========================================================
    # OPERAÇÃO
    # =========================================================

    def operacao_screen(self):
        self._current_screen = self.operacao_screen
        self.build_shell("Operação")
        self.empresa_sidebar()

        self._render_submenu(
            titulo="Operação",
            botoes=[
                ("Mesa", self.mesas_screen, COR_VERDE, COR_VERDE_HOVER),
                ("Pedido", self.pedidos_screen, COR_LARANJA, COR_LARANJA_HOVER),
                ("Comandas", self.comandas_screen, COR_AZUL, COR_AZUL_HOVER),
                ("KDS Cozinha", self.kds_cozinha_screen, COR_CINZA, COR_CINZA_HOVER),
                ("KDS Bar", self.kds_bar_screen, COR_CINZA, COR_CINZA_HOVER),
            ]
        )

    def mesas_screen(self):
        self._current_screen = self.mesas_screen
        self.build_shell("Operação - Mesa")
        self.empresa_sidebar()
        self._simple_box("Mesa", "Tela de mesas mantida dentro de Operação.")

    def pedidos_screen(self):
        self._current_screen = self.pedidos_screen
        self.build_shell("Operação - Pedido")
        self.empresa_sidebar()
        self._simple_box("Pedido", "Tela de pedidos mantida dentro de Operação.")

    def comandas_screen(self):
        self._current_screen = self.comandas_screen
        self.build_shell("Operação - Comandas")
        self.empresa_sidebar()
        self._simple_box("Comandas", "Tela de comandas mantida dentro de Operação.")

    def kds_cozinha_screen(self):
        self._current_screen = self.kds_cozinha_screen
        self.build_shell("Operação - KDS Cozinha")
        self.empresa_sidebar()
        self._simple_box("KDS Cozinha", "Tela KDS Cozinha mantida dentro de Operação.")

    def kds_bar_screen(self):
        self._current_screen = self.kds_bar_screen
        self.build_shell("Operação - KDS Bar")
        self.empresa_sidebar()
        self._simple_box("KDS Bar", "Tela KDS Bar mantida dentro de Operação.")

    # =========================================================
    # COLABORADOR
    # =========================================================

    def colaborador_dashboard_screen(self):
        self._current_screen = self.colaborador_dashboard_screen
        self.build_shell("Colaborador - Dashboard")
        self.colaborador_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        self._titulo_card(box, f"Bem-vindo, {self.usuario_nome}")
        CTkLabel(box, text=f"Cargo: {self.usuario_cargo}", font=("Arial", 18), text_color=COR_SUBTEXTO).pack(anchor="w", padx=14, pady=6)

        liberadas = [label for key, label in PERMISSOES_COLABORADOR if self.permissoes_colaborador.get(key)]
        CTkLabel(box, text="Permissões liberadas:", font=("Arial", 18, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=14, pady=(18, 8))
        CTkLabel(
            box,
            text=", ".join(liberadas) if liberadas else "Nenhuma",
            wraplength=1000,
            justify="left",
            text_color=COR_SUBTEXTO
        ).pack(anchor="w", padx=14, pady=6)

    def colab_perm_screen(self, titulo):
        self._current_screen = lambda: self.colab_perm_screen(titulo)
        self.build_shell(titulo)
        self.colaborador_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo_card(box, titulo)
        CTkLabel(box, text=f"Tela liberada para {self.usuario_nome}.", text_color=COR_SUBTEXTO).pack(anchor="w", padx=14, pady=8)

    # =========================================================
    # HELPERS DE TELA
    # =========================================================

    def _render_submenu(self, titulo, botoes):
        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        self._titulo_card(box, titulo)

        linha = CTkFrame(box, fg_color="transparent")
        linha.pack(fill="x", padx=14, pady=10)

        for texto, cmd, cor, hover in botoes:
            self._botao(linha, texto, cmd, color=cor, hover=hover, width=170, height=46).pack(side="left", padx=6)

        CTkLabel(
            box,
            text="As opções desta área foram agrupadas como sub-abas, sem ficar soltas no menu principal.",
            text_color=COR_SUBTEXTO,
            wraplength=1000,
            justify="left"
        ).pack(anchor="w", padx=14, pady=10)

    def _simple_box(self, titulo, descricao):
        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        self._titulo_card(box, titulo)
        CTkLabel(box, text=descricao, text_color=COR_SUBTEXTO, wraplength=950, justify="left").pack(anchor="w", padx=14, pady=8)

    def placeholder_screen(self, titulo):
        self._current_screen = lambda: self.placeholder_screen(titulo)
        self.build_shell(titulo)
        self.empresa_sidebar()
        self._simple_box(titulo, "Tela mantida no sistema e pronta para receber a lógica completa.")

if __name__ == "__main__":
    app = App()
    app.mainloop()