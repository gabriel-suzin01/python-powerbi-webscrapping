"""Módulo principal. Ele que é o responsável pela execução do programa."""

from pathlib import Path
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import SUCCESS
from dotenv import set_key

from src.common import Config, Logger
from src.info import WebExtractor
from src.sharepoint import UpdateSharepointFile

def insert_env_variables() -> None:
    """
        Função para inserir as variáveis de ambiente.
        Rodam uma vez só (para não parar com automações).
    """

    env_path = Path(".env")

    if not env_path.exists():
        env_path.touch()
    elif Config.get("INIT", "UPDATE_VALUES").lower() == "false":
        return

    app = ttk.Window(title="Informações essenciais", themename="darkly")

    window_width = 500
    window_height = 400
    x = (app.winfo_screenwidth() // 2) - (window_width // 2)
    y = (app.winfo_screenheight() // 2) - (window_height // 2)
    app.geometry(f"{window_width}x{window_height}+{x}+{y}")

    tenant_var = ttk.StringVar()
    client_var = ttk.StringVar()
    email_var = ttk.StringVar()
    password_var = ttk.StringVar()

    ttk.Label(app, text="Tenant ID (Azure)").pack(pady=5)
    ttk.Entry(app, textvariable=tenant_var, width=40).pack()

    ttk.Label(app, text="Client ID (Azure)").pack(pady=5)
    ttk.Entry(app, textvariable=client_var, width=40).pack()

    ttk.Label(app, text="E-mail").pack(pady=5)
    ttk.Entry(app, textvariable=email_var, width=40).pack()

    ttk.Label(app, text="Senha do e-mail").pack(pady=5)
    ttk.Entry(app, textvariable=password_var, width=40, show="*").pack()

    def aparecer_mensagem() -> None:
        messagebox.showwarning(title="Aviso!", message="Preencha todos os campos!")

    def enviar() -> None:
        if any(not var.get().strip() for var in (tenant_var, client_var, email_var, password_var)):
            aparecer_mensagem()
            Logger("[ENV] Erro, valores inseridos são inválidos!")
            return

        set_key(env_path, "TENANT_ID", tenant_var.get())
        set_key(env_path, "CLIENT_ID", client_var.get())
        set_key(env_path, "EMAIL", email_var.get())
        set_key(env_path, "PASSWORD", password_var.get())
        print("Dados salvos no .env")

        Config.set("INIT", "UPDATE_VALUES", "false")
        app.destroy()

    ttk.Button(app, text="Enviar", bootstyle=SUCCESS, command=enviar).pack(pady=20)

    app.protocol("WM_DELETE_WINDOW", aparecer_mensagem)
    app.mainloop()

def main() -> None:
    """Função principal."""

    insert_env_variables()

    infos = WebExtractor()
    json_data = infos.get_info()

    sharepoint = UpdateSharepointFile()
    sharepoint.put_in_sharepoint(json_data)

if __name__ == "__main__":
    main()
