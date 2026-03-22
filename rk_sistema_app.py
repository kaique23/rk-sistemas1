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

COR_FUNDO = "#07111f"
COR_CARD = "#0f1b2d"
COR_BORDA = "#1f3a5f"
COR_TEXTO = "#eaf4ff"
COR_SUBTEXTO = "#9fb6d1"

COR_PRIMARIA = "#0A84FF"
COR_SUCESSO = "#00C853"
COR_PERIGO = "#ef4444"


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

        self.logo = None
        self.logo_bg = None
        self.load_logo()

        self.login_screen()

    def load_logo(self):
        if os.path.exists("logo.png"):
            img = Image.open("logo.png")
            self.logo = CTkImage(light_image=img, dark_image=img, size=(120, 60))
            self.logo_bg = CTkImage(light_image=img, dark_image=img, size=(600, 300))

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def request(self, rota, data):
        return requests.post(f"{self.api}{rota}", json=data)

    # ================= LOGIN =================
    def login_screen(self):
        self.clear()

        base = CTkFrame(self, fg_color=COR_FUNDO)
        base.pack(fill="both", expand=True)

        # 🔥 MARCA D'ÁGUA
        if self.logo_bg:
            CTkLabel(base, image=self.logo_bg, text="").place(relx=0.5, rely=0.5, anchor="center")

        box = CTkFrame(base, fg_color=COR_CARD, corner_radius=15)
        box.pack(expand=True)

        if self.logo:
            CTkLabel(box, image=self.logo, text="").pack(pady=10)

        CTkLabel(box, text="GSI Sistemas", font=("Arial", 28, "bold")).pack(pady=5)

        CTkRadioButton(box, text="Empresa", variable=self.tipo_login, value="empresa").pack()
        CTkRadioButton(box, text="Admin", variable=self.tipo_login, value="admin").pack()
        CTkRadioButton(box, text="Colaborador", variable=self.tipo_login, value="colaborador").pack()

        self.email = CTkEntry(box, width=300, placeholder_text="Email")
        self.email.pack(pady=5)

        self.senha = CTkEntry(box, width=300, show="*", placeholder_text="Senha")
        self.senha.pack(pady=5)

        CTkButton(box, text="Entrar", fg_color=COR_PRIMARIA, command=self.login).pack(pady=10)

    def login(self):
        rota = {
            "empresa": "/empresa/login",
            "admin": "/admin/login",
            "colaborador": "/colaborador/login"
        }[self.tipo_login.get()]

        r = self.request(rota, {
            "email": self.email.get(),
            "senha": self.senha.get()
        })

        if r.status_code != 200:
            messagebox.showerror("Erro", r.text)
            return

        data = r.json()
        self.token = data["token"]
        self.usuario_tipo = self.tipo_login.get()
        self.usuario_nome = data.get("nome", "Usuário")
        self.usuario_cargo = data.get("cargo", "")

        if self.usuario_tipo == "admin":
            self.admin_screen()
        elif self.usuario_tipo == "empresa":
            self.dashboard()
        else:
            self.colaborador()

    # ================= LAYOUT =================
    def layout(self, titulo):
        self.clear()

        top = CTkFrame(self, fg_color=COR_CARD, height=70)
        top.pack(fill="x")

        if self.logo:
            CTkLabel(top, image=self.logo, text="").pack(side="left", padx=10)

        CTkLabel(top, text=titulo, font=("Arial", 20, "bold")).pack(side="left")

        CTkLabel(top, text=f"{self.usuario_nome} | {self.usuario_cargo}").pack(side="right", padx=10)

        CTkButton(top, text="Sair", fg_color=COR_PERIGO, command=self.login_screen).pack(side="right", padx=10)

        self.content = CTkFrame(self)
        self.content.pack(fill="both", expand=True)

    # ================= ADMIN =================
    def admin_screen(self):
        self.layout("Admin")

        CTkButton(self.content, text="Gerenciar Empresas", fg_color=COR_PRIMARIA).pack(pady=20)

    # ================= EMPRESA =================
    def dashboard(self):
        self.layout("Dashboard Empresa")

        CTkLabel(self.content, text="Bem-vindo ao sistema", font=("Arial", 22)).pack(pady=20)

        CTkButton(self.content, text="Colaboradores", fg_color=COR_SUCESSO, command=self.colaboradores).pack(pady=10)

    def colaboradores(self):
        self.layout("Colaboradores")

        CTkLabel(self.content, text="Gestão de colaboradores", font=("Arial", 22)).pack(pady=20)

    # ================= COLABORADOR =================
    def colaborador(self):
        self.layout("Painel do Colaborador")

        CTkLabel(self.content, text="Bem-vindo colaborador", font=("Arial", 22)).pack(pady=20)


if __name__ == "__main__":
    app = App()
    app.mainloop()