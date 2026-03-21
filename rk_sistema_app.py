import requests
from tkinter import messagebox
from customtkinter import *

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


class App(CTk):
    def __init__(self):
        super().__init__()
        self.title("RK Sistemas Completo")
        self.geometry("1500x880")

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

        self.login_screen()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

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

    def build_shell(self, title):
        self.clear()

        top = CTkFrame(self, height=70)
        top.pack(fill="x", padx=10, pady=10)

        CTkLabel(top, text=title, font=("Arial", 24, "bold")).pack(side="left", padx=15)

        right = CTkFrame(top, fg_color="transparent")
        right.pack(side="right", padx=10)

        if self.usuario_tipo == "empresa":
            CTkLabel(right, text=f"Plano: {self.plano_nome}", font=("Arial", 12)).pack(side="left", padx=8)

        if self.usuario_nome:
            CTkLabel(
                right,
                text=f"{self.usuario_nome} | {self.usuario_cargo}",
                font=("Arial", 13, "bold")
            ).pack(side="left", padx=10)

        CTkButton(right, text="Atualizar", width=90, command=self.refresh_screen).pack(side="left", padx=4)
        CTkButton(right, text="Sair", width=80, command=self.login_screen).pack(side="left", padx=4)

        main = CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.sidebar = CTkFrame(main, width=260)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)

        self.content = CTkFrame(main)
        self.content.pack(side="right", fill="both", expand=True)

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

    def login_screen(self):
        self.clear()
        self.token = None
        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"
        self.modulos_ativos = []
        self.permissoes_colaborador = {}

        box = CTkFrame(self)
        box.pack(expand=True, padx=20, pady=20)

        CTkLabel(box, text="RK Sistemas", font=("Arial", 30, "bold")).pack(pady=(25, 10))
        CTkLabel(box, text="Acesso ao sistema", font=("Arial", 16)).pack(pady=(0, 15))

        tipo_frame = CTkFrame(box)
        tipo_frame.pack(fill="x", padx=20, pady=10)

        CTkLabel(tipo_frame, text="Tipo de login", font=("Arial", 15, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
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

        CTkButton(box, text="Entrar", width=220, height=42, command=self.do_login).pack(pady=18)

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

    def admin_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Painel Admin", font=("Arial", 18, "bold")).pack(pady=15)
        CTkButton(self.sidebar, text="Empresas", command=self.admin_empresas_screen).pack(fill="x", padx=12, pady=5)

    def empresa_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Empresa", font=("Arial", 18, "bold")).pack(pady=15)

        botoes = [
            ("Dashboard", self.dashboard_screen),
            ("Colaboradores", self.colaboradores_screen),
        ]

        for texto, cmd in botoes:
            CTkButton(self.sidebar, text=texto, command=cmd).pack(fill="x", padx=12, pady=4)

    def colaborador_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Colaborador", font=("Arial", 18, "bold")).pack(pady=15)
        CTkButton(self.sidebar, text="Dashboard", command=self.colaborador_dashboard_screen).pack(fill="x", padx=12, pady=4)

        for key, label in PERMISSOES_COLABORADOR:
            if self.has_colab_perm(key):
                CTkButton(
                    self.sidebar,
                    text=label,
                    command=lambda l=label: self.colab_perm_screen(l)
                ).pack(fill="x", padx=12, pady=4)

    def admin_empresas_screen(self):
        self._current_screen = self.admin_empresas_screen
        self.build_shell("Admin - Empresas")
        self.admin_sidebar()

        left = CTkFrame(self.content, width=390)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Criar empresa", font=("Arial", 18, "bold")).pack(pady=15)

        self.admin_nome = CTkEntry(left, placeholder_text="Nome da empresa", width=300)
        self.admin_nome.pack(pady=6)

        self.admin_email = CTkEntry(left, placeholder_text="Email", width=300)
        self.admin_email.pack(pady=6)

        self.admin_senha = CTkEntry(left, placeholder_text="Senha", width=300)
        self.admin_senha.pack(pady=6)

        CTkButton(left, text="Criar Empresa", command=self.admin_criar_empresa).pack(pady=12)

        r, empresas = self.request_json("GET", f"{self.api}/admin/empresas", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", empresas, "Falha ao carregar empresas")
            return

        for emp in empresas:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=6)

            CTkLabel(card, text=f"{emp['nome']} | ID {emp['id']}", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Email: {emp['email']}").pack(anchor="w", padx=10)
            CTkLabel(card, text=f"Plano: {emp.get('plano_nome', '-')} | Status: {emp.get('status', '-')}").pack(anchor="w", padx=10, pady=(2, 10))

            CTkButton(card, text="Ver módulos", command=lambda eid=emp["id"]: self.admin_modulos_popup(eid)).pack(anchor="e", padx=10, pady=(0, 10))

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

        frame = CTkScrollableFrame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(frame, text=f"Módulos - Empresa {empresa_id}", font=("Arial", 20, "bold")).pack(pady=10)

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

        CTkButton(frame, text="Salvar módulos", command=salvar).pack(pady=15)

    def dashboard_screen(self):
        self._current_screen = self.dashboard_screen
        self.load_empresa_context()
        self.build_shell("Empresa - Dashboard")
        self.empresa_sidebar()

        box = CTkFrame(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        CTkLabel(box, text="Dashboard", font=("Arial", 24, "bold")).pack(pady=15)
        CTkLabel(box, text=f"Plano: {self.plano_nome}").pack(pady=6)
        CTkLabel(box, text=f"Módulos ativos: {', '.join(self.modulos_ativos) if self.modulos_ativos else 'Nenhum'}", wraplength=1000, justify="left").pack(pady=6)

    def colaboradores_screen(self):
        self._current_screen = self.colaboradores_screen
        self.build_shell("Colaboradores")
        self.empresa_sidebar()

        left = CTkFrame(self.content, width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Novo colaborador", font=("Arial", 18, "bold")).pack(pady=15)

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

        CTkLabel(left, text="Permissões", font=("Arial", 16, "bold")).pack(pady=(12, 8))

        self.col_vars = {}
        perms_frame = CTkScrollableFrame(left, width=340, height=300)
        perms_frame.pack(pady=5)

        for key, label in PERMISSOES_COLABORADOR:
            var = BooleanVar(value=False)
            ck = CTkCheckBox(perms_frame, text=label, variable=var, onvalue=True, offvalue=False)
            ck.pack(anchor="w", pady=4)
            self.col_vars[key] = var

        CTkButton(left, text="Salvar Colaborador", command=self.criar_colaborador).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/colaboradores", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data, "Falha ao carregar colaboradores")
            return

        for col in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)

            CTkLabel(card, text=f"{col['nome']} | {col['cargo']}", font=("Arial", 15, "bold")).pack(anchor="w", padx=10, pady=(10, 3))
            CTkLabel(card, text=f"{col['email']} | {'Ativo' if col['ativo'] else 'Inativo'}").pack(anchor="w", padx=10)

            perms = col.get("permissoes", {})
            ativas = [label for key, label in PERMISSOES_COLABORADOR if perms.get(key)]
            CTkLabel(
                card,
                text="Permissões: " + (", ".join(ativas) if ativas else "Nenhuma"),
                wraplength=850,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(3, 8))

            CTkButton(
                card,
                text="Editar permissões",
                command=lambda c=col: self.editar_permissoes_popup(c)
            ).pack(anchor="e", padx=10, pady=(0, 10))

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

        frame = CTkScrollableFrame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(frame, text=colaborador["nome"], font=("Arial", 20, "bold")).pack(pady=8)

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

        CTkButton(frame, text="Salvar permissões", command=salvar).pack(pady=15)

    def colaborador_dashboard_screen(self):
        self._current_screen = self.colaborador_dashboard_screen
        self.build_shell("Colaborador - Dashboard")
        self.colaborador_sidebar()

        box = CTkFrame(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        CTkLabel(box, text=f"Bem-vindo, {self.usuario_nome}", font=("Arial", 24, "bold")).pack(pady=15)
        CTkLabel(box, text=f"Cargo: {self.usuario_cargo}", font=("Arial", 18)).pack(pady=6)

        liberadas = [label for key, label in PERMISSOES_COLABORADOR if self.permissoes_colaborador.get(key)]
        CTkLabel(box, text="Permissões liberadas:", font=("Arial", 18, "bold")).pack(pady=(18, 8))
        CTkLabel(box, text=", ".join(liberadas) if liberadas else "Nenhuma", wraplength=1000, justify="left").pack(pady=6)

    def colab_perm_screen(self, titulo):
        self._current_screen = lambda: self.colab_perm_screen(titulo)
        self.build_shell(titulo)
        self.colaborador_sidebar()

        box = CTkFrame(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        CTkLabel(box, text=titulo, font=("Arial", 24, "bold")).pack(pady=20)
        CTkLabel(box, text=f"Tela liberada para {self.usuario_nome}.").pack(pady=8)


if __name__ == "__main__":
    app = App()
    app.mainloop()