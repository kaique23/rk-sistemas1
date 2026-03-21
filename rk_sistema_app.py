import requests
from tkinter import messagebox
from customtkinter import *

set_appearance_mode("dark")
set_default_color_theme("blue")


# =========================================================
# APP
# =========================================================

class App(CTk):
    def __init__(self):
        super().__init__()
        self.title("RK Sistemas Completo")
        self.geometry("1480x860")

        self.api = "https://rk-sistemas1.onrender.com"

        self.token = None
        self.tipo_login = StringVar(value="empresa")
        self.usuario_tipo = None  # admin / empresa / garcom

        self.plano_nome = "—"
        self.modulos_ativos = []

        self.sidebar = None
        self.content = None

        self.login_screen()

    # =====================================================
    # BASE
    # =====================================================

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

    def show_api_error(self, title, data, fallback="Erro"):
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("raw") or fallback
        else:
            detail = str(data)
        messagebox.showerror(title, detail)

    def set_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def clear_content(self):
        if self.content:
            for w in self.content.winfo_children():
                w.destroy()

    def build_shell(self, title):
        self.clear()

        top = CTkFrame(self, height=70)
        top.pack(fill="x", padx=10, pady=10)

        CTkLabel(top, text=title, font=("Arial", 24, "bold")).pack(side="left", padx=15)

        right = CTkFrame(top, fg_color="transparent")
        right.pack(side="right", padx=10)

        if self.usuario_tipo == "empresa":
            CTkLabel(
                right,
                text=f"Plano: {self.plano_nome}",
                font=("Arial", 12)
            ).pack(side="left", padx=8)

        CTkButton(right, text="Atualizar", width=100, command=self.refresh_current_screen).pack(side="left", padx=5)
        CTkButton(right, text="Sair", width=90, command=self.login_screen).pack(side="left", padx=5)

        main = CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.sidebar = CTkFrame(main, width=250)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)

        self.content = CTkFrame(main)
        self.content.pack(side="right", fill="both", expand=True)

    def refresh_current_screen(self):
        if hasattr(self, "_current_screen") and callable(self._current_screen):
            self._current_screen()

    # =====================================================
    # LOGIN
    # =====================================================

    def login_screen(self):
        self.clear()
        self.token = None
        self.usuario_tipo = None
        self.plano_nome = "—"
        self.modulos_ativos = []

        box = CTkFrame(self)
        box.pack(expand=True, padx=20, pady=20)

        CTkLabel(box, text="RK Sistemas", font=("Arial", 30, "bold")).pack(pady=(25, 10))
        CTkLabel(box, text="Login do sistema", font=("Arial", 16)).pack(pady=(0, 15))

        tipo_frame = CTkFrame(box)
        tipo_frame.pack(fill="x", padx=20, pady=10)

        CTkLabel(tipo_frame, text="Tipo de login", font=("Arial", 15, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        CTkRadioButton(tipo_frame, text="Empresa", variable=self.tipo_login, value="empresa").pack(anchor="w", padx=15, pady=3)
        CTkRadioButton(tipo_frame, text="Admin", variable=self.tipo_login, value="admin").pack(anchor="w", padx=15, pady=3)
        CTkRadioButton(tipo_frame, text="Garçom", variable=self.tipo_login, value="garcom").pack(anchor="w", padx=15, pady=(3, 10))

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

        if not email or not senha:
            messagebox.showwarning("Aviso", "Preencha email e senha.")
            return

        tipo = self.tipo_login.get()
        rota = {
            "admin": "/admin/login",
            "empresa": "/empresa/login",
            "garcom": "/garcom/login",
        }[tipo]

        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}{rota}",
                json={"email": email, "senha": senha}
            )

            if r.status_code != 200:
                self.show_api_error("Erro de login", data, "Não foi possível entrar")
                return

            self.token = data["token"]
            self.usuario_tipo = tipo

            if tipo == "admin":
                self.admin_empresas_screen()
            elif tipo == "empresa":
                self.load_empresa_context()
                self.empresa_dashboard_screen()
            else:
                self.garcom_dashboard_screen()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao conectar ao servidor.\n{e}")

    # =====================================================
    # CONTEXTO EMPRESA
    # =====================================================

    def load_empresa_context(self):
        if self.usuario_tipo != "empresa" or not self.token:
            return

        try:
            r, data = self.request_json(
                "GET",
                f"{self.api}/empresa/plano",
                params={"token": self.token}
            )
            if r.status_code == 200:
                self.plano_nome = data.get("plano_nome", "—")
                self.modulos_ativos = data.get("modulos_ativos", [])
            else:
                self.plano_nome = "—"
                self.modulos_ativos = []
        except Exception:
            self.plano_nome = "—"
            self.modulos_ativos = []

    def has_modulo(self, modulo):
        if self.usuario_tipo != "empresa":
            return True
        return modulo in self.modulos_ativos

    # =====================================================
    # SIDEBARS
    # =====================================================

    def admin_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Painel Admin", font=("Arial", 18, "bold")).pack(pady=15)

        CTkButton(self.sidebar, text="Empresas", command=self.admin_empresas_screen).pack(fill="x", padx=12, pady=5)
        CTkButton(self.sidebar, text="Atualizar", command=self.admin_empresas_screen).pack(fill="x", padx=12, pady=5)

    def empresa_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Empresa", font=("Arial", 18, "bold")).pack(pady=15)

        botoes = [
            ("Dashboard", self.empresa_dashboard_screen),
            ("Categorias", self.categorias_screen),
            ("Produtos", self.produtos_screen),
            ("Clientes", self.clientes_screen),
            ("Fornecedores", self.fornecedores_screen),
            ("Funcionários", self.funcionarios_screen),
            ("Mesas", self.mesas_screen),
            ("Comandas", self.comandas_screen),
            ("Pedidos", self.pedidos_screen),
            ("KDS Cozinha", self.kds_cozinha_screen),
            ("KDS Bar", self.kds_bar_screen),
            ("Entregadores", self.entregadores_screen),
            ("Chamados", self.chamados_screen),
            ("Configurações", self.config_screen),
        ]

        for texto, cmd in botoes:
            CTkButton(self.sidebar, text=texto, command=cmd).pack(fill="x", padx=12, pady=4)

    def garcom_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        CTkLabel(self.sidebar, text="Módulo Garçom", font=("Arial", 18, "bold")).pack(pady=15)

        CTkButton(self.sidebar, text="Dashboard", command=self.garcom_dashboard_screen).pack(fill="x", padx=12, pady=4)
        CTkButton(self.sidebar, text="Mesas", command=self.garcom_mesas_screen).pack(fill="x", padx=12, pady=4)
        CTkButton(self.sidebar, text="Comandas", command=self.garcom_comandas_screen).pack(fill="x", padx=12, pady=4)
        CTkButton(self.sidebar, text="Pedidos", command=self.garcom_pedidos_screen).pack(fill="x", padx=12, pady=4)
        CTkButton(self.sidebar, text="Chamados", command=self.garcom_chamados_screen).pack(fill="x", padx=12, pady=4)

    # =====================================================
    # ADMIN
    # =====================================================

    def admin_empresas_screen(self):
        self._current_screen = self.admin_empresas_screen
        self.build_shell("Admin - Empresas")
        self.admin_sidebar()

        left = CTkFrame(self.content, width=380)
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

        CTkLabel(left, text="Troca rápida de plano / módulo", font=("Arial", 15, "bold")).pack(pady=(20, 8))

        self.admin_empresa_id_entry = CTkEntry(left, placeholder_text="ID da empresa", width=300)
        self.admin_empresa_id_entry.pack(pady=5)

        self.admin_plano_id_entry = CTkEntry(left, placeholder_text="ID do plano", width=300)
        self.admin_plano_id_entry.pack(pady=5)

        CTkButton(left, text="Trocar Plano", command=self.admin_trocar_plano).pack(pady=8)

        self.admin_status_option = CTkOptionMenu(left, values=["ativo", "pausado", "bloqueado", "cancelado"])
        self.admin_status_option.pack(pady=5)

        CTkButton(left, text="Alterar Status", command=self.admin_alterar_status).pack(pady=8)

        self.admin_modulo_nome = CTkEntry(left, placeholder_text="Modulo ex: delivery", width=300)
        self.admin_modulo_nome.pack(pady=5)

        self.admin_modulo_ativo = CTkOptionMenu(left, values=["true", "false"])
        self.admin_modulo_ativo.pack(pady=5)

        CTkButton(left, text="Atualizar Módulo", command=self.admin_atualizar_modulo).pack(pady=8)

        CTkLabel(right, text="Empresas cadastradas", font=("Arial", 18, "bold")).pack(anchor="w", pady=(5, 10))

        try:
            r, empresas = self.request_json(
                "GET",
                f"{self.api}/admin/empresas",
                params={"token": self.token}
            )

            if r.status_code != 200:
                self.show_api_error("Erro", empresas, "Não foi possível carregar empresas")
                return

            if not empresas:
                CTkLabel(right, text="Nenhuma empresa cadastrada.").pack(anchor="w", pady=10)
                return

            for emp in empresas:
                card = CTkFrame(right)
                card.pack(fill="x", padx=5, pady=6)

                CTkLabel(
                    card,
                    text=f"{emp.get('nome', '')}  |  ID {emp.get('id', '')}",
                    font=("Arial", 16, "bold")
                ).pack(anchor="w", padx=10, pady=(10, 2))

                CTkLabel(
                    card,
                    text=f"Email: {emp.get('email', '')}"
                ).pack(anchor="w", padx=10)

                CTkLabel(
                    card,
                    text=f"Plano: {emp.get('plano_nome', '-')} | Status: {emp.get('status', '-')} | Vencimento: {emp.get('vencimento', '-')}"
                ).pack(anchor="w", padx=10, pady=(2, 10))

                mod_btn = CTkButton(
                    card,
                    text="Ver módulos",
                    command=lambda eid=emp["id"]: self.admin_show_modulos_popup(eid)
                )
                mod_btn.pack(anchor="e", padx=10, pady=(0, 10))

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def admin_show_modulos_popup(self, empresa_id):
        top = CTkToplevel(self)
        top.title(f"Módulos da empresa {empresa_id}")
        top.geometry("500x520")

        box = CTkScrollableFrame(top)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json(
            "GET",
            f"{self.api}/admin/empresa/modulos",
            params={"token": self.token, "empresa_id": empresa_id}
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar módulos")
            return

        CTkLabel(box, text=f"Empresa {empresa_id}", font=("Arial", 18, "bold")).pack(pady=10)

        for mod in data:
            row = CTkFrame(box)
            row.pack(fill="x", padx=5, pady=4)

            CTkLabel(row, text=mod["modulo"]).pack(side="left", padx=10, pady=10)
            CTkLabel(row, text="ATIVO" if mod["ativo"] else "DESLIGADO").pack(side="right", padx=10)

    def admin_criar_empresa(self):
        nome = self.admin_nome.get().strip()
        email = self.admin_email.get().strip()
        senha = self.admin_senha.get().strip()

        if not nome or not email or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos.")
            return

        r, data = self.request_json(
            "POST",
            f"{self.api}/admin/empresa",
            params={"token": self.token},
            json={"nome": nome, "email": email, "senha": senha}
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar empresa")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Empresa criada"))
        self.admin_empresas_screen()

    def admin_trocar_plano(self):
        try:
            empresa_id = int(self.admin_empresa_id_entry.get().strip())
            plano_id = int(self.admin_plano_id_entry.get().strip())
        except Exception:
            messagebox.showwarning("Aviso", "Informe IDs válidos.")
            return

        r, data = self.request_json(
            "POST",
            f"{self.api}/admin/empresa/plano",
            params={"token": self.token, "empresa_id": empresa_id, "plano_id": plano_id}
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao trocar plano")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Plano atualizado"))
        self.admin_empresas_screen()

    def admin_alterar_status(self):
        try:
            empresa_id = int(self.admin_empresa_id_entry.get().strip())
        except Exception:
            messagebox.showwarning("Aviso", "Informe o ID da empresa.")
            return

        status = self.admin_status_option.get()

        r, data = self.request_json(
            "POST",
            f"{self.api}/admin/empresa/status",
            params={"token": self.token, "empresa_id": empresa_id, "status": status}
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao alterar status")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Status atualizado"))
        self.admin_empresas_screen()

    def admin_atualizar_modulo(self):
        try:
            empresa_id = int(self.admin_empresa_id_entry.get().strip())
        except Exception:
            messagebox.showwarning("Aviso", "Informe o ID da empresa.")
            return

        modulo = self.admin_modulo_nome.get().strip()
        ativo = self.admin_modulo_ativo.get() == "true"

        if not modulo:
            messagebox.showwarning("Aviso", "Informe o nome do módulo.")
            return

        r, data = self.request_json(
            "POST",
            f"{self.api}/admin/empresa/modulo",
            json={
                "token": self.token,
                "empresa_id": empresa_id,
                "modulo": modulo,
                "ativo": ativo
            }
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao atualizar módulo")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Módulo atualizado"))

    # =====================================================
    # EMPRESA DASHBOARD
    # =====================================================

    def empresa_dashboard_screen(self):
        self._current_screen = self.empresa_dashboard_screen
        self.load_empresa_context()
        self.build_shell("Empresa - Dashboard")
        self.empresa_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(box, text="Resumo da empresa", font=("Arial", 22, "bold")).pack(anchor="w", pady=(5, 10))
        CTkLabel(box, text=f"Plano atual: {self.plano_nome}").pack(anchor="w", pady=3)

        mods = ", ".join(self.modulos_ativos) if self.modulos_ativos else "Nenhum módulo ativo"
        CTkLabel(box, text=f"Módulos ativos: {mods}", wraplength=1000, justify="left").pack(anchor="w", pady=3)

        cards = CTkFrame(box)
        cards.pack(fill="x", pady=15)

        endpoints = [
            ("Categorias", "/categorias"),
            ("Produtos", "/produtos?token=dummy&tipo=produto"),
            ("Mesas", "/mesas"),
            ("Comandas", "/comandas"),
            ("Pedidos", "/pedidos"),
            ("Chamados", "/chamados"),
        ]

        for titulo, _ in endpoints:
            card = CTkFrame(cards, width=210, height=100)
            card.pack(side="left", padx=8, pady=8)
            card.pack_propagate(False)
            CTkLabel(card, text=titulo, font=("Arial", 16, "bold")).pack(expand=True)

        info = CTkTextbox(box, height=260)
        info.pack(fill="x", pady=10)
        info.insert("end", "Esse painel já está ligado ao backend novo.\n\n")
        info.insert("end", "- Categorias definem se o item vai para cozinha ou bar.\n")
        info.insert("end", "- Comandas aceitam múltiplas por mesa.\n")
        info.insert("end", "- KDS cozinha e KDS bar ficam separados.\n")
        info.insert("end", "- Delivery usa nome do entregador e código de bip.\n")
        info.insert("end", "- Cardápio QR pode pedir, chamar garçom e pedir conta.\n")
        info.configure(state="disabled")

    # =====================================================
    # CATEGORIAS
    # =====================================================

    def categorias_screen(self):
        self._current_screen = self.categorias_screen
        self.build_shell("Categorias")
        self.empresa_sidebar()

        left = CTkFrame(self.content, width=380)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Nova categoria", font=("Arial", 18, "bold")).pack(pady=15)

        self.cat_nome = CTkEntry(left, placeholder_text="Nome da categoria", width=300)
        self.cat_nome.pack(pady=8)

        self.cat_setor = CTkOptionMenu(left, values=["cozinha", "bar"])
        self.cat_setor.pack(pady=8)

        CTkButton(left, text="Salvar Categoria", command=self.criar_categoria).pack(pady=12)

        CTkLabel(right, text="Lista de categorias", font=("Arial", 18, "bold")).pack(anchor="w", pady=(5, 10))

        r, data = self.request_json("GET", f"{self.api}/categorias", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar categorias")
            return

        for item in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{item['nome']}  |  Setor: {item['setor']}", font=("Arial", 15, "bold")).pack(anchor="w", padx=10, pady=10)

    def criar_categoria(self):
        nome = self.cat_nome.get().strip()
        setor = self.cat_setor.get()

        if not nome:
            messagebox.showwarning("Aviso", "Informe o nome.")
            return

        r, data = self.request_json(
            "POST",
            f"{self.api}/categorias",
            json={"token": self.token, "nome": nome, "setor": setor}
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar categoria")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Categoria criada"))
        self.categorias_screen()

    # =====================================================
    # PRODUTOS
    # =====================================================

    def produtos_screen(self):
        self._current_screen = self.produtos_screen
        self.build_shell("Produtos")
        self.empresa_sidebar()

        left = CTkFrame(self.content, width=400)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Novo produto", font=("Arial", 18, "bold")).pack(pady=15)

        self.prod_nome = CTkEntry(left, placeholder_text="Nome", width=320)
        self.prod_nome.pack(pady=6)

        self.prod_preco = CTkEntry(left, placeholder_text="Preço", width=320)
        self.prod_preco.pack(pady=6)

        self.prod_estoque = CTkEntry(left, placeholder_text="Estoque", width=320)
        self.prod_estoque.pack(pady=6)

        self.prod_tipo = CTkOptionMenu(left, values=["produto", "lanche"])
        self.prod_tipo.pack(pady=6)

        rcat, cats = self.request_json("GET", f"{self.api}/categorias", params={"token": self.token})
        if rcat.status_code != 200:
            self.show_api_error("Erro", cats, "Falha ao carregar categorias")
            return

        self.categorias_map = {f"{c['id']} - {c['nome']} ({c['setor']})": c["id"] for c in cats}
        values = list(self.categorias_map.keys()) if self.categorias_map else ["Sem categorias"]
        self.prod_categoria = CTkOptionMenu(left, values=values)
        self.prod_categoria.pack(pady=6)

        CTkButton(left, text="Salvar Produto", command=self.criar_produto).pack(pady=12)

        CTkLabel(right, text="Lista de produtos", font=("Arial", 18, "bold")).pack(anchor="w", pady=(5, 10))

        r, data = self.request_json(
            "GET",
            f"{self.api}/produtos",
            params={"token": self.token, "tipo": "produto"}
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar produtos")
            return

        for p in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)

            txt = (
                f"{p.get('nome', '')} | {p.get('codigo', '')}\n"
                f"Categoria: {p.get('categoria_nome', '-')} | Setor: {p.get('setor', '-')}\n"
                f"Preço: R$ {float(p.get('preco', 0)):.2f} | Estoque: {p.get('estoque', 0)}"
            )
            CTkLabel(card, text=txt, justify="left").pack(anchor="w", padx=10, pady=10)

    def criar_produto(self):
        if not self.categorias_map:
            messagebox.showwarning("Aviso", "Crie uma categoria antes.")
            return

        try:
            nome = self.prod_nome.get().strip()
            preco = float(self.prod_preco.get().replace(",", "."))
            estoque = int(self.prod_estoque.get() or "0")
        except Exception:
            messagebox.showwarning("Aviso", "Preço ou estoque inválido.")
            return

        categoria_id = self.categorias_map[self.prod_categoria.get()]
        tipo = self.prod_tipo.get()

        r, data = self.request_json(
            "POST",
            f"{self.api}/produto",
            json={
                "token": self.token,
                "categoria_id": categoria_id,
                "nome": nome,
                "preco": preco,
                "estoque": estoque,
                "tipo": tipo
            }
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar produto")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Produto criado"))
        self.produtos_screen()

    # =====================================================
    # CLIENTES / FORNECEDORES / FUNCIONÁRIOS
    # =====================================================

    def clientes_screen(self):
        self._current_screen = self.clientes_screen
        self.build_shell("Clientes")
        self.empresa_sidebar()

        if not self.has_modulo("cadastro_clientes"):
            self.modulo_block_screen("cadastro_clientes")
            return

        self.simple_cadastro_screen(
            title="Clientes",
            fields=["Nome", "Telefone", "Email", "Documento", "Observações"],
            endpoint_create="/clientes",
            endpoint_list="/clientes",
            key_map=["nome", "telefone", "email", "documento", "observacoes"]
        )

    def fornecedores_screen(self):
        self._current_screen = self.fornecedores_screen
        self.build_shell("Fornecedores")
        self.empresa_sidebar()

        if not self.has_modulo("cadastro_fornecedores"):
            self.modulo_block_screen("cadastro_fornecedores")
            return

        self.simple_cadastro_screen(
            title="Fornecedores",
            fields=["Nome", "Telefone", "Email", "Documento", "Observações"],
            endpoint_create="/fornecedores",
            endpoint_list="/fornecedores",
            key_map=["nome", "telefone", "email", "documento", "observacoes"]
        )

    def funcionarios_screen(self):
        self._current_screen = self.funcionarios_screen
        self.build_shell("Funcionários")
        self.empresa_sidebar()

        if not self.has_modulo("cadastro_funcionarios"):
            self.modulo_block_screen("cadastro_funcionarios")
            return

        left = CTkFrame(self.content, width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Novo funcionário", font=("Arial", 18, "bold")).pack(pady=15)

        self.fun_nome = CTkEntry(left, placeholder_text="Nome", width=320)
        self.fun_nome.pack(pady=6)

        self.fun_tel = CTkEntry(left, placeholder_text="Telefone", width=320)
        self.fun_tel.pack(pady=6)

        self.fun_email = CTkEntry(left, placeholder_text="Email", width=320)
        self.fun_email.pack(pady=6)

        self.fun_senha = CTkEntry(left, placeholder_text="Senha", width=320)
        self.fun_senha.pack(pady=6)

        self.fun_cargo = CTkOptionMenu(left, values=["garcom", "admin_empresa", "caixa", "cozinha", "bar"])
        self.fun_cargo.pack(pady=6)

        CTkButton(left, text="Salvar Funcionário", command=self.criar_funcionario).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/funcionarios", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar funcionários")
            return

        for f in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(
                card,
                text=f"{f['nome']} | {f['cargo']} | {f['email']} | {'ativo' if f['ativo'] else 'inativo'}"
            ).pack(anchor="w", padx=10, pady=10)

    def criar_funcionario(self):
        r, data = self.request_json(
            "POST",
            f"{self.api}/funcionarios",
            json={
                "token": self.token,
                "nome": self.fun_nome.get().strip(),
                "telefone": self.fun_tel.get().strip(),
                "email": self.fun_email.get().strip(),
                "senha": self.fun_senha.get().strip(),
                "cargo": self.fun_cargo.get(),
            }
        )

        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar funcionário")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Funcionário criado"))
        self.funcionarios_screen()

    def simple_cadastro_screen(self, title, fields, endpoint_create, endpoint_list, key_map):
        left = CTkFrame(self.content, width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text=f"Novo {title[:-1]}", font=("Arial", 18, "bold")).pack(pady=15)

        entries = []
        for fld in fields:
            e = CTkEntry(left, placeholder_text=fld, width=320)
            e.pack(pady=6)
            entries.append(e)

        def salvar():
            payload = {"token": self.token}
            for entry, key in zip(entries, key_map):
                payload[key] = entry.get().strip()

            r, data = self.request_json("POST", f"{self.api}{endpoint_create}", json=payload)
            if r.status_code != 200:
                self.show_api_error("Erro", data, "Falha ao salvar")
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Salvo"))
            self.refresh_current_screen()

        CTkButton(left, text="Salvar", command=salvar).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}{endpoint_list}", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao listar")
            return

        for item in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)
            texto = " | ".join([str(item.get(k, "")) for k in key_map[:4]])
            CTkLabel(card, text=texto).pack(anchor="w", padx=10, pady=10)

    # =====================================================
    # MESAS
    # =====================================================

    def mesas_screen(self):
        self._current_screen = self.mesas_screen
        self.build_shell("Mesas")
        self.empresa_sidebar()

        left = CTkFrame(self.content, width=360)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Nova mesa", font=("Arial", 18, "bold")).pack(pady=15)

        self.mesa_numero = CTkEntry(left, placeholder_text="Número da mesa", width=280)
        self.mesa_numero.pack(pady=8)

        CTkButton(left, text="Criar Mesa", command=self.criar_mesa).pack(pady=12)

        CTkLabel(right, text="Mesas cadastradas", font=("Arial", 18, "bold")).pack(anchor="w", pady=(5, 10))

        r, data = self.request_json("GET", f"{self.api}/mesas", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar mesas")
            return

        grid = CTkFrame(right, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        col = 0
        row = 0
        for mesa in data:
            card = CTkFrame(grid, width=230, height=150)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            card.pack_propagate(False)

            CTkLabel(card, text=f"Mesa {mesa['numero']}", font=("Arial", 18, "bold")).pack(pady=(12, 6))
            CTkLabel(card, text=f"Status: {mesa['status']}").pack(pady=3)
            CTkLabel(card, text=f"QR: {mesa.get('qr_code', '')[:18]}...", wraplength=180).pack(pady=3)

            col += 1
            if col > 3:
                col = 0
                row += 1

    def criar_mesa(self):
        try:
            numero = int(self.mesa_numero.get().strip())
        except Exception:
            messagebox.showwarning("Aviso", "Número inválido.")
            return

        r, data = self.request_json(
            "POST",
            f"{self.api}/mesas",
            json={"token": self.token, "numero": numero}
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar mesa")
            return

        messagebox.showinfo("Sucesso", f"{data.get('msg', 'Mesa criada')}\nQR: {data.get('qr_code', '')}")
        self.mesas_screen()

    # =====================================================
    # COMANDAS
    # =====================================================

    def comandas_screen(self):
        self._current_screen = self.comandas_screen
        self.build_shell("Comandas")
        self.empresa_sidebar()

        left = CTkFrame(self.content, width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Nova comanda", font=("Arial", 18, "bold")).pack(pady=15)

        r_mesas, mesas = self.request_json("GET", f"{self.api}/mesas", params={"token": self.token})
        self.mesas_map = {f"{m['id']} - Mesa {m['numero']}": m["id"] for m in mesas} if r_mesas.status_code == 200 else {}
        mesa_values = ["Sem mesa"] + list(self.mesas_map.keys())
        self.comanda_mesa = CTkOptionMenu(left, values=mesa_values)
        self.comanda_mesa.pack(pady=6)

        r_cli, clientes = self.request_json("GET", f"{self.api}/clientes", params={"token": self.token})
        self.clientes_map = {}
        if r_cli.status_code == 200 and isinstance(clientes, list):
            self.clientes_map = {f"{c['id']} - {c['nome']}": c["id"] for c in clientes}
        cliente_values = ["Sem cliente"] + list(self.clientes_map.keys())
        self.comanda_cliente = CTkOptionMenu(left, values=cliente_values)
        self.comanda_cliente.pack(pady=6)

        self.comanda_origem = CTkOptionMenu(left, values=["balcao", "qr", "app_entrega", "garcom"])
        self.comanda_origem.pack(pady=6)

        self.comanda_obs = CTkEntry(left, placeholder_text="Observações", width=320)
        self.comanda_obs.pack(pady=6)

        CTkButton(left, text="Criar Comanda", command=self.criar_comanda).pack(pady=12)

        CTkButton(left, text="Abrir Tela de Pedido", command=self.open_pedido_popup).pack(pady=6)

        CTkLabel(right, text="Comandas", font=("Arial", 18, "bold")).pack(anchor="w", pady=(5, 10))

        r, data = self.request_json("GET", f"{self.api}/comandas", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar comandas")
            return

        for c in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)

            txt = (
                f"Comanda #{c.get('numero', '')} | ID {c.get('id', '')}\n"
                f"Mesa: {c.get('mesa_numero', '-')} | Cliente: {c.get('cliente_nome', '-')}\n"
                f"Origem: {c.get('origem', '-')} | Status: {c.get('status', '-')}"
            )
            CTkLabel(card, text=txt, justify="left").pack(anchor="w", padx=10, pady=10)

    def criar_comanda(self):
        mesa = self.comanda_mesa.get()
        cliente = self.comanda_cliente.get()

        mesa_id = None if mesa == "Sem mesa" else self.mesas_map[mesa]
        cliente_id = None if cliente == "Sem cliente" else self.clientes_map[cliente]

        r, data = self.request_json(
            "POST",
            f"{self.api}/comandas",
            json={
                "token": self.token,
                "mesa_id": mesa_id,
                "cliente_id": cliente_id,
                "origem": self.comanda_origem.get(),
                "observacoes": self.comanda_obs.get().strip()
            }
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar comanda")
            return

        messagebox.showinfo("Sucesso", f"Comanda criada\nNúmero: {data.get('numero')}")
        self.comandas_screen()

    def open_pedido_popup(self):
        top = CTkToplevel(self)
        top.title("Novo Pedido")
        top.geometry("780x720")

        frame = CTkScrollableFrame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(frame, text="Criar pedido", font=("Arial", 20, "bold")).pack(pady=10)

        r_com, comandas = self.request_json("GET", f"{self.api}/comandas", params={"token": self.token, "status": "aberta"})
        if r_com.status_code != 200:
            self.show_api_error("Erro", comandas, "Falha ao carregar comandas")
            return

        com_map = {f"{c['id']} - Comanda {c['numero']}": c["id"] for c in comandas}
        com_values = list(com_map.keys()) if com_map else ["Sem comandas"]
        comanda_opt = CTkOptionMenu(frame, values=com_values)
        comanda_opt.pack(pady=8)

        origem_opt = CTkOptionMenu(frame, values=["balcao", "qr", "app_entrega", "garcom"])
        origem_opt.pack(pady=8)

        obs_entry = CTkEntry(frame, placeholder_text="Observações do pedido", width=420)
        obs_entry.pack(pady=8)

        r_prod, produtos = self.request_json("GET", f"{self.api}/produtos", params={"token": self.token, "tipo": "produto"})
        if r_prod.status_code != 200:
            self.show_api_error("Erro", produtos, "Falha ao carregar produtos")
            return

        r_add, adicionais = self.request_json("GET", f"{self.api}/adicionais", params={"token": self.token})
        adicionais_map = {a["id"]: a for a in adicionais} if r_add.status_code == 200 else {}

        items_holder = []

        def add_item_row():
            row = CTkFrame(frame)
            row.pack(fill="x", padx=5, pady=5)

            prod_map = {f"{p['id']} - {p['nome']} ({p.get('categoria_nome', '-')})": p["id"] for p in produtos}
            prod_opt = CTkOptionMenu(row, values=list(prod_map.keys()), width=260)
            prod_opt.pack(side="left", padx=5)

            qtd = CTkEntry(row, placeholder_text="Qtd", width=60)
            qtd.insert(0, "1")
            qtd.pack(side="left", padx=5)

            obs = CTkEntry(row, placeholder_text="Observação", width=180)
            obs.pack(side="left", padx=5)

            add_ids = []
            if adicionais_map:
                add_values = [f"{a['id']} - {a['nome']}" for a in adicionais]
                add_opt = CTkOptionMenu(row, values=["Sem adicional"] + add_values, width=180)
                add_opt.pack(side="left", padx=5)
            else:
                add_opt = None

            items_holder.append((prod_map, prod_opt, qtd, obs, add_opt))

        CTkButton(frame, text="Adicionar item", command=add_item_row).pack(pady=8)
        add_item_row()

        def salvar():
            if not comandas:
                messagebox.showwarning("Aviso", "Nenhuma comanda aberta.")
                return

            itens = []
            for prod_map, prod_opt, qtd, obs, add_opt in items_holder:
                try:
                    quantidade = int(qtd.get().strip() or "1")
                except Exception:
                    quantidade = 1

                adicionais_ids = []
                if add_opt and add_opt.get() != "Sem adicional":
                    adicionais_ids.append(int(add_opt.get().split(" - ")[0]))

                itens.append({
                    "produto_id": prod_map[prod_opt.get()],
                    "quantidade": quantidade,
                    "observacoes": obs.get().strip(),
                    "adicionais_ids": adicionais_ids
                })

            r, data = self.request_json(
                "POST",
                f"{self.api}/pedidos",
                json={
                    "token": self.token,
                    "comanda_id": com_map[comanda_opt.get()],
                    "itens": itens,
                    "origem": origem_opt.get(),
                    "observacoes": obs_entry.get().strip()
                }
            )

            if r.status_code != 200:
                self.show_api_error("Erro", data, "Falha ao criar pedido")
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Pedido criado"))
            top.destroy()

        CTkButton(frame, text="Salvar pedido", command=salvar).pack(pady=15)

    # =====================================================
    # PEDIDOS
    # =====================================================

    def pedidos_screen(self):
        self._current_screen = self.pedidos_screen
        self.build_shell("Pedidos")
        self.empresa_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        top = CTkFrame(box)
        top.pack(fill="x", pady=(0, 10))

        self.pedido_status_filter = CTkOptionMenu(top, values=["todos", "recebido", "em_preparo", "pronto", "entregue", "cancelado"])
        self.pedido_status_filter.pack(side="left", padx=5)

        self.pedido_setor_filter = CTkOptionMenu(top, values=["todos", "cozinha", "bar"])
        self.pedido_setor_filter.pack(side="left", padx=5)

        CTkButton(top, text="Filtrar", command=self.pedidos_screen).pack(side="left", padx=5)

        params = {"token": self.token}
        st = self.pedido_status_filter.get()
        se = self.pedido_setor_filter.get()
        if st != "todos":
            params["status"] = st
        if se != "todos":
            params["setor"] = se

        r, data = self.request_json("GET", f"{self.api}/pedidos", params=params)
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar pedidos")
            return

        for ped in data:
            card = CTkFrame(box)
            card.pack(fill="x", padx=5, pady=6)

            info = (
                f"Pedido ID {ped['id']} | Setor: {ped['setor']} | Status: {ped['status']} | Semáforo: {ped.get('semaforo', '-')}\n"
                f"Comanda: {ped.get('comanda_numero', '-')} | Mesa: {ped.get('mesa_numero', '-')} | Cliente: {ped.get('cliente_nome', '-')}\n"
                f"Origem: {ped.get('origem', '-')} | Minutos aberto: {ped.get('minutos_aberto', 0)}"
            )

            CTkLabel(card, text=info, justify="left").pack(anchor="w", padx=10, pady=(10, 5))

            btns = CTkFrame(card, fg_color="transparent")
            btns.pack(fill="x", padx=10, pady=(0, 10))

            CTkButton(btns, text="Itens", width=90, command=lambda pid=ped["id"]: self.show_pedido_itens(pid)).pack(side="left", padx=4)
            CTkButton(btns, text="Em preparo", width=110, command=lambda pid=ped["id"]: self.update_pedido_status(pid, "em_preparo")).pack(side="left", padx=4)
            CTkButton(btns, text="Pronto", width=90, command=lambda pid=ped["id"]: self.update_pedido_status(pid, "pronto")).pack(side="left", padx=4)
            CTkButton(btns, text="Entregue", width=100, command=lambda pid=ped["id"]: self.update_pedido_status(pid, "entregue")).pack(side="left", padx=4)
            CTkButton(btns, text="Saiu entrega", width=120, command=lambda pid=ped["id"]: self.sair_entrega_popup(pid)).pack(side="left", padx=4)

    def show_pedido_itens(self, pedido_id):
        top = CTkToplevel(self)
        top.title(f"Itens do pedido {pedido_id}")
        top.geometry("650x500")

        box = CTkScrollableFrame(top)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json(
            "GET",
            f"{self.api}/pedidos/{pedido_id}/itens",
            params={"token": self.token}
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar itens")
            return

        for item in data:
            card = CTkFrame(box)
            card.pack(fill="x", padx=5, pady=5)

            CTkLabel(
                card,
                text=f"{item['nome_produto']} | Qtd: {item['quantidade']} | R$ {float(item['preco']):.2f}",
                font=("Arial", 15, "bold")
            ).pack(anchor="w", padx=10, pady=(10, 3))

            if item.get("observacoes"):
                CTkLabel(card, text=f"Obs: {item['observacoes']}").pack(anchor="w", padx=10, pady=(0, 3))

            adds = item.get("adicionais", [])
            if adds:
                texto = "Adicionais: " + ", ".join([a["nome_adicional"] for a in adds])
                CTkLabel(card, text=texto).pack(anchor="w", padx=10, pady=(0, 10))
            else:
                CTkLabel(card, text="Sem adicionais").pack(anchor="w", padx=10, pady=(0, 10))

    def update_pedido_status(self, pedido_id, status):
        r, data = self.request_json(
            "POST",
            f"{self.api}/pedidos/{pedido_id}/status",
            json={"token": self.token, "status": status}
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao atualizar status")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Status atualizado"))
        self.pedidos_screen()

    def sair_entrega_popup(self, pedido_id):
        top = CTkToplevel(self)
        top.title("Saiu para entrega")
        top.geometry("420x220")

        frame = CTkFrame(top)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(frame, text=f"Pedido {pedido_id}", font=("Arial", 18, "bold")).pack(pady=10)

        nome = CTkEntry(frame, placeholder_text="Nome do entregador", width=280)
        nome.pack(pady=8)

        def enviar():
            r, data = self.request_json(
                "POST",
                f"{self.api}/pedidos/{pedido_id}/sair-entrega",
                json={"token": self.token, "nome_entregador": nome.get().strip()}
            )
            if r.status_code != 200:
                self.show_api_error("Erro", data, "Falha ao enviar para entrega")
                return

            messagebox.showinfo("Sucesso", f"{data.get('msg')}\nCódigo: {data.get('codigo_bip', '')}")
            top.destroy()
            self.pedidos_screen()

        CTkButton(frame, text="Confirmar", command=enviar).pack(pady=12)

    # =====================================================
    # KDS
    # =====================================================

    def kds_cozinha_screen(self):
        self._current_screen = self.kds_cozinha_screen
        self.build_shell("KDS - Cozinha")
        self.empresa_sidebar()

        if not self.has_modulo("kds_cozinha"):
            self.modulo_block_screen("kds_cozinha")
            return

        self.render_kds("/kds/cozinha", "cozinha")

    def kds_bar_screen(self):
        self._current_screen = self.kds_bar_screen
        self.build_shell("KDS - Bar")
        self.empresa_sidebar()

        if not self.has_modulo("kds_bar"):
            self.modulo_block_screen("kds_bar")
            return

        self.render_kds("/kds/bar", "bar")

    def render_kds(self, endpoint, setor):
        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(box, text=f"Fila {setor.upper()}", font=("Arial", 22, "bold")).pack(anchor="w", pady=(5, 10))

        r, data = self.request_json("GET", f"{self.api}{endpoint}", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar KDS")
            return

        for ped in data:
            cor = "#1f6aa5"
            if ped.get("semaforo") == "atrasado":
                cor = "#8B0000"
            elif ped.get("semaforo") == "atencao":
                cor = "#8B6508"
            elif ped.get("status") == "pronto":
                cor = "#2E8B57"

            card = CTkFrame(box, fg_color=cor)
            card.pack(fill="x", padx=5, pady=6)

            txt = (
                f"Pedido {ped['id']} | Mesa {ped.get('mesa_numero', '-')} | Comanda {ped.get('comanda_numero', '-')}\n"
                f"Status: {ped['status']} | Semáforo: {ped.get('semaforo', '-')} | {ped.get('minutos_aberto', 0)} min"
            )
            CTkLabel(card, text=txt, justify="left").pack(anchor="w", padx=10, pady=(10, 5))

            btns = CTkFrame(card, fg_color="transparent")
            btns.pack(fill="x", padx=10, pady=(0, 10))
            CTkButton(btns, text="Itens", width=80, command=lambda pid=ped["id"]: self.show_pedido_itens(pid)).pack(side="left", padx=4)
            CTkButton(btns, text="Em preparo", width=110, command=lambda pid=ped["id"]: self.update_pedido_status(pid, "em_preparo")).pack(side="left", padx=4)
            CTkButton(btns, text="Pronto", width=90, command=lambda pid=ped["id"]: self.update_pedido_status(pid, "pronto")).pack(side="left", padx=4)
            CTkButton(btns, text="Entregue", width=90, command=lambda pid=ped["id"]: self.update_pedido_status(pid, "entregue")).pack(side="left", padx=4)

    # =====================================================
    # ENTREGADORES
    # =====================================================

    def entregadores_screen(self):
        self._current_screen = self.entregadores_screen
        self.build_shell("Entregadores")
        self.empresa_sidebar()

        if not self.has_modulo("delivery"):
            self.modulo_block_screen("delivery")
            return

        left = CTkFrame(self.content, width=380)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Novo entregador", font=("Arial", 18, "bold")).pack(pady=15)
        self.ent_nome = CTkEntry(left, placeholder_text="Nome", width=300)
        self.ent_nome.pack(pady=6)
        self.ent_tel = CTkEntry(left, placeholder_text="Telefone", width=300)
        self.ent_tel.pack(pady=6)

        CTkButton(left, text="Salvar Entregador", command=self.criar_entregador).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/entregadores", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar entregadores")
            return

        for e in data:
            card = CTkFrame(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{e['nome']} | {e['telefone']}").pack(anchor="w", padx=10, pady=10)

    def criar_entregador(self):
        r, data = self.request_json(
            "POST",
            f"{self.api}/entregadores",
            json={
                "token": self.token,
                "nome": self.ent_nome.get().strip(),
                "telefone": self.ent_tel.get().strip()
            }
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao criar entregador")
            return

        messagebox.showinfo("Sucesso", data.get("msg", "Entregador criado"))
        self.entregadores_screen()

    # =====================================================
    # CHAMADOS
    # =====================================================

    def chamados_screen(self):
        self._current_screen = self.chamados_screen
        self.build_shell("Chamados das Mesas")
        self.empresa_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json("GET", f"{self.api}/chamados", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar chamados")
            return

        if not data:
            CTkLabel(box, text="Nenhum chamado aberto.").pack(anchor="w", pady=10)
            return

        for ch in data:
            card = CTkFrame(box)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(
                card,
                text=f"Mesa {ch.get('mesa_numero', '-')} | Tipo: {ch.get('tipo', '-')} | Status: {ch.get('status', '-')}"
            ).pack(anchor="w", padx=10, pady=10)

    # =====================================================
    # CONFIGURAÇÕES
    # =====================================================

    def config_screen(self):
        self._current_screen = self.config_screen
        self.build_shell("Configurações")
        self.empresa_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        CTkLabel(box, text="Configurações gerais", font=("Arial", 20, "bold")).pack(anchor="w", pady=(5, 10))

        self.cfg_whats_num = CTkEntry(box, placeholder_text="WhatsApp número")
        self.cfg_whats_num.pack(fill="x", pady=5)

        self.cfg_whats_token = CTkEntry(box, placeholder_text="WhatsApp token")
        self.cfg_whats_token.pack(fill="x", pady=5)

        self.cfg_ifood = CTkEntry(box, placeholder_text="Token iFood")
        self.cfg_ifood.pack(fill="x", pady=5)

        self.cfg_aiq = CTkEntry(box, placeholder_text="Token aiqfome")
        self.cfg_aiq.pack(fill="x", pady=5)

        self.cfg_uber = CTkEntry(box, placeholder_text="Token Uber")
        self.cfg_uber.pack(fill="x", pady=5)

        self.cfg_imp_nome = CTkEntry(box, placeholder_text="Nome da impressora")
        self.cfg_imp_nome.pack(fill="x", pady=5)

        self.cfg_imp_porta = CTkEntry(box, placeholder_text="Porta impressora")
        self.cfg_imp_porta.pack(fill="x", pady=5)

        self.cfg_imp_larg = CTkEntry(box, placeholder_text="Largura", width=200)
        self.cfg_imp_larg.pack(fill="x", pady=5)

        self.pg_pix = CTkCheckBox(box, text="PIX")
        self.pg_pix.pack(anchor="w", pady=3)

        self.pg_qr = CTkCheckBox(box, text="QR Code")
        self.pg_qr.pack(anchor="w", pady=3)

        self.pg_credito = CTkCheckBox(box, text="Cartão crédito")
        self.pg_credito.pack(anchor="w", pady=3)

        self.pg_debito = CTkCheckBox(box, text="Cartão débito")
        self.pg_debito.pack(anchor="w", pady=3)

        self.pg_dinheiro = CTkCheckBox(box, text="Dinheiro")
        self.pg_dinheiro.pack(anchor="w", pady=3)

        self.imp_corte = CTkCheckBox(box, text="Cortar papel automático")
        self.imp_corte.pack(anchor="w", pady=3)

        btns = CTkFrame(box, fg_color="transparent")
        btns.pack(fill="x", pady=15)

        CTkButton(btns, text="Salvar", command=self.save_configs).pack(side="left", padx=5)
        CTkButton(btns, text="Testar WhatsApp", command=self.test_whatsapp).pack(side="left", padx=5)
        CTkButton(btns, text="Testar Delivery", command=self.test_delivery).pack(side="left", padx=5)

        r, cfg = self.request_json("GET", f"{self.api}/configuracoes", params={"token": self.token})
        if r.status_code == 200 and isinstance(cfg, dict):
            self.set_entry(self.cfg_whats_num, cfg.get("whatsapp_numero", ""))
            self.set_entry(self.cfg_whats_token, cfg.get("whatsapp_token", ""))
            self.set_entry(self.cfg_ifood, cfg.get("ifood_token", ""))
            self.set_entry(self.cfg_aiq, cfg.get("aiqfome_token", ""))
            self.set_entry(self.cfg_uber, cfg.get("uber_token", ""))
            self.set_entry(self.cfg_imp_nome, cfg.get("impressora_nome", ""))
            self.set_entry(self.cfg_imp_porta, cfg.get("impressora_porta", ""))
            self.set_entry(self.cfg_imp_larg, cfg.get("impressora_largura", "80mm"))

            if cfg.get("pagamento_pix", True): self.pg_pix.select()
            if cfg.get("pagamento_qrcode", True): self.pg_qr.select()
            if cfg.get("pagamento_cartao_credito", True): self.pg_credito.select()
            if cfg.get("pagamento_cartao_debito", True): self.pg_debito.select()
            if cfg.get("pagamento_dinheiro", True): self.pg_dinheiro.select()
            if cfg.get("impressora_corta_papel", True): self.imp_corte.select()

    def save_configs(self):
        r, data = self.request_json(
            "POST",
            f"{self.api}/configuracoes/salvar",
            json={
                "token": self.token,
                "whatsapp_numero": self.cfg_whats_num.get().strip(),
                "whatsapp_token": self.cfg_whats_token.get().strip(),
                "whatsapp_webhook": "",
                "ifood_token": self.cfg_ifood.get().strip(),
                "aiqfome_token": self.cfg_aiq.get().strip(),
                "uber_token": self.cfg_uber.get().strip(),
                "pagamento_pix": self.pg_pix.get() == 1,
                "pagamento_qrcode": self.pg_qr.get() == 1,
                "pagamento_cartao_credito": self.pg_credito.get() == 1,
                "pagamento_cartao_debito": self.pg_debito.get() == 1,
                "pagamento_dinheiro": self.pg_dinheiro.get() == 1,
                "impressora_nome": self.cfg_imp_nome.get().strip(),
                "impressora_porta": self.cfg_imp_porta.get().strip(),
                "impressora_largura": self.cfg_imp_larg.get().strip() or "80mm",
                "impressora_corta_papel": self.imp_corte.get() == 1
            }
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao salvar")
            return
        messagebox.showinfo("Sucesso", data.get("msg", "Configurações salvas"))

    def test_whatsapp(self):
        r, data = self.request_json("POST", f"{self.api}/whatsapp/teste", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("WhatsApp", data, "Bloqueado")
            return
        messagebox.showinfo("WhatsApp", data.get("msg", "Liberado"))

    def test_delivery(self):
        r, data = self.request_json("POST", f"{self.api}/delivery/teste", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Delivery", data, "Bloqueado")
            return
        messagebox.showinfo("Delivery", data.get("msg", "Liberado"))

    # =====================================================
    # GARÇOM
    # =====================================================

    def garcom_dashboard_screen(self):
        self._current_screen = self.garcom_dashboard_screen
        self.build_shell("Garçom - Dashboard")
        self.garcom_sidebar()

        box = CTkFrame(self.content)
        box.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(box, text="Módulo do Garçom", font=("Arial", 24, "bold")).pack(pady=15)
        CTkLabel(box, text="Use o menu lateral para abrir mesas, comandas e lançar pedidos.").pack(pady=8)
        CTkButton(box, text="Ir para Comandas", command=self.garcom_comandas_screen).pack(pady=8)
        CTkButton(box, text="Ir para Pedidos", command=self.garcom_pedidos_screen).pack(pady=8)

    def garcom_mesas_screen(self):
        self._current_screen = self.garcom_mesas_screen
        self.build_shell("Garçom - Mesas")
        self.garcom_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json("GET", f"{self.api}/mesas", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar mesas")
            return

        for mesa in data:
            card = CTkFrame(box)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"Mesa {mesa['numero']} | Status: {mesa['status']}").pack(anchor="w", padx=10, pady=10)

    def garcom_comandas_screen(self):
        self._current_screen = self.garcom_comandas_screen
        self.build_shell("Garçom - Comandas")
        self.garcom_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        top = CTkFrame(box)
        top.pack(fill="x", pady=(0, 10))

        self.g_mesa_id = CTkEntry(top, placeholder_text="ID da mesa", width=120)
        self.g_mesa_id.pack(side="left", padx=5)

        self.g_cliente_id = CTkEntry(top, placeholder_text="ID do cliente", width=120)
        self.g_cliente_id.pack(side="left", padx=5)

        CTkButton(top, text="Abrir Comanda", command=self.garcom_criar_comanda).pack(side="left", padx=5)

        # usa endpoint empresa para listar
        r, data = self.request_json("GET", f"{self.api}/comandas", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar comandas")
            return

        for c in data:
            card = CTkFrame(box)
            card.pack(fill="x", padx=5, pady=5)
            txt = f"Comanda {c.get('numero')} | ID {c.get('id')} | Mesa {c.get('mesa_numero', '-')}"
            CTkLabel(card, text=txt).pack(anchor="w", padx=10, pady=10)

    def garcom_criar_comanda(self):
        try:
            mesa_id = int(self.g_mesa_id.get().strip()) if self.g_mesa_id.get().strip() else None
            cliente_id = int(self.g_cliente_id.get().strip()) if self.g_cliente_id.get().strip() else None
        except Exception:
            messagebox.showwarning("Aviso", "IDs inválidos.")
            return

        r, data = self.request_json(
            "POST",
            f"{self.api}/garcom/comandas",
            params={"token": self.token, "mesa_id": mesa_id, "cliente_id": cliente_id}
        )
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao abrir comanda")
            return

        messagebox.showinfo("Sucesso", f"Comanda {data.get('numero')} aberta")
        self.garcom_comandas_screen()

    def garcom_pedidos_screen(self):
        self._current_screen = self.garcom_pedidos_screen
        self.build_shell("Garçom - Pedidos")
        self.garcom_sidebar()

        box = CTkFrame(self.content)
        box.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(box, text="Use a tela da empresa -> Comandas -> Abrir Tela de Pedido", font=("Arial", 18, "bold")).pack(pady=15)
        CTkLabel(box, text="Esse módulo já está pronto no backend.").pack(pady=10)

    def garcom_chamados_screen(self):
        self._current_screen = self.garcom_chamados_screen
        self.build_shell("Garçom - Chamados")
        self.garcom_sidebar()

        box = CTkScrollableFrame(self.content)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json("GET", f"{self.api}/chamados", params={"token": self.token})
        if r.status_code != 200:
            self.show_api_error("Erro", data, "Falha ao carregar chamados")
            return

        for ch in data:
            card = CTkFrame(box)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"Mesa {ch.get('mesa_numero', '-')} | {ch.get('tipo', '-')} | {ch.get('status', '-')}").pack(anchor="w", padx=10, pady=10)

    # =====================================================
    # UTIL
    # =====================================================

    def modulo_block_screen(self, modulo):
        box = CTkFrame(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        CTkLabel(box, text="Módulo não ativo", font=("Arial", 24, "bold")).pack(pady=18)
        CTkLabel(
            box,
            text=f"O módulo '{modulo}' não está ativo para esta empresa.",
            font=("Arial", 15)
        ).pack(pady=8)
        CTkLabel(
            box,
            text="Ative esse módulo no painel admin para liberar esta tela.",
            font=("Arial", 14)
        ).pack(pady=8)


if __name__ == "__main__":
    app = App()
    app.mainloop()