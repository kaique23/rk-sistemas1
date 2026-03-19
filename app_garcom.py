
import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
import requests

API_DEFAULT = "http://127.0.0.1:8000"

class GarcomApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RK Sistemas - App do Garçom")
        self.geometry("1100x760")
        self.api = API_DEFAULT
        self.token = None
        self.header = ctk.CTkLabel(self, text="App do Garçom", font=("Segoe UI", 24, "bold"))
        self.header.pack(pady=10)
        self.body = ctk.CTkFrame(self)
        self.body.pack(fill="both", expand=True, padx=12, pady=12)
        self.show_login()

    def clear(self):
        for w in self.body.winfo_children(): w.destroy()
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    def req(self, method, endpoint, json=None):
        try:
            if method == "GET":
                return requests.get(f"{self.api}{endpoint}", headers=self.headers(), timeout=20)
            return requests.post(f"{self.api}{endpoint}", headers=self.headers(), json=json, timeout=20)
        except requests.exceptions.RequestException:
            messagebox.showerror("Conexão", "Não foi possível conectar ao servidor.")
            return None

    def show_login(self):
        self.clear()
        self.e_api = ctk.CTkEntry(self.body, width=420, placeholder_text="API"); self.e_api.insert(0, API_DEFAULT); self.e_api.pack(pady=8)
        self.e_email = ctk.CTkEntry(self.body, width=420, placeholder_text="Email"); self.e_email.pack(pady=8)
        self.e_senha = ctk.CTkEntry(self.body, width=420, placeholder_text="Senha", show="*"); self.e_senha.pack(pady=8)
        ctk.CTkButton(self.body, text="Entrar", command=self.login).pack(pady=14)

    def login(self):
        self.api = self.e_api.get().strip()
        r = self.req("POST", "/auth/empresa/login", {"email": self.e_email.get().strip(), "senha": self.e_senha.get().strip()})
        if not r: return
        if r.status_code != 200:
            messagebox.showerror("Login", r.text); return
        self.token = r.json()["access_token"]
        self.show_main()

    def show_main(self):
        self.clear()
        top = ctk.CTkFrame(self.body); top.pack(fill="x", pady=8)
        ctk.CTkButton(top, text="Atualizar mesas", command=self.load_tables).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Atualizar produtos", command=self.load_products).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Abrir comanda", command=self.open_comanda).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Lançar pedido", command=self.launch_order).pack(side="left", padx=6)

        self.tree_mesas = ttk.Treeview(self.body, columns=("id","numero","status","cliente","total"), show="headings", height=12)
        for cid, title, width in [("id","ID",60),("numero","Mesa",100),("status","Status",120),("cliente","Cliente",200),("total","Total",120)]:
            self.tree_mesas.heading(cid, text=title); self.tree_mesas.column(cid, width=width, anchor="center")
        self.tree_mesas.pack(fill="x", pady=10)

        self.tree_prod = ttk.Treeview(self.body, columns=("id","nome","preco","estoque"), show="headings", height=12)
        for cid, title, width in [("id","ID",60),("nome","Produto",240),("preco","Preço",120),("estoque","Estoque",100)]:
            self.tree_prod.heading(cid, text=title); self.tree_prod.column(cid, width=width, anchor="center")
        self.tree_prod.pack(fill="both", expand=True, pady=10)

        self.load_tables(); self.load_products()

    def load_tables(self):
        r = self.req("GET", "/empresa/mesas")
        if not r or r.status_code != 200: return
        for i in self.tree_mesas.get_children(): self.tree_mesas.delete(i)
        for m in r.json():
            self.tree_mesas.insert("", "end", values=(m["id"], m["numero"], m["status"], m["cliente_nome"], f'R$ {m["total"]:.2f}'))

    def load_products(self):
        r = self.req("GET", "/empresa/produtos")
        if not r or r.status_code != 200: return
        for i in self.tree_prod.get_children(): self.tree_prod.delete(i)
        for p in r.json():
            self.tree_prod.insert("", "end", values=(p["id"], p["nome"], f'R$ {p["preco"]:.2f}', p["estoque"]))

    def open_comanda(self):
        mesa_id = simpledialog.askinteger("Comanda", "ID da mesa (opcional):", parent=self)
        cliente = simpledialog.askstring("Comanda", "Cliente (opcional):", parent=self)
        garcom = simpledialog.askstring("Comanda", "Garçom:", initialvalue="Garçom", parent=self)
        r = self.req("POST", f"/empresa/comandas?mesa_id={mesa_id or ''}&cliente_nome={cliente or ''}&garcom_nome={garcom or ''}")
        if r and r.status_code == 200:
            messagebox.showinfo("Comanda", "Comanda aberta.")

    def launch_order(self):
        mesa_sel = self.tree_mesas.selection(); prod_sel = self.tree_prod.selection()
        if not mesa_sel or not prod_sel:
            messagebox.showwarning("Garçom", "Selecione mesa e produto."); return
        mesa_id = int(self.tree_mesas.item(mesa_sel[0], "values")[0])
        produto_id = int(self.tree_prod.item(prod_sel[0], "values")[0])
        qtd = simpledialog.askfloat("Quantidade", "Quantidade:", parent=self)
        cliente = simpledialog.askstring("Cliente", "Nome do cliente (opcional):", parent=self)
        if not qtd: return
        r = self.req("POST", "/empresa/pedidos", {"mesa_id": mesa_id, "comanda_id": None, "origem": "GARCOM", "setor": "COZINHA", "cliente_nome": cliente, "observacoes": None, "tempo_estimado_min": 20, "itens": [{"produto_id": produto_id, "quantidade": qtd, "observacoes": None}]})
        if r and r.status_code == 200:
            messagebox.showinfo("Garçom", "Pedido enviado para a cozinha.")
            self.load_tables(); self.load_products()
        elif r:
            messagebox.showerror("Garçom", r.text)

if __name__ == "__main__":
    app = GarcomApp(); app.mainloop()
