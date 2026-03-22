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


class App(CTk):
    def __init__(self):
        super().__init__()

        self.title("GSI Sistemas")
        self.geometry("1550x900")
        self.configure(fg_color=COR_FUNDO)

        self.api = "https://rk-sistemas1.onrender.com"
        self.token = None
        self.tipo_login = StringVar(value="empresa")

        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"

        self.sidebar = None
        self.content = None
        self._current_screen = None

        self.logo_top = None
        self.logo_login = None
        self.logo_bg = None
        self.bg_label = None
        self._carregar_logo()

        self.login_screen()

    def _gerar_logo_transparente(self, img_rgba: Image.Image, alpha: int = 35) -> Image.Image:
        nova = img_rgba.copy().convert("RGBA")
        pixels = []
        for r, g, b, a in nova.getdata():
            if a == 0:
                pixels.append((r, g, b, 0))
            else:
                pixels.append((r, g, b, alpha))
        nova.putdata(pixels)
        return nova

    def _carregar_logo(self):
        if os.path.exists("logo.png"):
            img = Image.open("logo.png").convert("RGBA")
            img_bg = self._gerar_logo_transparente(img, alpha=35)
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
        return CTkButton(parent, text=text, command=command, fg_color=color, hover_color=hover, text_color="white", corner_radius=10, **kwargs)

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

    def login_screen(self):
        self.clear()
        self.token = None
        self.usuario_tipo = None
        self.usuario_nome = ""
        self.usuario_cargo = ""
        self.plano_nome = "—"

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
        CTkRadioButton(tipo_frame, text="Admin Global", variable=self.tipo_login, value="admin").pack(anchor="w", padx=15, pady=3)
        CTkRadioButton(tipo_frame, text="Colaborador", variable=self.tipo_login, value="colaborador").pack(anchor="w", padx=15, pady=(3, 10))

        self.login_email = CTkEntry(box, width=360, placeholder_text="Email")
        self.login_email.pack(pady=8)

        self.login_senha = CTkEntry(box, width=360, placeholder_text="Senha", show="*")
        self.login_senha.pack(pady=8)

        self.login_api = CTkEntry(box, width=360)
        self.login_api.insert(0, self.api)
        self.login_api.pack(pady=8)

        self._botao(box, "Entrar", self.do_login, color=COR_AZUL, hover=COR_AZUL_HOVER, width=220, height=42).pack(pady=18)

    def do_login(self):
        self.api = self.login_api.get().strip()
        rota = {
            "empresa": "/empresa/login",
            "admin": "/admin/login",
            "colaborador": "/colaborador/login",
        }[self.tipo_login.get()]

        r, data = self.request_json(
            "POST",
            f"{self.api}{rota}",
            json={"email": self.login_email.get().strip(), "senha": self.login_senha.get().strip()},
        )
        if r.status_code != 200:
            self.api_error("Erro de login", data)
            return

        self.token = data["token"]
        self.usuario_tipo = self.tipo_login.get()
        self.usuario_nome = data.get("nome", "Usuário")
        self.usuario_cargo = data.get("cargo", "")

        if self.usuario_tipo == "admin":
            self.admin_empresas_screen()
        else:
            self.dashboard_screen()

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

        if self.usuario_nome:
            CTkLabel(right, text=f"{self.usuario_nome} | {self.usuario_cargo}", font=("Arial", 13, "bold"), text_color=COR_TEXTO).pack(side="left", padx=10)

        self._botao(right, "☰", self.config_popup, color=COR_CINZA, hover=COR_CINZA_HOVER, width=42).pack(side="left", padx=4)
        self._botao(right, "Atualizar", self.refresh_screen, color=COR_LARANJA, hover=COR_LARANJA_HOVER, width=96).pack(side="left", padx=4)
        self._botao(right, "Sair", self.login_screen, color=COR_VERMELHO, hover=COR_VERMELHO_HOVER, width=80).pack(side="left", padx=4)

        main = CTkFrame(fundo, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.sidebar = CTkFrame(main, width=270, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        self.sidebar.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar.pack_propagate(False)

        self.content = CTkFrame(main, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)

        self._marca_dagua(self.content, 0.50, 0.50)

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
        self._botao(self.sidebar, "Cadastro", self.cadastro_screen, COR_VERDE, COR_VERDE_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Operação", self.operacao_screen, COR_LARANJA, COR_LARANJA_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Impressoras", self.impressoras_screen, COR_CINZA, COR_CINZA_HOVER).pack(fill="x", padx=12, pady=4)
        self._botao(self.sidebar, "Fila Impressão", self.fila_impressao_screen, COR_CINZA, COR_CINZA_HOVER).pack(fill="x", padx=12, pady=4)

    def dashboard_screen(self):
        self._current_screen = self.dashboard_screen
        self.build_shell("Dashboard")
        if self.usuario_tipo == "admin":
            self.admin_sidebar()
        else:
            self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        CTkLabel(box, text="Dashboard", font=("Arial", 24, "bold"), text_color=COR_TEXTO).pack(pady=20)

    def cadastro_screen(self):
        self._current_screen = self.cadastro_screen
        self.build_shell("Cadastro")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        linha = CTkFrame(box, fg_color="transparent")
        linha.pack(pady=20)

        self._botao(linha, "Clientes", self.clientes_screen, COR_VERDE, COR_VERDE_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Fornecedores", self.fornecedores_screen, COR_VERDE, COR_VERDE_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Colaboradores", self.placeholder_screen_colaboradores, COR_AZUL, COR_AZUL_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Entregadores", self.entregadores_screen, COR_LARANJA, COR_LARANJA_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Produtos", self.produtos_screen, COR_CINZA, COR_CINZA_HOVER, width=160).pack(side="left", padx=6)

    def operacao_screen(self):
        self._current_screen = self.operacao_screen
        self.build_shell("Operação")
        self.empresa_sidebar()

        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        linha = CTkFrame(box, fg_color="transparent")
        linha.pack(pady=20)

        self._botao(linha, "Mesa", self.mesas_screen, COR_VERDE, COR_VERDE_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Pedido", self.pedidos_screen, COR_LARANJA, COR_LARANJA_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "Comandas", self.comandas_screen, COR_AZUL, COR_AZUL_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "KDS Cozinha", self.kds_cozinha_screen, COR_CINZA, COR_CINZA_HOVER, width=160).pack(side="left", padx=6)
        self._botao(linha, "KDS Bar", self.kds_bar_screen, COR_CINZA, COR_CINZA_HOVER, width=160).pack(side="left", padx=6)

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

    def impressoras_screen(self):
        self._current_screen = self.impressoras_screen
        self.build_shell("Impressoras")
        self.empresa_sidebar()

        left = self._card(self.content)
        left.configure(width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Nova impressora", font=("Arial", 20, "bold"), text_color=COR_TEXTO).pack(pady=15)

        self.imp_nome = CTkEntry(left, placeholder_text="Nome", width=320)
        self.imp_nome.pack(pady=6)

        self.imp_tipo = CTkOptionMenu(left, values=["cozinha", "bar", "balcao", "entrega", "fiscal"], width=320)
        self.imp_tipo.pack(pady=6)

        self.imp_conexao = CTkEntry(left, placeholder_text="Conexão / IP / USB", width=320)
        self.imp_conexao.pack(pady=6)

        self.imp_modelo = CTkEntry(left, placeholder_text="Modelo", width=320)
        self.imp_modelo.pack(pady=6)

        def salvar():
            r, data = self.request_json(
                "POST",
                f"{self.api}/impressoras",
                json={
                    "token": self.token,
                    "nome": self.imp_nome.get().strip(),
                    "tipo": self.imp_tipo.get(),
                    "conexao": self.imp_conexao.get().strip(),
                    "modelo": self.imp_modelo.get().strip(),
                    "ativa": True,
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Impressora cadastrada"))
            self.impressoras_screen()

        self._botao(left, "Salvar Impressora", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/impressoras", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for imp in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{imp['nome']} | {imp['tipo']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Conexão: {imp.get('conexao', '')}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 10))

    def produtos_screen(self):
        self._current_screen = self.produtos_screen
        self.build_shell("Produtos")
        self.empresa_sidebar()

        left = self._card(self.content)
        left.configure(width=430)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        CTkLabel(left, text="Novo produto", font=("Arial", 20, "bold"), text_color=COR_TEXTO).pack(pady=15)

        self.prod_nome = CTkEntry(left, placeholder_text="Nome", width=320)
        self.prod_nome.pack(pady=6)

        self.prod_preco = CTkEntry(left, placeholder_text="Preço", width=320)
        self.prod_preco.pack(pady=6)

        self.prod_estoque = CTkEntry(left, placeholder_text="Estoque", width=320)
        self.prod_estoque.pack(pady=6)

        self.prod_tipo = CTkOptionMenu(left, values=["produto", "lanche"], width=320)
        self.prod_tipo.pack(pady=6)

        self.prod_setor = CTkOptionMenu(left, values=["cozinha", "bar", "balcao", "nenhum"], width=320)
        self.prod_setor.pack(pady=6)

        r_imp, lista_imps = self.request_json("GET", f"{self.api}/impressoras", params={"token": self.token})
        impressora_map = {"Nenhuma": None}
        if r_imp.status_code == 200:
            for imp in lista_imps:
                impressora_map[f"{imp['nome']} ({imp['tipo']})"] = imp["id"]

        self.prod_impressora = CTkOptionMenu(left, values=list(impressora_map.keys()), width=320)
        self.prod_impressora.pack(pady=6)

        def salvar():
            try:
                preco = float(self.prod_preco.get().replace(",", "."))
            except Exception:
                messagebox.showwarning("Aviso", "Preço inválido")
                return
            try:
                estoque = int(self.prod_estoque.get() or "0")
            except Exception:
                messagebox.showwarning("Aviso", "Estoque inválido")
                return

            r, data = self.request_json(
                "POST",
                f"{self.api}/produto",
                json={
                    "token": self.token,
                    "categoria_id": None,
                    "nome": self.prod_nome.get().strip(),
                    "preco": preco,
                    "estoque": estoque,
                    "tipo": self.prod_tipo.get(),
                    "setor_impressao": self.prod_setor.get(),
                    "impressora_id": impressora_map.get(self.prod_impressora.get()),
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Produto cadastrado"))
            self.produtos_screen()

        self._botao(left, "Salvar Produto", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/produtos", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for prod in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{prod['nome']} | R$ {float(prod['preco']):.2f}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Setor: {prod['setor_impressao']} | Impressora: {prod.get('impressora_nome') or '-'}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 10))

    def mesas_screen(self):
        self._crud_simples(
            titulo="Mesas",
            rota_post="/mesas",
            rota_get="/mesas",
            campos=[("numero", "Número")],
        )

    def comandas_screen(self):
        self._current_screen = self.comandas_screen
        self.build_shell("Comandas")
        self.empresa_sidebar()

        left = self._card(self.content)
        left.configure(width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        self.cmd_mesa_id = CTkEntry(left, placeholder_text="ID da mesa (opcional)", width=320)
        self.cmd_mesa_id.pack(pady=6)
        self.cmd_cliente_id = CTkEntry(left, placeholder_text="ID do cliente (opcional)", width=320)
        self.cmd_cliente_id.pack(pady=6)

        def criar():
            mesa_id = self.cmd_mesa_id.get().strip()
            cliente_id = self.cmd_cliente_id.get().strip()
            r, data = self.request_json(
                "POST",
                f"{self.api}/comandas",
                json={
                    "token": self.token,
                    "mesa_id": int(mesa_id) if mesa_id else None,
                    "cliente_id": int(cliente_id) if cliente_id else None,
                    "origem": "balcao",
                    "observacoes": "",
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Comanda criada"))
            self.comandas_screen()

        self._botao(left, "Criar Comanda", criar, COR_VERDE, COR_VERDE_HOVER).pack(pady=12)

        r, data = self.request_json("GET", f"{self.api}/comandas", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for c in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"Comanda {c['numero']} | {c['status']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Mesa: {c.get('mesa_numero') or '-'} | Cliente: {c.get('cliente_nome') or '-'} | Total: R$ {float(c.get('valor_total') or 0):.2f}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 6))
            btns = CTkFrame(card, fg_color="transparent")
            btns.pack(anchor="e", padx=10, pady=(0, 10))
            self._botao(btns, "Lançar Pedido", lambda cid=c["id"]: self.criar_pedido_popup(cid), COR_AZUL, COR_AZUL_HOVER, width=130).pack(side="left", padx=4)
            self._botao(btns, "Fechar Conta", lambda cid=c["id"]: self.fechar_comanda_popup(cid), COR_LARANJA, COR_LARANJA_HOVER, width=130).pack(side="left", padx=4)

    def pedidos_screen(self):
        self._current_screen = self.pedidos_screen
        self.build_shell("Pedidos")
        self.empresa_sidebar()

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json("GET", f"{self.api}/pedidos", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for ped in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"Pedido {ped['id']} | Comanda {ped.get('comanda_numero') or '-'}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Mesa: {ped.get('mesa_numero') or '-'} | Cliente: {ped.get('cliente_nome') or '-'} | Origem: {ped.get('origem')}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 10))

    def fila_impressao_screen(self):
        self._current_screen = self.fila_impressao_screen
        self.build_shell("Fila de Impressão")
        self.empresa_sidebar()

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(fill="both", expand=True, padx=10, pady=10)

        r, data = self.request_json("GET", f"{self.api}/fila-impressao", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for fila in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{fila['tipo'].upper()} | {fila.get('impressora_nome') or '-'} | {fila['status']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkTextbox(card, height=120).pack(fill="x", padx=10, pady=(0, 10))
            txt = card.winfo_children()[-1]
            txt.insert("1.0", fila["conteudo"])
            txt.configure(state="disabled")

    def criar_pedido_popup(self, comanda_id: int):
        top = CTkToplevel(self)
        top.title(f"Novo pedido - Comanda {comanda_id}")
        top.geometry("620x520")
        top.configure(fg_color=COR_FUNDO)

        frame = self._card(top)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        r, produtos = self.request_json("GET", f"{self.api}/produtos", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", produtos)
            top.destroy()
            return

        mapa_prod = {f"{p['nome']} | R$ {float(p['preco']):.2f}": p["id"] for p in produtos}
        prod_opt = CTkOptionMenu(frame, values=list(mapa_prod.keys()) or ["Sem produtos"], width=420)
        prod_opt.pack(pady=8)

        qtd = CTkEntry(frame, placeholder_text="Quantidade", width=180)
        qtd.pack(pady=8)
        obs = CTkEntry(frame, placeholder_text="Observações", width=420)
        obs.pack(pady=8)

        itens_temp = []
        lista = CTkTextbox(frame, height=180, width=520)
        lista.pack(pady=10)

        def add_item():
            try:
                quantidade = int(qtd.get() or "1")
            except Exception:
                messagebox.showwarning("Aviso", "Quantidade inválida")
                return
            nome = prod_opt.get()
            if nome not in mapa_prod:
                return
            itens_temp.append(
                {
                    "produto_id": mapa_prod[nome],
                    "quantidade": quantidade,
                    "observacoes": obs.get().strip(),
                }
            )
            lista.insert("end", f"{quantidade}x {nome}\n")
            qtd.delete(0, "end")
            obs.delete(0, "end")

        def salvar():
            if not itens_temp:
                messagebox.showwarning("Aviso", "Adicione pelo menos um item")
                return
            r2, data2 = self.request_json(
                "POST",
                f"{self.api}/pedidos",
                json={
                    "token": self.token,
                    "comanda_id": comanda_id,
                    "itens": itens_temp,
                    "origem": "garcom",
                    "observacoes": "",
                },
            )
            if r2.status_code != 200:
                self.api_error("Erro", data2)
                return
            messagebox.showinfo("Sucesso", data2.get("msg", "Pedido criado"))
            top.destroy()
            self.comandas_screen()

        self._botao(frame, "Adicionar Item", add_item, COR_AZUL, COR_AZUL_HOVER).pack(pady=6)
        self._botao(frame, "Salvar Pedido", salvar, COR_VERDE, COR_VERDE_HOVER).pack(pady=6)

    def fechar_comanda_popup(self, comanda_id: int):
        top = CTkToplevel(self)
        top.title(f"Fechar comanda {comanda_id}")
        top.geometry("420x360")
        top.configure(fg_color=COR_FUNDO)

        frame = self._card(top)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        forma = CTkOptionMenu(frame, values=["pix", "credito", "debito", "dinheiro"], width=260)
        forma.pack(pady=10)

        fiscal_var = BooleanVar(value=True)
        entrega_var = BooleanVar(value=False)

        CTkCheckBox(frame, text="Imprimir cupom fiscal no balcão", variable=fiscal_var).pack(anchor="w", padx=20, pady=8)
        CTkCheckBox(frame, text="Imprimir cupom do entregador", variable=entrega_var).pack(anchor="w", padx=20, pady=8)

        def fechar():
            r, data = self.request_json(
                "POST",
                f"{self.api}/comandas/{comanda_id}/fechar",
                json={
                    "token": self.token,
                    "forma_pagamento": forma.get(),
                    "imprimir_fiscal": bool(fiscal_var.get()),
                    "imprimir_entrega": bool(entrega_var.get()),
                },
            )
            if r.status_code != 200:
                self.api_error("Erro", data)
                return
            messagebox.showinfo("Sucesso", data.get("msg", "Comanda fechada"))
            top.destroy()
            self.comandas_screen()

        self._botao(frame, "Fechar Conta", fechar, COR_LARANJA, COR_LARANJA_HOVER).pack(pady=20)

    def kds_cozinha_screen(self):
        self._placeholder("KDS Cozinha")

    def kds_bar_screen(self):
        self._placeholder("KDS Bar")

    def placeholder_screen_colaboradores(self):
        self._placeholder("Colaboradores")

    def _placeholder(self, titulo):
        self._current_screen = lambda: self._placeholder(titulo)
        self.build_shell(titulo)
        self.empresa_sidebar()
        box = self._card(self.content)
        box.pack(fill="both", expand=True, padx=20, pady=20)
        CTkLabel(box, text=titulo, font=("Arial", 24, "bold"), text_color=COR_TEXTO).pack(pady=20)

    def _crud_simples(self, titulo, rota_post, rota_get, campos):
        self._current_screen = lambda: self._crud_simples(titulo, rota_post, rota_get, campos)
        self.build_shell(titulo)
        self.empresa_sidebar()

        left = self._card(self.content)
        left.configure(width=420)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left.pack_propagate(False)

        right = CTkScrollableFrame(self.content, fg_color=COR_CARD, corner_radius=14, border_width=1, border_color=COR_BORDA)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

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
            messagebox.showinfo("Sucesso", data.get("msg", "Salvo"))
            self._crud_simples(titulo, rota_post, rota_get, campos)

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

    def config_popup(self):
        top = CTkToplevel(self)
        top.title("Configurações")
        top.geometry("420x320")
        top.configure(fg_color=COR_FUNDO)

        frame = self._card(top)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        self._botao(frame, "Impressoras", self.impressoras_screen, COR_AZUL, COR_AZUL_HOVER, width=260).pack(pady=8)
        self._botao(frame, "Fila de Impressão", self.fila_impressao_screen, COR_CINZA, COR_CINZA_HOVER, width=260).pack(pady=8)
        self._botao(frame, "Fechar", top.destroy, COR_VERMELHO, COR_VERMELHO_HOVER, width=260).pack(pady=20)

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

        r, data = self.request_json("GET", f"{self.api}/admin/empresas", params={"token": self.token})
        if r.status_code != 200:
            self.api_error("Erro", data)
            return

        for emp in data:
            card = self._card(right)
            card.pack(fill="x", padx=5, pady=5)
            CTkLabel(card, text=f"{emp['nome']} | {emp['email']}", font=("Arial", 16, "bold"), text_color=COR_TEXTO).pack(anchor="w", padx=10, pady=(10, 2))
            CTkLabel(card, text=f"Plano: {emp.get('plano_nome')} | Status: {emp.get('status')}", text_color=COR_SUBTEXTO).pack(anchor="w", padx=10, pady=(0, 10))


if __name__ == "__main__":
    app = App()
    app.mainloop()