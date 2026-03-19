
import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
import requests, io, qrcode
from PIL import Image, ImageTk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

API_URL_PADRAO = "http://127.0.0.1:8000"
COR_BG = "#0F1117"
COR_CARD = "#1F2937"
COR_MENU = "#111827"
COR_PRIMARIA = "#10B981"
COR_SECUNDARIA = "#3B82F6"
COR_TEXTO = "#E5E7EB"
COR_ERRO = "#EF4444"
COR_AVISO = "#F59E0B"

class ApiClient:
    def __init__(self):
        self.base_url = API_URL_PADRAO
        self.token = None
    def set_base_url(self, url): self.base_url = url.rstrip("/")
    def set_token(self, token): self.token = token
    def headers(self): return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    def get(self, endpoint, params=None): return requests.get(f"{self.base_url}{endpoint}", headers=self.headers(), params=params, timeout=20)
    def post(self, endpoint, json=None, params=None): return requests.post(f"{self.base_url}{endpoint}", headers=self.headers(), json=json, params=params, timeout=25)

class GerenceDesktop(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RK Sistemas - App Desktop Profissional")
        self.geometry("1500x860")
        self.configure(fg_color=COR_BG)
        self.api = ApiClient()
        self.usuario = None
        self.empresa = None
        self.carrinho = []
        self.produtos_cache = []
        self.header = ctk.CTkFrame(self, fg_color=COR_CARD, height=72, corner_radius=0)
        self.header.pack(fill="x")
        ctk.CTkLabel(self.header, text="RK Sistemas - Gastronomia Profissional", font=("Segoe UI", 24, "bold")).pack(side="left", padx=18, pady=16)
        self.lbl_status = ctk.CTkLabel(self.header, text="Desconectado", text_color=COR_TEXTO)
        self.lbl_status.pack(side="right", padx=18)
        self.content = ctk.CTkFrame(self, fg_color=COR_BG); self.content.pack(fill="both", expand=True)
        self.show_login()

    def clear_content(self):
        for w in self.content.winfo_children(): w.destroy()
    def safe_request(self, method, endpoint, json=None, params=None):
        try:
            return self.api.get(endpoint, params=params) if method == "GET" else self.api.post(endpoint, json=json, params=params)
        except requests.exceptions.RequestException:
            messagebox.showerror("Conexão", "Não foi possível conectar ao servidor.")
            return None
    def build_tree(self, parent, columns):
        tree = ttk.Treeview(parent, columns=[c[0] for c in columns], show="headings")
        for col_id, title, width in columns:
            tree.heading(col_id, text=title); tree.column(col_id, width=width, anchor="center")
        tree.pack(fill="both", expand=True)
        return tree

    def show_login(self):
        self.clear_content()
        card = ctk.CTkFrame(self.content, fg_color=COR_CARD, corner_radius=18); card.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(card, text="Login da Empresa", font=("Segoe UI", 28, "bold")).pack(padx=40, pady=(28,8))
        ctk.CTkLabel(card, text="Aplicativo de PC conectado ao backend RK Sistemas", text_color=COR_TEXTO).pack(pady=(0,18))
        self.entry_api = ctk.CTkEntry(card, width=420, height=44, placeholder_text="Servidor da API"); self.entry_api.insert(0, API_URL_PADRAO); self.entry_api.pack(pady=8, padx=40)
        self.entry_email = ctk.CTkEntry(card, width=420, height=44, placeholder_text="Email"); self.entry_email.pack(pady=8, padx=40)
        self.entry_senha = ctk.CTkEntry(card, width=420, height=44, placeholder_text="Senha", show="*"); self.entry_senha.pack(pady=8, padx=40)
        self.lbl_login_msg = ctk.CTkLabel(card, text="", text_color=COR_ERRO); self.lbl_login_msg.pack(pady=6)
        ctk.CTkButton(card, text="Entrar", width=420, height=44, fg_color=COR_PRIMARIA, command=self.login).pack(pady=(12,30))

    def login(self):
        self.api.set_base_url(self.entry_api.get().strip())
        r = self.safe_request("POST", "/auth/empresa/login", json={"email": self.entry_email.get().strip(), "senha": self.entry_senha.get().strip()})
        if not r: return
        if r.status_code != 200:
            self.lbl_login_msg.configure(text=r.text); return
        self.api.set_token(r.json()["access_token"])
        me = self.safe_request("GET", "/empresa/me")
        if not me or me.status_code != 200:
            self.lbl_login_msg.configure(text="Não foi possível carregar os dados da empresa."); return
        dados = me.json()
        self.usuario = dados["usuario"]; self.empresa = dados
        self.lbl_status.configure(text=f'{self.empresa["nome_fantasia"]} | {self.usuario["nome"]} | {self.usuario["papel"]}')
        self.show_app()

    def show_app(self):
        self.clear_content()
        self.sidebar = ctk.CTkFrame(self.content, fg_color=COR_MENU, width=250, corner_radius=0); self.sidebar.pack(side="left", fill="y"); self.sidebar.pack_propagate(False)
        ctk.CTkLabel(self.sidebar, text="Módulos", font=("Segoe UI", 22, "bold")).pack(pady=(20,14))
        for texto, comando in [
            ("Dashboard", self.show_dashboard), ("PDV / Caixa", self.show_pdv), ("Mesas / Comandas", self.show_mesas),
            ("KDS / Cozinha", self.show_kds), ("Clientes", self.show_clientes), ("Produtos / Estoque", self.show_produtos),
            ("Financeiro", self.show_financeiro), ("iFood", self.show_ifood)
        ]:
            ctk.CTkButton(self.sidebar, text=texto, width=210, height=42, fg_color=COR_CARD, hover_color="#283548", command=comando).pack(pady=5, padx=15)
        ctk.CTkButton(self.sidebar, text="Logout", width=210, height=42, fg_color=COR_ERRO, command=self.logout).pack(side="bottom", pady=18, padx=15)
        self.main = ctk.CTkFrame(self.content, fg_color=COR_BG); self.main.pack(side="right", fill="both", expand=True, padx=12, pady=12)
        self.show_dashboard()

    def clear_main(self):
        for w in self.main.winfo_children(): w.destroy()
    def logout(self):
        self.api.set_token(None); self.usuario = None; self.empresa = None; self.carrinho = []; self.lbl_status.configure(text="Desconectado"); self.show_login()

    def show_dashboard(self):
        self.clear_main()
        ctk.CTkLabel(self.main, text="Dashboard", font=("Segoe UI", 28, "bold")).pack(anchor="w", pady=(0,14))
        r = self.safe_request("GET", "/empresa/relatorios/resumo")
        if not r or r.status_code != 200:
            return
        resumo = r.json()
        cards = ctk.CTkFrame(self.main, fg_color="transparent"); cards.pack(fill="x")
        for titulo, valor in [("Vendas", f'R$ {resumo["total_vendas"]:.2f}'), ("Produtos", str(resumo["qtd_produtos"])), ("Pedidos", str(resumo["qtd_pedidos"])), ("Pedidos iFood", str(resumo["qtd_ifood"]))]:
            card = ctk.CTkFrame(cards, fg_color=COR_CARD, width=260, height=110); card.pack(side="left", padx=8, pady=8, fill="both", expand=True)
            ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 16)).pack(pady=(18,6))
            ctk.CTkLabel(card, text=valor, font=("Segoe UI", 22, "bold"), text_color=COR_PRIMARIA).pack()
        ctk.CTkLabel(self.main, text="Mais vendidos", font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(20,8))
        frame = ctk.CTkFrame(self.main, fg_color=COR_CARD); frame.pack(fill="both", expand=True)
        tree = self.build_tree(frame, [("produto","Produto",320),("qtd","Quantidade",140)])
        for nome, qtd in resumo.get("mais_vendidos", []):
            tree.insert("", "end", values=(nome, qtd))

    def show_pdv(self):
        self.clear_main()
        ctk.CTkLabel(self.main, text="Frente de Caixa (PDV)", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        corpo = ctk.CTkFrame(self.main, fg_color="transparent"); corpo.pack(fill="both", expand=True, pady=10)
        esquerda = ctk.CTkFrame(corpo, fg_color=COR_CARD); esquerda.pack(side="left", fill="both", expand=True, padx=(0,8))
        direita = ctk.CTkFrame(corpo, fg_color=COR_CARD, width=420); direita.pack(side="right", fill="both", padx=(8,0)); direita.pack_propagate(False)
        barra = ctk.CTkFrame(esquerda, fg_color="transparent"); barra.pack(fill="x", padx=12, pady=12)
        self.entry_busca_produto = ctk.CTkEntry(barra, width=260, placeholder_text="Buscar produto"); self.entry_busca_produto.pack(side="left", padx=5)
        self.entry_busca_produto.bind("<KeyRelease>", lambda e: self.render_pdv_products())
        self.entry_qtd_produto = ctk.CTkEntry(barra, width=90, placeholder_text="Qtd"); self.entry_qtd_produto.insert(0, "1"); self.entry_qtd_produto.pack(side="left", padx=5)
        ctk.CTkButton(barra, text="Atualizar", fg_color=COR_SECUNDARIA, command=self.load_products).pack(side="left", padx=5)
        ctk.CTkButton(barra, text="Adicionar", fg_color=COR_PRIMARIA, command=self.add_selected_to_cart).pack(side="left", padx=5)
        self.tree_pdv_produtos = self.build_tree(esquerda, [("id","ID",60),("codigo","Código",120),("nome","Nome",280),("preco","Preço",110),("estoque","Estoque",100)])
        ctk.CTkLabel(direita, text="Carrinho", font=("Segoe UI", 22, "bold")).pack(pady=(16,8))
        self.tree_cart = self.build_tree(direita, [("id","ID",50),("nome","Nome",180),("qtd","Qtd",60),("subtotal","Subtotal",100)])
        self.lbl_total_cart = ctk.CTkLabel(direita, text="Total: R$ 0,00", font=("Segoe UI", 24, "bold"), text_color=COR_PRIMARIA); self.lbl_total_cart.pack(pady=10)
        self.combo_setor = ctk.CTkComboBox(direita, values=["COZINHA", "BAR"], width=180); self.combo_setor.set("COZINHA"); self.combo_setor.pack(pady=5)
        self.combo_origem = ctk.CTkComboBox(direita, values=["PDV", "GARCOM", "QR", "DELIVERY", "IFOOD", "WHATSAPP"], width=180); self.combo_origem.set("PDV"); self.combo_origem.pack(pady=5)
        ctk.CTkButton(direita, text="Limpar", fg_color=COR_ERRO, command=self.clear_cart).pack(pady=6)
        ctk.CTkButton(direita, text="Lançar pedido", fg_color=COR_PRIMARIA, command=self.finish_order).pack(pady=6)
        self.load_products()

    def load_products(self):
        r = self.safe_request("GET", "/empresa/produtos")
        if not r or r.status_code != 200: return
        self.produtos_cache = r.json()
        self.render_pdv_products()
        if hasattr(self, "tree_produtos_estoque"): self.load_stock()

    def render_pdv_products(self):
        if not hasattr(self, "tree_pdv_produtos"): return
        termo = self.entry_busca_produto.get().strip().lower() if hasattr(self, "entry_busca_produto") else ""
        for i in self.tree_pdv_produtos.get_children(): self.tree_pdv_produtos.delete(i)
        for p in self.produtos_cache:
            if termo and termo not in f'{p["codigo"]} {p["nome"]}'.lower(): continue
            self.tree_pdv_produtos.insert("", "end", values=(p["id"], p["codigo"], p["nome"], f'R$ {p["preco"]:.2f}', p["estoque"]))

    def add_selected_to_cart(self):
        sel = self.tree_pdv_produtos.selection()
        if not sel: return
        qtd = float(self.entry_qtd_produto.get() or 1)
        vals = self.tree_pdv_produtos.item(sel[0], "values")
        produto_id = int(vals[0]); nome = vals[2]; preco = float(str(vals[3]).replace("R$ ","").replace(",", ".")); estoque = float(vals[4])
        atual = next((x for x in self.carrinho if x["produto_id"] == produto_id), None)
        qtd_total = qtd + (atual["quantidade"] if atual else 0)
        if qtd_total > estoque:
            messagebox.showwarning("PDV", "Quantidade acima do estoque."); return
        if atual:
            atual["quantidade"] += qtd; atual["subtotal"] = atual["quantidade"] * atual["preco"]
        else:
            self.carrinho.append({"produto_id": produto_id, "nome": nome, "quantidade": qtd, "preco": preco, "subtotal": qtd * preco})
        self.render_cart()

    def render_cart(self):
        for i in self.tree_cart.get_children(): self.tree_cart.delete(i)
        total = 0
        for c in self.carrinho:
            total += c["subtotal"]
            self.tree_cart.insert("", "end", values=(c["produto_id"], c["nome"], c["quantidade"], f'R$ {c["subtotal"]:.2f}'))
        self.lbl_total_cart.configure(text=f"Total: R$ {total:.2f}")

    def clear_cart(self):
        self.carrinho = []; self.render_cart()

    def finish_order(self):
        if not self.carrinho: return
        cliente = simpledialog.askstring("Cliente", "Nome do cliente (opcional):", parent=self)
        mesa_id = simpledialog.askinteger("Mesa", "ID da mesa (opcional):", parent=self)
        comanda_id = simpledialog.askinteger("Comanda", "ID da comanda (opcional):", parent=self)
        r = self.safe_request("POST", "/empresa/pedidos", json={"mesa_id": mesa_id, "comanda_id": comanda_id, "origem": self.combo_origem.get(), "setor": self.combo_setor.get(), "cliente_nome": cliente, "observacoes": None, "tempo_estimado_min": 20, "itens": [{"produto_id": c["produto_id"], "quantidade": c["quantidade"], "observacoes": None} for c in self.carrinho]})
        if r and r.status_code == 200:
            if mesa_id:
                rm = self.safe_request("GET", "/empresa/mesas")
                if rm and rm.status_code == 200:
                    for m in rm.json():
                        if m["id"] == mesa_id and m.get("pix_code"):
                            self.show_pix_qr(m["pix_code"])
                            break
            self.clear_cart(); self.load_products(); messagebox.showinfo("PDV", "Pedido lançado com sucesso.")
        elif r:
            messagebox.showerror("PDV", r.text)

    def show_pix_qr(self, payload):
        top = ctk.CTkToplevel(self); top.title("QR Code PIX"); top.geometry("460x650"); top.grab_set()
        qr = qrcode.QRCode(version=1, box_size=8, border=2); qr.add_data(payload); qr.make(fit=True); img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO(); img.save(buffer, format="PNG"); buffer.seek(0)
        pil = Image.open(buffer).resize((280, 280)); foto = ImageTk.PhotoImage(pil)
        lbl = ctk.CTkLabel(top, image=foto, text=""); lbl.image = foto; lbl.pack(pady=18)
        txt = ctk.CTkTextbox(top, width=400, height=180); txt.pack(pady=10); txt.insert("1.0", payload)

    def show_mesas(self):
        self.clear_main()
        ctk.CTkLabel(self.main, text="Controle de Mesas e Comandas", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        self.tree_mesas = self.build_tree(self.main, [("id","ID",60),("numero","Mesa",90),("status","Status",120),("cliente","Cliente",220),("total","Total",120)])
        r = self.safe_request("GET", "/empresa/mesas")
        if r and r.status_code == 200:
            for m in r.json():
                self.tree_mesas.insert("", "end", values=(m["id"], m["numero"], m["status"], m["cliente_nome"], f'R$ {m["total"]:.2f}'))

    def show_kds(self):
        self.clear_main()
        ctk.CTkLabel(self.main, text="KDS / Tela da Cozinha", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        scroll = ctk.CTkScrollableFrame(self.main); scroll.pack(fill="both", expand=True, pady=10)
        r = self.safe_request("GET", "/empresa/kds")
        if r and r.status_code == 200:
            for p in r.json():
                cor = COR_ERRO if p["semaforo"] == "vermelho" else COR_PRIMARIA if p["semaforo"] == "verde" else COR_AVISO
                card = ctk.CTkFrame(scroll); card.pack(fill="x", padx=8, pady=8)
                ctk.CTkLabel(card, text=f'Pedido #{p["pedido_id"]} | {p["status"]}', text_color=cor, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=12, pady=(10,4))
                for i in p["itens"]:
                    ctk.CTkLabel(card, text=f'- {i["quantidade"]}x {i["nome"]} | Obs: {i["observacoes"]}').pack(anchor="w", padx=16)

    def show_clientes(self):
        self.clear_main()
        topo = ctk.CTkFrame(self.main, fg_color="transparent"); topo.pack(fill="x")
        ctk.CTkLabel(topo, text="Cadastro de Clientes", font=("Segoe UI", 28, "bold")).pack(side="left")
        ctk.CTkButton(topo, text="Novo cliente", fg_color=COR_PRIMARIA, command=self.new_client).pack(side="right")
        self.tree_clientes = self.build_tree(self.main, [("id","ID",60),("nome","Nome",260),("telefone","Telefone",160),("email","Email",240),("documento","Documento",160)])
        self.load_clients()

    def load_clients(self):
        r = self.safe_request("GET", "/empresa/clientes")
        if not r or r.status_code != 200: return
        for i in self.tree_clientes.get_children(): self.tree_clientes.delete(i)
        for c in r.json():
            self.tree_clientes.insert("", "end", values=(c["id"], c["nome"], c["telefone"], c["email"], c["documento"]))

    def new_client(self):
        nome = simpledialog.askstring("Cliente", "Nome:", parent=self)
        if not nome: return
        telefone = simpledialog.askstring("Cliente", "Telefone:", parent=self)
        email = simpledialog.askstring("Cliente", "Email:", parent=self)
        documento = simpledialog.askstring("Cliente", "Documento:", parent=self)
        endereco = simpledialog.askstring("Cliente", "Endereço:", parent=self)
        r = self.safe_request("POST", "/empresa/clientes", json={"nome": nome, "telefone": telefone, "email": email, "documento": documento, "endereco": endereco, "observacoes": None})
        if r and r.status_code == 200: self.load_clients()

    def show_produtos(self):
        self.clear_main()
        topo = ctk.CTkFrame(self.main, fg_color="transparent"); topo.pack(fill="x")
        ctk.CTkLabel(topo, text="Produtos / Estoque", font=("Segoe UI", 28, "bold")).pack(side="left")
        ctk.CTkButton(topo, text="Novo produto", fg_color=COR_PRIMARIA, command=self.form_product).pack(side="right")
        self.tree_produtos_estoque = self.build_tree(self.main, [("id","ID",60),("codigo","Código",100),("nome","Nome",260),("categoria","Categoria",140),("preco","Preço",100),("estoque","Estoque",100),("fornecedor","Fornecedor",180)])
        self.load_stock()

    def load_stock(self):
        r = self.safe_request("GET", "/empresa/produtos")
        if not r or r.status_code != 200: return
        for i in self.tree_produtos_estoque.get_children(): self.tree_produtos_estoque.delete(i)
        for p in r.json():
            self.tree_produtos_estoque.insert("", "end", values=(p["id"], p["codigo"], p["nome"], p["categoria"], f'R$ {p["preco"]:.2f}', p["estoque"], p["fornecedor"]))

    def form_product(self):
        top = ctk.CTkToplevel(self); top.title("Produto - formulário único"); top.geometry("520x700"); top.grab_set()
        fields = {}
        labels = [("codigo","Código"),("nome","Nome"),("categoria","Categoria"),("descricao","Descrição"),("preco","Preço"),("custo","Custo"),("estoque","Estoque"),("estoque_minimo","Estoque mínimo"),("unidade","Unidade"),("fornecedor","Fornecedor"),("observacoes","Observações")]
        for key, label in labels:
            ctk.CTkLabel(top, text=label).pack(anchor="w", padx=18, pady=(10,0))
            e = ctk.CTkEntry(top, width=460); e.pack(padx=18, pady=4); fields[key] = e
        fields["unidade"].insert(0, "UN")
        e_kg = ctk.CTkCheckBox(top, text="Produto por KG"); e_kg.pack(anchor="w", padx=18, pady=10)
        ativo = ctk.CTkCheckBox(top, text="Ativo"); ativo.select(); ativo.pack(anchor="w", padx=18, pady=4)
        def salvar():
            try:
                payload = {"codigo": fields["codigo"].get() or None, "nome": fields["nome"].get(), "categoria": fields["categoria"].get() or None, "descricao": fields["descricao"].get() or None, "preco": float(fields["preco"].get() or 0), "custo": float(fields["custo"].get() or 0), "estoque": float(fields["estoque"].get() or 0), "estoque_minimo": float(fields["estoque_minimo"].get() or 0), "unidade": fields["unidade"].get() or "UN", "fornecedor": fields["fornecedor"].get() or None, "observacoes": fields["observacoes"].get() or None, "e_kg": bool(e_kg.get()), "ativo": bool(ativo.get())}
            except ValueError:
                messagebox.showerror("Produto", "Preços e estoque precisam ser numéricos."); return
            if not payload["nome"]:
                messagebox.showwarning("Produto", "Informe o nome."); return
            r = self.safe_request("POST", "/empresa/produtos", json=payload)
            if r and r.status_code == 200:
                top.destroy(); self.load_products()
            elif r:
                messagebox.showerror("Produto", r.text)
        ctk.CTkButton(top, text="Salvar produto", fg_color=COR_PRIMARIA, command=salvar).pack(pady=18)

    def show_financeiro(self):
        self.clear_main()
        topo = ctk.CTkFrame(self.main, fg_color="transparent"); topo.pack(fill="x")
        ctk.CTkLabel(topo, text="Financeiro", font=("Segoe UI", 28, "bold")).pack(side="left")
        ctk.CTkButton(topo, text="Novo lançamento", fg_color=COR_PRIMARIA, command=self.new_financial).pack(side="right")
        self.tree_fin = self.build_tree(self.main, [("id","ID",60),("tipo","Tipo",120),("descricao","Descrição",260),("categoria","Categoria",160),("valor","Valor",120),("pago","Pago",80)])
        self.load_financial()

    def load_financial(self):
        r = self.safe_request("GET", "/empresa/financeiro")
        if not r or r.status_code != 200: return
        for i in self.tree_fin.get_children(): self.tree_fin.delete(i)
        for f in r.json():
            self.tree_fin.insert("", "end", values=(f["id"], f["tipo"], f["descricao"], f["categoria"], f'R$ {f["valor"]:.2f}', "SIM" if f["pago"] else "NÃO"))

    def new_financial(self):
        tipo = simpledialog.askstring("Financeiro", "Tipo (pagar/receber):", parent=self)
        descricao = simpledialog.askstring("Financeiro", "Descrição:", parent=self)
        categoria = simpledialog.askstring("Financeiro", "Categoria:", parent=self)
        valor = simpledialog.askfloat("Financeiro", "Valor:", parent=self)
        if not tipo or not descricao or valor is None: return
        r = self.safe_request("POST", "/empresa/financeiro", json={"tipo": tipo, "descricao": descricao, "categoria": categoria, "valor": valor, "vencimento": None})
        if r and r.status_code == 200: self.load_financial()

    def show_ifood(self):
        self.clear_main()
        ctk.CTkLabel(self.main, text="Integração iFood", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        form = ctk.CTkFrame(self.main, fg_color=COR_CARD); form.pack(fill="x", pady=12)
        self.if_merchant = ctk.CTkEntry(form, width=280, placeholder_text="Merchant ID"); self.if_merchant.pack(side="left", padx=6, pady=10)
        self.if_token = ctk.CTkEntry(form, width=320, placeholder_text="Token iFood"); self.if_token.pack(side="left", padx=6, pady=10)
        ctk.CTkButton(form, text="Salvar iFood", fg_color=COR_PRIMARIA, command=self.save_ifood).pack(side="left", padx=6)
        ctk.CTkButton(form, text="Atualizar pedidos", fg_color=COR_SECUNDARIA, command=self.load_ifood).pack(side="left", padx=6)
        self.tree_ifood = self.build_tree(self.main, [("order_id","Order ID",180),("status","Status",120),("cliente","Cliente",180),("total","Valor pago",120),("entregador","Valor entregador",140),("saida","Saiu entrega",160),("entregue","Entregue",160)])
        self.load_ifood()

    def save_ifood(self):
        r = self.safe_request("POST", "/empresa/ifood/config", json={"merchant_id": self.if_merchant.get().strip(), "token": self.if_token.get().strip(), "webhook_secret": None})
        if r and r.status_code == 200: messagebox.showinfo("iFood", "Configuração salva.")
        elif r: messagebox.showerror("iFood", r.text)

    def load_ifood(self):
        r = self.safe_request("GET", "/empresa/ifood/pedidos")
        if not r or r.status_code != 200: return
        for i in self.tree_ifood.get_children(): self.tree_ifood.delete(i)
        for p in r.json():
            self.tree_ifood.insert("", "end", values=(p["order_id"], p["status"], p["cliente_nome"], f'R$ {p["total_pago"]:.2f}', f'R$ {p["valor_entregador"]:.2f}', p["saiu_entrega_em"], p["entregue_em"]))

if __name__ == "__main__":
    app = GerenceDesktop(); app.mainloop()
