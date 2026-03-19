import requests
from customtkinter import *
from tkinter import messagebox

set_appearance_mode("dark")
set_default_color_theme("blue")


class App(CTk):
    def __init__(self):
        super().__init__()
        self.title("RK Sistemas")
        self.geometry("1320x780")

        self.api = "https://rk-sistemas1.onrender.com"
        self.token = None
        self.tipo_login = StringVar(value="empresa")

        self.total = 0.0
        self.carrinho = []
        self.adicionais = []

        self.pagamento_var = StringVar(value="dinheiro")
        self.filtro_tipo_var = StringVar(value="produto")
        self.plano_nome = "—"

        self.tela_login()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def request_json(self, method, url, **kwargs):
        r = requests.request(method, url, timeout=15, **kwargs)
        content_type = r.headers.get("content-type", "")
        data = r.json() if "application/json" in content_type else {}
        return r, data

    def carregar_plano_atual(self):
        if not self.token or self.tipo_login.get() != "empresa":
            self.plano_nome = "—"
            return
        try:
            r, data = self.request_json(
                "GET",
                f"{self.api}/empresa/plano",
                params={"token": self.token}
            )
            if r.status_code == 200:
                self.plano_nome = data.get("plano_nome", "—")
        except Exception:
            self.plano_nome = "—"

    def criar_topo(self, titulo="RK Sistemas"):
        topo = CTkFrame(self, height=70)
        topo.pack(fill="x", padx=10, pady=10)

        CTkLabel(topo, text=titulo, font=("Arial", 24, "bold")).pack(side="left", padx=15)

        direita = CTkFrame(topo, fg_color="transparent")
        direita.pack(side="right", padx=10)

        if self.token and self.tipo_login.get() == "empresa":
            CTkLabel(direita, text=f"Plano: {self.plano_nome}", font=("Arial", 12)).pack(side="left", padx=8)

        if self.tipo_login.get() == "admin":
            CTkButton(direita, text="Empresas", width=90, command=self.tela_admin_empresas).pack(side="left", padx=4)
        else:
            CTkButton(direita, text="PDV", width=80, command=self.tela_pdv).pack(side="left", padx=4)
            CTkButton(direita, text="Mesas", width=80, command=self.tela_mesas).pack(side="left", padx=4)
            CTkButton(direita, text="Lanches", width=90, command=self.tela_lanches).pack(side="left", padx=4)
            CTkButton(direita, text="Produtos", width=90, command=self.tela_produtos).pack(side="left", padx=4)
            CTkButton(direita, text="Financeiro", width=100, command=self.tela_financeiro).pack(side="left", padx=4)
            CTkButton(direita, text="Relatórios", width=100, command=self.tela_relatorios).pack(side="left", padx=4)
            CTkButton(direita, text="⚙", width=50, command=self.tela_configuracoes).pack(side="left", padx=4)

        CTkButton(direita, text="Sair", width=80, command=self.tela_login).pack(side="left", padx=4)

    def tela_login(self):
        self.clear()
        self.token = None
        self.plano_nome = "—"

        container = CTkFrame(self)
        container.pack(expand=True, padx=30, pady=30)

        CTkLabel(container, text="RK Sistemas", font=("Arial", 30, "bold")).pack(pady=(25, 10))
        CTkLabel(container, text="Acesso ao sistema", font=("Arial", 16)).pack(pady=(0, 15))

        tipo_frame = CTkFrame(container)
        tipo_frame.pack(pady=10, padx=20, fill="x")

        CTkLabel(tipo_frame, text="Tipo de login:").pack(anchor="w", padx=10, pady=(10, 5))
        CTkRadioButton(tipo_frame, text="Empresa", variable=self.tipo_login, value="empresa").pack(anchor="w", padx=15, pady=4)
        CTkRadioButton(tipo_frame, text="Admin", variable=self.tipo_login, value="admin").pack(anchor="w", padx=15, pady=(0, 10))

        self.email = CTkEntry(container, placeholder_text="Email", width=340)
        self.email.pack(pady=8)

        self.senha = CTkEntry(container, placeholder_text="Senha", show="*", width=340)
        self.senha.pack(pady=8)

        self.api_entry = CTkEntry(container, width=340)
        self.api_entry.insert(0, self.api)
        self.api_entry.pack(pady=8)

        CTkButton(container, text="Entrar", width=220, height=40, command=self.login).pack(pady=18)

    def login(self):
        self.api = self.api_entry.get().strip()
        email = self.email.get().strip()
        senha = self.senha.get().strip()

        if not email or not senha:
            messagebox.showwarning("Aviso", "Preencha email e senha.")
            return

        rota = "/empresa/login" if self.tipo_login.get() == "empresa" else "/admin/login"

        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}{rota}",
                json={"email": email, "senha": senha}
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", f"Não foi possível entrar.\n{data.get('detail', r.text)}")
                return

            self.token = data["token"]

            if self.tipo_login.get() == "admin":
                self.tela_admin_empresas()
            else:
                self.carregar_plano_atual()
                self.tela_pdv()

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar ao servidor.\n{e}")

    # =========================
    # ADMIN
    # =========================

    def tela_admin_empresas(self):
        self.clear()
        self.criar_topo("Painel Admin - Empresas")

        principal = CTkFrame(self)
        principal.pack(fill="both", expand=True, padx=15, pady=15)

        esquerda = CTkFrame(principal, width=420)
        esquerda.pack(side="left", fill="y", padx=(0, 8))
        esquerda.pack_propagate(False)

        direita = CTkScrollableFrame(principal)
        direita.pack(side="right", fill="both", expand=True, padx=(8, 0))

        CTkLabel(esquerda, text="Criar empresa", font=("Arial", 18, "bold")).pack(pady=15)

        self.emp_nome = CTkEntry(esquerda, placeholder_text="Nome da empresa", width=320)
        self.emp_nome.pack(pady=8)

        self.emp_email = CTkEntry(esquerda, placeholder_text="Email da empresa", width=320)
        self.emp_email.pack(pady=8)

        self.emp_senha = CTkEntry(esquerda, placeholder_text="Senha da empresa", width=320)
        self.emp_senha.pack(pady=8)

        CTkButton(
            esquerda,
            text="Criar Empresa",
            width=220,
            height=40,
            command=self.criar_empresa_admin
        ).pack(pady=15)

        CTkLabel(direita, text="Empresas cadastradas", font=("Arial", 18, "bold")).pack(anchor="w", pady=10)

        self.admin_lista_empresas = direita
        self.carregar_empresas_admin()

    def criar_empresa_admin(self):
        nome = self.emp_nome.get().strip()
        email = self.emp_email.get().strip()
        senha = self.emp_senha.get().strip()

        if not nome or not email or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos.")
            return

        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}/admin/empresa",
                params={"token": self.token},
                json={"nome": nome, "email": email, "senha": senha}
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", data.get("detail", r.text))
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Empresa criada"))
            self.emp_nome.delete(0, "end")
            self.emp_email.delete(0, "end")
            self.emp_senha.delete(0, "end")
            self.carregar_empresas_admin()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar empresa.\n{e}")

    def carregar_empresas_admin(self):
        for w in self.admin_lista_empresas.winfo_children():
            if isinstance(w, CTkFrame):
                w.destroy()

        try:
            r, empresas = self.request_json(
                "GET",
                f"{self.api}/admin/empresas",
                params={"token": self.token}
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", "Não foi possível carregar empresas.")
                return

            for empresa in empresas:
                card = CTkFrame(self.admin_lista_empresas)
                card.pack(fill="x", pady=8, padx=5)

                topo = CTkFrame(card, fg_color="transparent")
                topo.pack(fill="x", padx=10, pady=(10, 0))

                CTkLabel(
                    topo,
                    text=f"{empresa['nome']}",
                    font=("Arial", 16, "bold")
                ).pack(side="left")

                CTkLabel(
                    topo,
                    text=f"Plano: {empresa.get('plano_nome', '-')}",
                    font=("Arial", 13)
                ).pack(side="right")

                CTkLabel(
                    card,
                    text=f"Email: {empresa['email']} | Status: {empresa.get('status', '-')} | Vencimento: {empresa.get('vencimento', '-')}",
                ).pack(anchor="w", padx=10, pady=8)

                acoes = CTkFrame(card, fg_color="transparent")
                acoes.pack(fill="x", padx=10, pady=(0, 10))

                plano_var = StringVar(value="1")
                planos_menu = CTkOptionMenu(
                    acoes,
                    values=["1", "2", "3"],
                    variable=plano_var,
                    width=90
                )
                planos_menu.pack(side="left", padx=4)

                CTkButton(
                    acoes,
                    text="Trocar Plano",
                    width=120,
                    command=lambda eid=empresa["id"], pv=plano_var: self.admin_trocar_plano(eid, pv.get())
                ).pack(side="left", padx=4)

                CTkButton(
                    acoes,
                    text="Ativar",
                    width=80,
                    command=lambda eid=empresa["id"]: self.admin_alterar_status(eid, "ativo")
                ).pack(side="left", padx=4)

                CTkButton(
                    acoes,
                    text="Pausar",
                    width=80,
                    command=lambda eid=empresa["id"]: self.admin_alterar_status(eid, "pausado")
                ).pack(side="left", padx=4)

                CTkButton(
                    acoes,
                    text="Bloquear",
                    width=90,
                    command=lambda eid=empresa["id"]: self.admin_alterar_status(eid, "bloqueado")
                ).pack(side="left", padx=4)

                CTkButton(
                    acoes,
                    text="Cancelar",
                    width=90,
                    command=lambda eid=empresa["id"]: self.admin_alterar_status(eid, "cancelado")
                ).pack(side="left", padx=4)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar empresas.\n{e}")

    def admin_trocar_plano(self, empresa_id: int, plano_id: str):
        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}/admin/empresa/plano",
                params={
                    "token": self.token,
                    "empresa_id": empresa_id,
                    "plano_id": int(plano_id)
                }
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", data.get("detail", r.text))
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Plano alterado"))
            self.carregar_empresas_admin()

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível trocar o plano.\n{e}")

    def admin_alterar_status(self, empresa_id: int, status: str):
        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}/admin/empresa/status",
                params={
                    "token": self.token,
                    "empresa_id": empresa_id,
                    "status": status
                }
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", data.get("detail", r.text))
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Status alterado"))
            self.carregar_empresas_admin()

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível alterar status.\n{e}")

    # =========================
    # EMPRESA
    # =========================

    def tela_pdv(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("PDV - RK Sistemas")

        busca_frame = CTkFrame(self)
        busca_frame.pack(fill="x", padx=10, pady=5)

        self.busca = CTkEntry(busca_frame, placeholder_text="Pesquisar item pelo nome...", width=350)
        self.busca.pack(side="left", padx=8, pady=8)

        CTkOptionMenu(
            busca_frame,
            values=["produto", "lanche"],
            variable=self.filtro_tipo_var,
            width=140
        ).pack(side="left", padx=5)

        CTkButton(busca_frame, text="Buscar", width=100, command=self.buscar_produtos).pack(side="left", padx=5)
        CTkButton(busca_frame, text="Limpar busca", width=120, command=self.carregar_produtos).pack(side="left", padx=5)

        principal = CTkFrame(self)
        principal.pack(fill="both", expand=True, padx=10, pady=10)

        esquerda = CTkFrame(principal)
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 5))

        direita = CTkFrame(principal, width=350)
        direita.pack(side="right", fill="y", padx=(5, 0))
        direita.pack_propagate(False)

        CTkLabel(esquerda, text="Itens", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.produtos_frame = CTkScrollableFrame(esquerda)
        self.produtos_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        CTkLabel(esquerda, text="Adicionais", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=(5, 5))
        self.adicionais_frame = CTkScrollableFrame(esquerda, height=170)
        self.adicionais_frame.pack(fill="x", padx=10, pady=(0, 10))

        CTkLabel(direita, text="Caixa / Carrinho", font=("Arial", 18, "bold")).pack(pady=10)

        self.box = CTkTextbox(direita, height=280)
        self.box.pack(fill="x", padx=10, pady=10)

        CTkLabel(direita, text="Desconto (R$)").pack(anchor="w", padx=10)
        self.desconto_entry = CTkEntry(direita, placeholder_text="0.00")
        self.desconto_entry.pack(fill="x", padx=10, pady=(0, 10))
        self.desconto_entry.bind("<KeyRelease>", lambda event: self.atualizar_carrinho())

        CTkLabel(direita, text="Método de pagamento").pack(anchor="w", padx=10)
        CTkOptionMenu(
            direita,
            values=["dinheiro", "pix", "qr_code", "cartao_credito", "cartao_debito"],
            variable=self.pagamento_var
        ).pack(fill="x", padx=10, pady=(0, 10))

        self.total_label = CTkLabel(direita, text="Total: R$ 0.00", font=("Arial", 20, "bold"))
        self.total_label.pack(pady=10)

        CTkButton(direita, text="Finalizar Venda", height=40, command=self.finalizar).pack(fill="x", padx=10, pady=5)
        CTkButton(direita, text="Limpar Carrinho", height=40, command=self.limpar_carrinho).pack(fill="x", padx=10, pady=5)

        self.carregar_produtos()
        self.carregar_adicionais()

    def tela_produtos(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("Produtos - RK Sistemas")
        self.tela_cadastro_itens("produto")

    def tela_lanches(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("Lanches - RK Sistemas")
        self.tela_cadastro_itens("lanche")

    def tela_cadastro_itens(self, tipo):
        frame = CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        titulo = "Cadastro de Produtos" if tipo == "produto" else "Cadastro de Lanches"
        CTkLabel(frame, text=titulo, font=("Arial", 20, "bold")).pack(pady=15)

        self.cad_nome = CTkEntry(frame, placeholder_text="Nome", width=350)
        self.cad_nome.pack(pady=8)

        self.cad_preco = CTkEntry(frame, placeholder_text="Preço", width=350)
        self.cad_preco.pack(pady=8)

        self.cad_estoque = CTkEntry(frame, placeholder_text="Estoque", width=350)
        self.cad_estoque.pack(pady=8)

        CTkButton(
            frame,
            text="Cadastrar",
            width=200,
            command=lambda: self.cadastrar_item(tipo)
        ).pack(pady=15)

        self.lista_cadastro = CTkScrollableFrame(frame)
        self.lista_cadastro.pack(fill="both", expand=True, padx=10, pady=10)

        self.carregar_lista_cadastro(tipo)

    def cadastrar_item(self, tipo):
        try:
            nome = self.cad_nome.get().strip()
            preco = float(self.cad_preco.get().replace(",", "."))
            estoque = int(self.cad_estoque.get())

            r, data = self.request_json(
                "POST",
                f"{self.api}/produto",
                json={
                    "token": self.token,
                    "nome": nome,
                    "preco": preco,
                    "estoque": estoque,
                    "tipo": tipo
                }
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", data.get("detail", r.text))
                return

            messagebox.showinfo("Sucesso", f"Item cadastrado com código {data.get('codigo', '')}")

            self.cad_nome.delete(0, "end")
            self.cad_preco.delete(0, "end")
            self.cad_estoque.delete(0, "end")
            self.carregar_lista_cadastro(tipo)

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível cadastrar.\n{e}")

    def carregar_lista_cadastro(self, tipo):
        for w in self.lista_cadastro.winfo_children():
            w.destroy()

        try:
            r, itens = self.request_json(
                "GET",
                f"{self.api}/produtos",
                params={"token": self.token, "tipo": tipo}
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", "Erro ao carregar itens.")
                return

            if not itens:
                CTkLabel(self.lista_cadastro, text="Nenhum item cadastrado.").pack(pady=10)
                return

            for item in itens:
                card = CTkFrame(self.lista_cadastro)
                card.pack(fill="x", padx=5, pady=5)

                CTkLabel(
                    card,
                    text=f"{item['nome']} | Código: {item['codigo']} | R$ {float(item['preco']):.2f} | Estoque: {item['estoque']}"
                ).pack(anchor="w", padx=10, pady=10)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao listar.\n{e}")

    def tela_mesas(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("Mesas - RK Sistemas")

        frame = CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(frame, text="Módulo de mesas", font=("Arial", 20, "bold")).pack(pady=20)
        CTkLabel(frame, text="Aqui vamos colocar abertura de mesa, comandas e histórico.").pack(pady=10)

    def tela_financeiro(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("Financeiro - RK Sistemas")

        frame = CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(frame, text="Financeiro", font=("Arial", 20, "bold")).pack(pady=20)
        CTkButton(frame, text="Contas a Pagar", width=220).pack(pady=8)
        CTkButton(frame, text="Contas a Receber", width=220).pack(pady=8)
        CTkButton(frame, text="Fluxo de Caixa", width=220).pack(pady=8)

    def tela_relatorios(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("Relatórios - RK Sistemas")

        frame = CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(frame, text="Relatórios", font=("Arial", 20, "bold")).pack(pady=20)
        CTkButton(frame, text="Vendas", width=220).pack(pady=8)
        CTkButton(frame, text="Produtos mais vendidos", width=220).pack(pady=8)
        CTkButton(frame, text="Lucro", width=220).pack(pady=8)

    def tela_configuracoes(self):
        self.clear()
        self.carregar_plano_atual()
        self.criar_topo("Configurações - RK Sistemas")

        frame = CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        CTkLabel(frame, text="Integrações", font=("Arial", 20, "bold")).pack(pady=15)

        self.cfg_whatsapp_numero = CTkEntry(frame, placeholder_text="WhatsApp número")
        self.cfg_whatsapp_numero.pack(fill="x", padx=10, pady=5)

        self.cfg_whatsapp_token = CTkEntry(frame, placeholder_text="WhatsApp token / código")
        self.cfg_whatsapp_token.pack(fill="x", padx=10, pady=5)

        self.cfg_whatsapp_webhook = CTkEntry(frame, placeholder_text="WhatsApp webhook / link")
        self.cfg_whatsapp_webhook.pack(fill="x", padx=10, pady=5)

        self.cfg_ifood = CTkEntry(frame, placeholder_text="Token iFood")
        self.cfg_ifood.pack(fill="x", padx=10, pady=5)

        self.cfg_aiqfome = CTkEntry(frame, placeholder_text="Token aiqfome")
        self.cfg_aiqfome.pack(fill="x", padx=10, pady=5)

        self.cfg_uber = CTkEntry(frame, placeholder_text="Token Uber Eats")
        self.cfg_uber.pack(fill="x", padx=10, pady=5)

        CTkButton(frame, text="Testar WhatsApp", command=self.testar_whatsapp).pack(fill="x", padx=10, pady=5)
        CTkButton(frame, text="Testar Delivery", command=self.testar_delivery).pack(fill="x", padx=10, pady=5)

        CTkLabel(frame, text="Pagamentos", font=("Arial", 20, "bold")).pack(pady=15)

        self.pg_pix = CTkCheckBox(frame, text="PIX")
        self.pg_pix.pack(anchor="w", padx=10, pady=3)

        self.pg_qrcode = CTkCheckBox(frame, text="QR Code")
        self.pg_qrcode.pack(anchor="w", padx=10, pady=3)

        self.pg_credito = CTkCheckBox(frame, text="Cartão de Crédito")
        self.pg_credito.pack(anchor="w", padx=10, pady=3)

        self.pg_debito = CTkCheckBox(frame, text="Cartão de Débito")
        self.pg_debito.pack(anchor="w", padx=10, pady=3)

        self.pg_dinheiro = CTkCheckBox(frame, text="Dinheiro")
        self.pg_dinheiro.pack(anchor="w", padx=10, pady=3)

        CTkLabel(frame, text="Impressora térmica", font=("Arial", 20, "bold")).pack(pady=15)

        self.imp_nome = CTkEntry(frame, placeholder_text="Nome da impressora")
        self.imp_nome.pack(fill="x", padx=10, pady=5)

        self.imp_porta = CTkEntry(frame, placeholder_text="Porta / conexão")
        self.imp_porta.pack(fill="x", padx=10, pady=5)

        self.imp_largura = CTkEntry(frame, placeholder_text="Largura da bobina (ex: 80mm)")
        self.imp_largura.pack(fill="x", padx=10, pady=5)

        self.imp_corte = CTkCheckBox(frame, text="Cortar papel automaticamente")
        self.imp_corte.pack(anchor="w", padx=10, pady=5)

        CTkButton(frame, text="Salvar Configurações", height=42, command=self.salvar_configuracoes).pack(fill="x", padx=10, pady=20)

        self.carregar_configuracoes()

    def testar_whatsapp(self):
        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}/whatsapp/teste",
                params={"token": self.token}
            )
            if r.status_code != 200:
                messagebox.showwarning("Plano", data.get("detail", "Bloqueado"))
                return
            messagebox.showinfo("WhatsApp", data.get("msg", "Liberado"))
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def testar_delivery(self):
        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}/delivery/teste",
                params={"token": self.token}
            )
            if r.status_code != 200:
                messagebox.showwarning("Plano", data.get("detail", "Bloqueado"))
                return
            messagebox.showinfo("Delivery", data.get("msg", "Liberado"))
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def carregar_configuracoes(self):
        try:
            r, cfg = self.request_json(
                "GET",
                f"{self.api}/configuracoes",
                params={"token": self.token}
            )

            if r.status_code != 200:
                return

            if not cfg:
                self.pg_pix.select()
                self.pg_qrcode.select()
                self.pg_credito.select()
                self.pg_debito.select()
                self.pg_dinheiro.select()
                self.imp_corte.select()
                return

            self._set_entry(self.cfg_whatsapp_numero, cfg.get("whatsapp_numero", ""))
            self._set_entry(self.cfg_whatsapp_token, cfg.get("whatsapp_token", ""))
            self._set_entry(self.cfg_whatsapp_webhook, cfg.get("whatsapp_webhook", ""))
            self._set_entry(self.cfg_ifood, cfg.get("ifood_token", ""))
            self._set_entry(self.cfg_aiqfome, cfg.get("aiqfome_token", ""))
            self._set_entry(self.cfg_uber, cfg.get("uber_token", ""))
            self._set_entry(self.imp_nome, cfg.get("impressora_nome", ""))
            self._set_entry(self.imp_porta, cfg.get("impressora_porta", ""))
            self._set_entry(self.imp_largura, cfg.get("impressora_largura", "80mm"))

            self._set_check(self.pg_pix, cfg.get("pagamento_pix", 1))
            self._set_check(self.pg_qrcode, cfg.get("pagamento_qrcode", 1))
            self._set_check(self.pg_credito, cfg.get("pagamento_cartao_credito", 1))
            self._set_check(self.pg_debito, cfg.get("pagamento_cartao_debito", 1))
            self._set_check(self.pg_dinheiro, cfg.get("pagamento_dinheiro", 1))
            self._set_check(self.imp_corte, cfg.get("impressora_corta_papel", 1))

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar configurações.\n{e}")

    def salvar_configuracoes(self):
        try:
            r, data = self.request_json(
                "POST",
                f"{self.api}/configuracoes/salvar",
                json={
                    "token": self.token,
                    "whatsapp_numero": self.cfg_whatsapp_numero.get().strip(),
                    "whatsapp_token": self.cfg_whatsapp_token.get().strip(),
                    "whatsapp_webhook": self.cfg_whatsapp_webhook.get().strip(),
                    "ifood_token": self.cfg_ifood.get().strip(),
                    "aiqfome_token": self.cfg_aiqfome.get().strip(),
                    "uber_token": self.cfg_uber.get().strip(),
                    "pagamento_pix": self.pg_pix.get() == 1,
                    "pagamento_qrcode": self.pg_qrcode.get() == 1,
                    "pagamento_cartao_credito": self.pg_credito.get() == 1,
                    "pagamento_cartao_debito": self.pg_debito.get() == 1,
                    "pagamento_dinheiro": self.pg_dinheiro.get() == 1,
                    "impressora_nome": self.imp_nome.get().strip(),
                    "impressora_porta": self.imp_porta.get().strip(),
                    "impressora_largura": self.imp_largura.get().strip() or "80mm",
                    "impressora_corta_papel": self.imp_corte.get() == 1
                }
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", data.get("detail", r.text))
                return

            messagebox.showinfo("Sucesso", data.get("msg", "Configurações salvas"))

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar configurações.\n{e}")

    def carregar_produtos(self):
        try:
            tipo = self.filtro_tipo_var.get()
            r, dados = self.request_json(
                "GET",
                f"{self.api}/produtos",
                params={"token": self.token, "tipo": tipo}
            )
            if r.status_code != 200:
                messagebox.showerror("Erro", "Erro ao carregar itens.")
                return
            self.render_produtos(dados)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar itens.\n{e}")

    def buscar_produtos(self):
        nome = self.busca.get().strip()
        tipo = self.filtro_tipo_var.get()

        if not nome:
            self.carregar_produtos()
            return

        try:
            r, dados = self.request_json(
                "GET",
                f"{self.api}/produtos/buscar",
                params={"token": self.token, "nome": nome, "tipo": tipo}
            )
            if r.status_code != 200:
                messagebox.showerror("Erro", "Erro na busca.")
                return
            self.render_produtos(dados)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro na busca.\n{e}")

    def render_produtos(self, produtos):
        for w in self.produtos_frame.winfo_children():
            w.destroy()

        if not produtos:
            CTkLabel(self.produtos_frame, text="Nenhum item encontrado.").pack(pady=10)
            return

        for p in produtos:
            item = CTkFrame(self.produtos_frame)
            item.pack(fill="x", padx=5, pady=6)

            CTkLabel(item, text=p["nome"], font=("Arial", 15, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
            CTkLabel(
                item,
                text=f"Código: {p['codigo']}   |   Preço: R$ {float(p['preco']):.2f}   |   Estoque: {p['estoque']}"
            ).pack(anchor="w", padx=10, pady=(0, 8))

            CTkButton(item, text="Adicionar", width=120, command=lambda x=p: self.add_prod(x)).pack(anchor="e", padx=10, pady=(0, 8))

    def carregar_adicionais(self):
        try:
            r, dados = self.request_json(
                "GET",
                f"{self.api}/adicionais",
                params={"token": self.token}
            )
            if r.status_code != 200:
                messagebox.showerror("Erro", "Erro ao carregar adicionais.")
                return
            self.render_adicionais(dados)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar adicionais.\n{e}")

    def render_adicionais(self, adicionais):
        for w in self.adicionais_frame.winfo_children():
            w.destroy()

        if not adicionais:
            CTkLabel(self.adicionais_frame, text="Nenhum adicional cadastrado.").pack(pady=10)
            return

        for a in adicionais:
            item = CTkFrame(self.adicionais_frame)
            item.pack(fill="x", padx=5, pady=4)

            CTkLabel(item, text=f"{a['nome']}  |  +R$ {float(a['preco']):.2f}").pack(side="left", padx=10, pady=8)
            CTkButton(item, text="Adicionar", width=110, command=lambda x=a: self.add_add(x)).pack(side="right", padx=10, pady=6)

    def add_prod(self, p):
        self.carrinho.append(p)
        self.total += float(p["preco"])
        self.atualizar_carrinho()

    def add_add(self, a):
        self.adicionais.append(a)
        self.total += float(a["preco"])
        self.atualizar_carrinho()

    def obter_desconto(self):
        texto = self.desconto_entry.get().strip().replace(",", ".")
        if not texto:
            return 0.0
        try:
            return max(float(texto), 0.0)
        except ValueError:
            return 0.0

    def atualizar_carrinho(self):
        self.box.delete("0.0", "end")

        if self.carrinho:
            self.box.insert("end", "ITENS\n")
            self.box.insert("end", "------------------------------\n")
            for p in self.carrinho:
                self.box.insert("end", f"{p['nome']}  -  R$ {float(p['preco']):.2f}\n")

        if self.adicionais:
            self.box.insert("end", "\nADICIONAIS\n")
            self.box.insert("end", "------------------------------\n")
            for a in self.adicionais:
                self.box.insert("end", f"+ {a['nome']}  -  R$ {float(a['preco']):.2f}\n")

        desconto = self.obter_desconto()
        total_final = max(self.total - desconto, 0.0)

        self.box.insert("end", "\n------------------------------\n")
        self.box.insert("end", f"Subtotal: R$ {self.total:.2f}\n")
        self.box.insert("end", f"Desconto: R$ {desconto:.2f}\n")
        self.box.insert("end", f"Pagamento: {self.pagamento_var.get()}\n")
        self.box.insert("end", f"Total final: R$ {total_final:.2f}\n")

        self.total_label.configure(text=f"Total: R$ {total_final:.2f}")

    def limpar_carrinho(self):
        self.total = 0.0
        self.carrinho = []
        self.adicionais = []
        self.pagamento_var.set("dinheiro")
        if hasattr(self, "desconto_entry"):
            self.desconto_entry.delete(0, "end")
        self.atualizar_carrinho()

    def finalizar(self):
        try:
            desconto = self.obter_desconto()

            r, resposta = self.request_json(
                "POST",
                f"{self.api}/venda",
                json={
                    "token": self.token,
                    "itens": [p["id"] for p in self.carrinho],
                    "adicionais": [a["id"] for a in self.adicionais],
                    "desconto": desconto,
                    "metodo_pagamento": self.pagamento_var.get()
                }
            )

            if r.status_code != 200:
                messagebox.showerror("Erro", f"Falha ao finalizar venda.\n{resposta.get('detail', r.text)}")
                return

            messagebox.showinfo(
                "Venda",
                f"{resposta.get('msg', 'Venda finalizada')}\n"
                f"Pagamento: {resposta.get('metodo_pagamento', '')}\n"
                f"Total: R$ {float(resposta.get('total', 0)):.2f}"
            )
            self.limpar_carrinho()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao finalizar venda.\n{e}")

    def _set_entry(self, entry, valor):
        entry.delete(0, "end")
        entry.insert(0, valor)

    def _set_check(self, checkbox, valor):
        if int(valor) == 1:
            checkbox.select()
        else:
            checkbox.deselect()


if __name__ == "__main__":
    app = App()
    app.mainloop()