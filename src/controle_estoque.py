# app.py (REFATORADO: Sidebar + Header, tema claro)
import customtkinter as ctk
import sqlite3
from tkinter import messagebox, filedialog
import os
import shutil
import subprocess
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import datetime
import db
import tkinter.messagebox as messagebox
import tkinter as tk  
from db import delete_item
import tkinter.messagebox as mbox

import logging
from logging.handlers import RotatingFileHandler as _RotatingFileHandler

_log_handler = _RotatingFileHandler(
    "app_log.txt", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
)
_log_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(message)s", datefmt="%d/%m/%Y %H:%M:%S")
)
_app_logger = logging.getLogger("controle_estoque")
_app_logger.addHandler(_log_handler)
_app_logger.setLevel(logging.INFO)


def log_event(evento: str):
    """Registra eventos com rotação automática (máx 1 MB, 3 backups)."""
    _app_logger.info(evento)


# ---------- APARÊNCIA ----------
ctk.set_appearance_mode("light")  # tema claro
ctk.set_default_color_theme("blue")

# --- CONSTANTES GLOBAIS ---
ATTACHMENTS_FOLDER_NOTEBOOKS = "anexos_notebooks"

_OBRAS_FALLBACK = [
    "Domma", "Seleto Primavera", "Unic São Gonçalo", "PRIME Caxias",
    "LIV Primavera", "Reserva Equitativa", "Encantado", "Seleto Inhaúma",
]

def _load_obras_from_db():
    try:
        nomes = db.get_obras()
        return nomes if nomes else _OBRAS_FALLBACK
    except Exception:
        return _OBRAS_FALLBACK

LISTA_OBRAS = _load_obras_from_db()
STATUS_COLORS = {
    "Disponível":          "#22C55E",
    "Alocado":             "#EF4444",
    "Triagem":             "#3B82F6",
    "Verificar":           "#F59E0B",
    "Assistência Técnica": "#EAB308",
    "Não definido":        "#94A3B8",
}
TEXT_COLORS = {
    "Disponível":          "#FFFFFF",
    "Alocado":             "#FFFFFF",
    "Triagem":             "#FFFFFF",
    "Verificar":           "#FFFFFF",
    "Assistência Técnica": "#FFFFFF",
    "Não definido":        "#FFFFFF",
}
SITUACOES_NOTEBOOK = ["Disponível", "Alocado", "Triagem", "Assistência Técnica", "Verificar"]

# --- Design System ---
THEME = {
    "primary":             "#2563EB",
    "primary_hover":       "#1D4ED8",
    "sidebar_bg":          "#0F172A",
    "sidebar_item_hover":  "#1E293B",
    "sidebar_active_bg":   "#2563EB",
    "sidebar_text":        "#94A3B8",
    "sidebar_active_text": "#FFFFFF",
    "sidebar_sep":         "#1E293B",
    "header_bg":           "#FFFFFF",
    "content_bg":          "#F1F5F9",
    "card_bg":             "#FFFFFF",
    "border":              "#E2E8F0",
    "text":                "#0F172A",
    "text_secondary":      "#64748B",
    "success":             "#16A34A",
    "danger":              "#DC2626",
    "warning":             "#D97706",
    "danger_hover":        "#B91C1C",
    "accent_blue":         "#3B82F6",
    "accent_purple":       "#8B5CF6",
    "accent_green":        "#10B981",
    "accent_red":          "#EF4444",
}

# --- BANCO DE DADOS LEGADO PARA NOTEBOOKS (INTACTO) ---
DB_NAME_NOTEBOOKS = "database_notebooks.db"
def db_connect_notebooks():
    conn = sqlite3.connect(DB_NAME_NOTEBOOKS)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def db_setup_notebooks():
    conn, cursor = db_connect_notebooks()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notebooks (
            placa_id TEXT PRIMARY KEY, numero_serie TEXT, usuario_anterior TEXT, 
            usuario_atual TEXT, senha TEXT, setor TEXT, cargo TEXT, nota_fiscal TEXT, 
            perifericos TEXT, observacao TEXT, situacao TEXT DEFAULT 'Não definido', fotos TEXT DEFAULT 'Não'
        )
    """)
    conn.commit()
    conn.close()

# ------------------------------
# CLASSE: AtivoDetailWindow (INTACTA)
# ------------------------------
class AtivoDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, placa_id, on_close_callback):
        super().__init__(master)
        self.on_close_callback = on_close_callback
        self.placa_id_initial = placa_id
        self.title(f"Detalhes: {placa_id if placa_id else 'Novo Notebook'}")
        self.geometry("700x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grab_set()

        # Scroll principal
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(1, weight=1)
        self.widgets = {}

        # Campos principais
        campos = {
            "placa_id": "ID (Placa de Identificação):",
            "numero_serie": "Número de Série:",
            "usuario_anterior": "Usuário Anterior:",
            "usuario_atual": "Usuário Atual:",
            "senha": "Senha:",
            "setor": "Setor:",
            "cargo": "Cargo:",
            "nota_fiscal": "Nota Fiscal:",
        }
        for i, (key, text) in enumerate(campos.items()):
            ctk.CTkLabel(self.scroll_frame, text=text).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self.scroll_frame)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            self.widgets[key] = entry

        # Observação
        ctk.CTkLabel(self.scroll_frame, text="Observação:").grid(row=9, column=0, padx=10, pady=5, sticky="nw")
        self.widgets['observacao'] = ctk.CTkTextbox(self.scroll_frame, height=100)
        self.widgets['observacao'].grid(row=9, column=1, padx=10, pady=5, sticky="ew")

        # Situação
        ctk.CTkLabel(self.scroll_frame, text="Situação:").grid(row=10, column=0, padx=10, pady=5, sticky="w")
        self.widgets['situacao'] = ctk.StringVar(value="Disponível")
        self.situacao_menu = ctk.CTkOptionMenu(
            self.scroll_frame,
            variable=self.widgets['situacao'],
            values=["Disponível", "Alocado", "Triagem", "Verificar", "Assistência Técnica"],
            command=self.update_situacao_color
        )
        self.situacao_menu.grid(row=10, column=1, padx=10, pady=5, sticky="ew")

        # --- Campo Obra ---
        ctk.CTkLabel(self.scroll_frame, text="Obra:").grid(row=11, column=0, padx=10, pady=5, sticky="w")
        self.widgets['obra'] = ctk.StringVar(value="")
        ctk.CTkOptionMenu(self.scroll_frame, variable=self.widgets['obra'], values=LISTA_OBRAS)\
            .grid(row=11, column=1, padx=10, pady=5, sticky="ew")

        # --- Campo Periféricos ---
        ctk.CTkLabel(self.scroll_frame, text="Periféricos:").grid(row=12, column=0, padx=10, pady=(10, 5), sticky="nw")
        perifericos_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", corner_radius=0)
        perifericos_frame.grid(row=12, column=1, padx=10, pady=5, sticky="ew")

        self.widgets['perifericos'] = {}
        opcoes_perifericos = ["Mouse", "Teclado", "Monitor", "Mousepad", "Fone de ouvido"]
        for i, opcao in enumerate(opcoes_perifericos):
            var = tk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(perifericos_frame, text=opcao, variable=var)
            chk.grid(row=i // 2, column=i % 2, padx=5, pady=2, sticky="w")
            self.widgets['perifericos'][opcao] = var

        # --- Campo Autocad (Sim/Não) ---
        ctk.CTkLabel(self.scroll_frame, text="Autocad:").grid(row=13, column=0, padx=10, pady=5, sticky="w")
        self.widgets['autocad'] = ctk.StringVar(value="Não")
        autocad_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        autocad_frame.grid(row=13, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkRadioButton(
            autocad_frame, text="Sim", variable=self.widgets['autocad'], value="Sim",
            fg_color="green", hover_color="#00cc00"
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            autocad_frame, text="Não", variable=self.widgets['autocad'], value="Não",
            fg_color="red", hover_color="#cc0000"
        ).pack(side="left", padx=5)

        # --- Campo Fotos (Sim/Não) ---
        ctk.CTkLabel(self.scroll_frame, text="Fotos:").grid(row=14, column=0, padx=10, pady=5, sticky="w")
        self.widgets['fotos'] = ctk.StringVar(value="Não")
        fotos_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        fotos_frame.grid(row=14, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkRadioButton(
            fotos_frame, text="Sim", variable=self.widgets['fotos'], value="Sim",
            fg_color="green", hover_color="#00cc00"
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            fotos_frame, text="Não", variable=self.widgets['fotos'], value="Não",
            fg_color="red", hover_color="#cc0000"
        ).pack(side="left", padx=5)

        # Botão de Anexo
        ctk.CTkButton(self.scroll_frame, text="Anexo", command=self.attach_file)\
            .grid(row=15, column=1, padx=10, pady=10, sticky="w")

        # Botão de Salvar
        ctk.CTkButton(self, text="Salvar", command=self.save_event)\
            .pack(side="bottom", padx=10, pady=10, anchor="e")

        # Carrega dados iniciais
        self.load_data()
        self.update_situacao_color()
        self.update_fotos_color()

    def on_closing(self):
        self.on_close_callback(); self.destroy()

    def update_situacao_color(self, choice=None):
        color = STATUS_COLORS.get(self.widgets['situacao'].get())
        if color:
            try:
                self.situacao_menu.configure(button_color=color, button_hover_color=color)
            except Exception:
                pass

    def update_fotos_color(self):
        if self.widgets['fotos'].get() == "Sim":
            try:
                self.radio_fotos_sim.configure(fg_color="green")
                self.radio_fotos_nao.configure(fg_color=self.radio_fotos_nao.cget("hover_color"))
            except Exception:
                pass
        else:
            try:
                self.radio_fotos_nao.configure(fg_color="red")
                self.radio_fotos_sim.configure(fg_color=self.radio_fotos_sim.cget("hover_color"))
            except Exception:
                pass

    def load_data(self):
        """Carrega os dados do notebook e preenche os widgets da janela de detalhes."""
        if not self.placa_id_initial:
            self.widgets['placa_id'].focus()
            return

        # Preenche o campo de placa_id e mantém EDITÁVEL
        self.widgets['placa_id'].insert(0, self.placa_id_initial)
        try:
            self.widgets['placa_id'].configure(state="normal")  # garante edição
        except Exception:
            pass

        conn, cursor = db_connect_notebooks()
        cursor.execute("SELECT * FROM notebooks WHERE placa_id = ?", (self.placa_id_initial,))
        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        for key, widget in self.widgets.items():
            if key not in data.keys():
                continue

            value = data[key] if data[key] is not None else ""

            # Campos normais
            if isinstance(widget, ctk.CTkEntry):
                widget.insert(0, value)
            elif isinstance(widget, ctk.CTkTextbox):
                widget.insert("1.0", value)
            elif isinstance(widget, ctk.StringVar):
                widget.set(value)

        # ---- Campos especiais ----

        # Obra (StringVar)
        if "obra" in data.keys() and data["obra"]:
            self.widgets['obra'].set(data["obra"])

        # Periféricos (CSV/JSON tolerante a formatos legados)
        if "perifericos" in data.keys() and data["perifericos"] is not None:
            try:
                import json, unicodedata

                def _norm(s: str) -> str:
                    s = (s or "").strip().lower()
                    s = unicodedata.normalize("NFKD", s)
                    s = "".join(c for c in s if not unicodedata.combining(c))
                    return s

                raw = str(data["perifericos"] or "")

                # aceita JSON ["Mouse","Teclado"] ou CSV com separadores legados
                if raw.startswith("["):
                    try:
                        selecionados = json.loads(raw)
                    except Exception:
                        selecionados = []
                else:
                    for sep in [";", "|", "/", "\\"]:
                        raw = raw.replace(sep, ",")
                    selecionados = [p.strip() for p in raw.split(",") if p.strip()]

                sel_norm = {_norm(p) for p in selecionados}

                # Marca checkboxes por nome normalizado (tolerante a acento/caixa)
                if isinstance(self.widgets.get('perifericos'), dict):
                    for nome, var in self.widgets['perifericos'].items():
                        var.set(_norm(nome) in sel_norm)

            except Exception as e:
                print(f"[WARN] Erro ao carregar periféricos: {e}")



        # Autocad
        if "autocad" in data.keys():
            self.widgets['autocad'].set(data['autocad'])
        
        # Fotos
        if "fotos" in data.keys():
            self.widgets['fotos'].set(data['fotos'])

        # Atualiza cores dos botões após carregar
        self.update_situacao_color()
        self.update_fotos_color()


    def save_event(self):
        import sqlite3

        # 1) Coleta robusta dos valores dos widgets
        data = {}
        for key, w in self.widgets.items():
            # Textbox multilinha
            if isinstance(w, ctk.CTkTextbox):
                data[key] = w.get("1.0", "end-1c")
            # Grupo de checkboxes (periféricos)
            elif isinstance(w, dict):
                selecionados = [nome for nome, var in w.items() if var.get()]
                data[key] = ",".join(selecionados)  # CSV com vírgula
            # StringVar / OptionMenu
            elif hasattr(w, "get") and not hasattr(w, "insert"):
                data[key] = w.get()
            else:
                # CTkEntry e similares
                try:
                    data[key] = w.get()
                except Exception:
                    data[key] = ""

        # 2) Validação
        new_placa = (data.get("placa_id") or "").strip()
        if not new_placa:
            messagebox.showerror("Erro", "O ID (Placa de Identificação) é obrigatório.")
            return

        # 3) Abre conexão e garante que as colunas existem
        conn, cursor = db_connect_notebooks()
        try:
            cursor.execute("PRAGMA table_info(notebooks)")
            cols = {row[1] for row in cursor.fetchall()}
            for col_name, ddl in [
                ("obra",      "ALTER TABLE notebooks ADD COLUMN obra TEXT"),
                ("autocad",   "ALTER TABLE notebooks ADD COLUMN autocad TEXT DEFAULT 'Não'"),
                ("fotos",     "ALTER TABLE notebooks ADD COLUMN fotos TEXT DEFAULT 'Não'"),
                ("perifericos","ALTER TABLE notebooks ADD COLUMN perifericos TEXT")
            ]:
                if col_name not in cols:
                    try:
                        cursor.execute(ddl)
                    except Exception:
                        pass

            is_edit = bool(self.placa_id_initial)
            old_placa = self.placa_id_initial if is_edit else None

            if is_edit:
                if new_placa != old_placa:
                    # evita colisão
                    cursor.execute("SELECT 1 FROM notebooks WHERE placa_id = ?", (new_placa,))
                    if cursor.fetchone():
                        messagebox.showerror("Erro", f"Já existe um notebook com ID '{new_placa}'.")
                        conn.close()
                        return

                    # UPDATE trocando a PK
                    cursor.execute("""
                        UPDATE notebooks
                        SET placa_id=?,
                            numero_serie=?,
                            usuario_anterior=?,
                            usuario_atual=?,
                            senha=?,
                            setor=?,
                            cargo=?,
                            nota_fiscal=?,
                            perifericos=?,
                            observacao=?,
                            situacao=?,
                            fotos=?,
                            obra=?,
                            autocad=?
                        WHERE placa_id=?
                    """, (
                        new_placa,
                        data.get("numero_serie", ""),
                        data.get("usuario_anterior", ""),
                        data.get("usuario_atual", ""),
                        data.get("senha", ""),
                        data.get("setor", ""),
                        data.get("cargo", ""),
                        data.get("nota_fiscal", ""),
                        data.get("perifericos", ""),
                        data.get("observacao", ""),
                        data.get("situacao", ""),
                        data.get("fotos", "Não"),
                        data.get("obra", ""),
                        data.get("autocad", "Não"),
                        old_placa,
                    ))

                    # Renomeia/move pasta de anexos, se existir
                    try:
                        # type: ignore
                        old_path = os.path.join(ATTACHMENTS_FOLDER_NOTEBOOKS, old_placa)  # type: ignore
                        new_path = os.path.join(ATTACHMENTS_FOLDER_NOTEBOOKS, new_placa)  # type: ignore
                        if os.path.isdir(old_path):
                            os.makedirs(ATTACHMENTS_FOLDER_NOTEBOOKS, exist_ok=True)
                            if not os.path.exists(new_path):
                                os.rename(old_path, new_path)
                            else:
                                # pasta nova já existe -> move conteúdo e remove pasta antiga
                                for fname in os.listdir(old_path):
                                    shutil.move(os.path.join(old_path, fname), new_path)
                                shutil.rmtree(old_path, ignore_errors=True)
                    except Exception as e:
                        print("Aviso ao mover anexos:", e)

                else:
                    # edição sem troca de ID
                    cursor.execute("""
                        UPDATE notebooks
                        SET numero_serie=?,
                            usuario_anterior=?,
                            usuario_atual=?,
                            senha=?,
                            setor=?,
                            cargo=?,
                            nota_fiscal=?,
                            perifericos=?,
                            observacao=?,
                            situacao=?,
                            fotos=?,
                            obra=?,
                            autocad=?
                        WHERE placa_id=?
                    """, (
                        data.get("numero_serie", ""),
                        data.get("usuario_anterior", ""),
                        data.get("usuario_atual", ""),
                        data.get("senha", ""),
                        data.get("setor", ""),
                        data.get("cargo", ""),
                        data.get("nota_fiscal", ""),
                        data.get("perifericos", ""),
                        data.get("observacao", ""),
                        data.get("situacao", ""),
                        data.get("fotos", "Não"),
                        data.get("obra", ""),
                        data.get("autocad", "Não"),
                        new_placa,
                    ))

            else:
                # INSERT (novo registro)
                cursor.execute("""
                    INSERT INTO notebooks (
                        placa_id,
                        numero_serie,
                        usuario_anterior,
                        usuario_atual,
                        senha,
                        setor,
                        cargo,
                        nota_fiscal,
                        perifericos,
                        observacao,
                        situacao,
                        fotos,
                        obra,
                        autocad
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    new_placa,
                    data.get("numero_serie", ""),
                    data.get("usuario_anterior", ""),
                    data.get("usuario_atual", ""),
                    data.get("senha", ""),
                    data.get("setor", ""),
                    data.get("cargo", ""),
                    data.get("nota_fiscal", ""),
                    data.get("perifericos", ""),
                    data.get("observacao", ""),
                    data.get("situacao", ""),
                    data.get("fotos", "Não"),
                    data.get("obra", ""),
                    data.get("autocad", "Não"),
                ))

            conn.commit()

            # log opcional
            try:
                if 'log_event' in globals():
                    if is_edit:
                        msg = f"Notebook '{old_placa}' atualizado para '{new_placa}'."
                    else:
                        msg = f"Notebook '{new_placa}' criado."
                    log_event(msg)
            except:
                pass

            messagebox.showinfo("Sucesso", "Dados do notebook salvos com sucesso!")
            self.on_closing()

        except Exception as e:
            messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro: {e}")
        finally:
            conn.close()



    def attach_file(self):
        from tkinter import filedialog
        import os, shutil

        placa = ""
        # placa_id é CTkEntry; se for StringVar, também funciona
        w_placa = self.widgets.get("placa_id")
        if hasattr(w_placa, "get"):
            placa = w_placa.get().strip()

        if not placa:
            messagebox.showwarning("Aviso", "Preencha o ID do notebook antes de anexar.")
            return

        src = filedialog.askopenfilename(title="Selecione um arquivo para anexar")
        if not src:
            return

        # pasta base para notebooks: anexos_notebooks/<placa_id>
        base = os.path.join(ATTACHMENTS_FOLDER_NOTEBOOKS, placa)
        os.makedirs(base, exist_ok=True)

        dst = os.path.join(base, os.path.basename(src))
        try:
            shutil.copy(src, dst)
            messagebox.showinfo("Sucesso", f"Arquivo anexado em:\n{dst}")
            if os.name == "nt":
                os.startfile(base)  # abre a pasta no Explorer
        except Exception as e:
            messagebox.showerror("Erro ao anexar", f"Ocorreu um erro: {e}")


# ================================
# [NOVO] Filtros para Notebooks
# ================================
class NotebookFilterWindow(ctk.CTkToplevel):
    """Janela simples para escolher filtros e aplicar na listagem de notebooks"""
    def __init__(self, master, current_filter, on_apply):
        super().__init__(master)
        self.title("Filtros — Notebooks (TEST v3)")   # <<< título para confirmar
        self.geometry("360x280")
        self.grab_set()
        self.on_apply = on_apply

        # --- Situação ---
        situacoes = ["Todos", "Disponível", "Alocado", "Triagem", "Assistência Técnica", "Verificar"]

        # DEBUG visual: mostra a lista recebida
        ctk.CTkLabel(self, text="(debug) opções: " + ", ".join(situacoes), wraplength=320, text_color="#888")\
            .pack(padx=20, pady=(10, 6), anchor="w")

        ctk.CTkLabel(self, text="Situação do Notebook:")\
            .pack(padx=20, pady=(8, 6), anchor="w")

        self.situacao_var = ctk.StringVar(value=current_filter.get("situacao", "Todos"))
        self.situacao_menu = ctk.CTkOptionMenu(self, variable=self.situacao_var, values=situacoes)
        self.situacao_menu.pack(padx=20, fill="x")

        # força atualização (algumas versões do CTk precisam)
        self.after(0, lambda: self.situacao_menu.configure(values=situacoes))

        # --- Obra ---
        ctk.CTkLabel(self, text="Obra:").pack(padx=20, pady=(14, 6), anchor="w")
        obras = ["Todos"] + LISTA_OBRAS
        self.obra_var = ctk.StringVar(value=current_filter.get("obra", "Todos"))
        ctk.CTkOptionMenu(self, variable=self.obra_var, values=obras).pack(padx=20, fill="x")

        # --- Ações ---
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=20, pady=18)
        ctk.CTkButton(btns, text="Cancelar", fg_color="gray",
                      command=self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(btns, text="Salvar",
                      command=self._save).pack(side="left", expand=True, fill="x", padx=(8, 0))

    def _save(self):
        if callable(self.on_apply):
            self.on_apply({
                "situacao": self.situacao_var.get(),
                "obra": self.obra_var.get(),
            })
        self.destroy()


# ------------------------------
# JANELAS E UTILITÁRIOS PARA ESTOQUE (mantidas)
# ------------------------------

# ADICIONE estas novas classes no seu app.py

# SUBSTITUA a sua classe ItemEditWindow por esta versão corrigida

class ItemEditWindow(ctk.CTkToplevel):
    # >>> INÍCIO (ItemEditWindow.__init__ - readicionar campo "Nome do Item")
    def __init__(self, master, obra_id, on_save_callback, item=None):
        super().__init__(master)
        self.obra_id = obra_id
        self.item_data = item
        self.item_id = (item or {}).get("id")
        self.on_save_callback = on_save_callback

        self.title("Editar Item de Estoque" if item else "Adicionar Novo Item")
        self.geometry("520x650")  # Aumentada altura para acomodar o campo extra
        self.grab_set()

        self.widgets = {}

        # --- layout base ---
        # layout base da janela
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sf = ctk.CTkScrollableFrame(self)
        sf.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # >>> colunas do grid do SF (rótulo | entrada 1 | entrada 2)
        sf.grid_columnconfigure(0, weight=0, minsize=150)  # rótulos
        sf.grid_columnconfigure(1, weight=1)               # entrada
        sf.grid_columnconfigure(2, weight=1)               # entrada (expande até a borda)


        # --- campos ---
        categorias = db.get_categorias()
        self.categoria_map = {c['nome']: c['id'] for c in (categorias or [])}
        valores_cat = list(self.categoria_map.keys()) or ["Sem Categoria"]

      # Nome do Produto
        ctk.CTkLabel(sf, text="Nome do Produto:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.widgets['nome'] = ctk.CTkEntry(sf)
        self.widgets['nome'].grid(row=0, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Item (categoria)
        ctk.CTkLabel(sf, text="Item:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.widgets['categoria_id'] = ctk.StringVar(value=valores_cat[0])
        ctk.CTkOptionMenu(sf, variable=self.widgets['categoria_id'], values=valores_cat)\
            .grid(row=1, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Nº de Série
        ctk.CTkLabel(sf, text="Nº de Série (Opcional):").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.widgets['numero_serie'] = ctk.CTkEntry(sf)
        self.widgets['numero_serie'].grid(row=2, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Quantidade em Uso
        ctk.CTkLabel(sf, text="Quantidade em Uso:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.widgets['qtd_uso'] = ctk.CTkEntry(sf)
        self.widgets['qtd_uso'].grid(row=3, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Quantidade em Estoque
        ctk.CTkLabel(sf, text="Quantidade em Estoque:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.widgets['qtd_estoque'] = ctk.CTkEntry(sf)
        self.widgets['qtd_estoque'].grid(row=4, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Condição
        ctk.CTkLabel(sf, text="Condição:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.widgets['condicao'] = ctk.StringVar(value="Novo")
        ctk.CTkOptionMenu(sf, variable=self.widgets['condicao'], values=["Novo","Usado","Com defeito"])\
            .grid(row=5, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Status
        ctk.CTkLabel(sf, text="Status:").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        self.widgets['status'] = ctk.StringVar(value="Disponível")
        ctk.CTkOptionMenu(sf, variable=self.widgets['status'],
                        values=["Disponível","Em Uso","Em Manutenção","Quebrado"])\
            .grid(row=6, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Danificado?
        ctk.CTkLabel(sf, text="Danificado?").grid(row=7, column=0, padx=10, pady=8, sticky="w")
        self.widgets['danificado'] = ctk.StringVar(value="Não")
        ctk.CTkOptionMenu(sf, variable=self.widgets['danificado'], values=["Não","Sim"])\
            .grid(row=7, column=1, columnspan=2, padx=10, pady=8, sticky="ew")

        # Observação (text area)
        ctk.CTkLabel(sf, text="Observação:").grid(row=8, column=0, padx=10, pady=8, sticky="nw")
        self.widgets['observacao'] = ctk.CTkTextbox(sf, height=100)
        self.widgets['observacao'].grid(row=8, column=1, columnspan=2, padx=10, pady=8, sticky="ew")


# --- botões de ação na linha 9 do SF ---
        # (garante a coluna 2 para o botão Excluir)
        sf.grid_columnconfigure(2, minsize=1)

        # Botão ANEXO
        self.btn_anexo = ctk.CTkButton(sf, text="Anexo", command=self.attach_file)
        self.btn_anexo.grid(row=9, column=1, padx=(10, 6), pady=(4, 10), sticky="w")

        # Botão EXCLUIR (ao lado do Anexo)
        self.btn_delete = ctk.CTkButton(
            sf, text="Excluir",
            fg_color="#e74c3c", hover_color="#c0392b",
            command=self._on_delete_item
        )
        self.btn_delete.grid(row=9, column=2, padx=(6, 10), pady=(4, 10), sticky="w")

        # --- botão SALVAR no rodapé da janela (fora do SF) ---
        ctk.CTkButton(self, text="Salvar", height=40, command=self.save_item)\
            .grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # pré-carrega dados (se for edição)
        if self.item_data:
            self.load_item_data()

    def load_item_data(self):
        try:
            item = self.item_data or {}
            # categoria por nome
            if item.get('categoria_id') is not None:
                for nome, cid in self.categoria_map.items():
                    if cid == item['categoria_id']:
                        self.widgets['categoria_id'].set(nome)
                        break
            self.widgets['nome'].insert(0, item.get('nome', ''))
            self.widgets['numero_serie'].insert(0, item.get('numero_serie', ''))
            self.widgets['qtd_uso'].insert(0, str(item.get('qtd_em_uso', item.get('qtd_uso', 0)) or 0))
            self.widgets['qtd_estoque'].insert(0, str(item.get('qtd_estoque', 0)))
            self.widgets['condicao'].set(item.get('condicao', 'Novo'))
            self.widgets['status'].set(item.get('status', 'Disponível'))

            # se banco tem "funcionando", converte para danificado
            funcionando = item.get('funcionando')
            if funcionando is not None:
                self.widgets['danificado'].set("Não" if str(funcionando).lower() == "sim" else "Sim")
            else:
                self.widgets['danificado'].set("Não")

            self.widgets['observacao'].insert("1.0", item.get('observacao', ''))
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar: {e}")

    def _on_delete_item(self):
        if not self.item_id:
            mbox.showwarning("Excluir", "Este item ainda não foi salvo.")
            return

        if not mbox.askyesno("Confirmar", "Tem certeza que deseja excluir este item?"):
            return

        ok, msg = delete_item(self.item_id)
        if not ok:
            mbox.showerror("Erro", msg)
            return

        mbox.showinfo("Sucesso", msg)
        try:
            if hasattr(self.master, "refresh_estoque_list"):
                self.master.refresh_estoque_list()
        except Exception:
            pass
        self.destroy()

    def save_item(self):
        try:
            categoria_nome = self.widgets['categoria_id'].get()
            categoria_id = self.categoria_map.get(categoria_nome)
            nome = self.widgets['nome'].get().strip()
            numero_serie = self.widgets['numero_serie'].get().strip()
            qtd_uso = int(self.widgets['qtd_uso'].get() or 0)
            qtd_estoque = int(self.widgets['qtd_estoque'].get() or 0)
            qtd_total = qtd_uso + qtd_estoque

            condicao = self.widgets['condicao'].get()
            status = self.widgets['status'].get()
            danificado = self.widgets['danificado'].get()  # "Sim"/"Não"
            funcionando = "Não" if danificado == "Sim" else "Sim"
            observacao = self.widgets['observacao'].get("1.0", "end-1c")

            if not nome:
                messagebox.showerror("Erro de Validação", "O nome do item é obrigatório.")
                return

            data = {
                "obra_id": self.obra_id,
                "categoria_id": categoria_id,
                "nome": nome,
                "numero_serie": numero_serie,
                "qtd_total": qtd_total,
                "qtd_uso": qtd_uso,
                "qtd_em_uso": qtd_uso,
                "qtd_estoque": qtd_estoque,
                "condicao": condicao,
                "status": status,
                "possui": (self.item_data.get("possui") if self.item_data else "Sim"),
                "funcionando": funcionando,
                "observacao": observacao,
            }

            if self.item_data and 'id' in self.item_data:
                data['id'] = self.item_data['id']
                db.update_item(data)
                messagebox.showinfo("Sucesso", "Item atualizado com sucesso!")
            else:
                db.add_item(data)
                messagebox.showinfo("Sucesso", "Novo item adicionado ao estoque!")

            self.on_save_callback()
            self.destroy()
        except ValueError:
            messagebox.showerror("Erro de Validação", "Campos de quantidade devem ser números válidos.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao salvar: {e}")

    def attach_file(self):
        """Anexa arquivo ao item. Para itens novos, peça para salvar primeiro."""
        try:
            if not (self.item_data and self.item_data.get('id')):
                messagebox.showinfo("Anexo",
                                    "Salve o item primeiro para habilitar anexos.")
                return

            file_path = filedialog.askopenfilename(
                title="Selecione um arquivo para anexar"
            )
            if not file_path:
                return

            # Pasta de anexos por obra/item
            base = os.path.join("anexos_obras", f"obra_{self.obra_id}", f"item_{self.item_data['id']}")
            os.makedirs(base, exist_ok=True)

            destino = os.path.join(base, os.path.basename(file_path))
            shutil.copy(file_path, destino)
            messagebox.showinfo("Anexo", "Arquivo anexado com sucesso!")
            # Windows: abre a pasta
            if os.name == "nt":
                os.startfile(base)
        except Exception as e:
            messagebox.showerror("Erro ao anexar", f"{e}")


class DarBaixaWindow(ctk.CTkToplevel):
    def __init__(self, master, item, on_save_callback):
        super().__init__(master)
        self.item = item; self.on_save_callback = on_save_callback
        self.title(f"Dar Baixa: {self.item['nome']}"); self.geometry("400x300"); self.grab_set()
        ctk.CTkLabel(self, text=f"Item: {self.item['nome']}\nEstoque Atual: {self.item.get('qtd_estoque', 0)}", font=("", 14)).pack(pady=15)
        ctk.CTkLabel(self, text="Quantidade a ser baixada:").pack(padx=20, anchor="w")
        self.qtd_entry = ctk.CTkEntry(self); self.qtd_entry.pack(padx=20, fill="x")
        ctk.CTkLabel(self, text="Observação (Ex: item quebrado):").pack(padx=20, anchor="w", pady=(10,0))
        self.obs_textbox = ctk.CTkTextbox(self, height=80); self.obs_textbox.pack(padx=20, fill="x")
        ctk.CTkButton(self, text="Confirmar Baixa", command=self.confirmar_baixa, fg_color="#d9534f").pack(side="bottom", pady=20, padx=20, fill="x")
    def confirmar_baixa(self):
        try:
            quantidade = int(self.qtd_entry.get())
            observacao = self.obs_textbox.get("1.0", "end-1c")
            if quantidade <= 0:
                messagebox.showerror("Erro", "A quantidade deve ser maior que zero.")
                return
            responsavel = getattr(self.master, "current_user", None)  # master é a janela principal (App)
            success, message = db.dar_baixa_item(self.item['id'], quantidade, observacao, responsavel)
            if success:
                messagebox.showinfo("Sucesso", message); self.on_save_callback(); self.destroy()
            else:
                messagebox.showerror("Erro", message)
        except ValueError:
            messagebox.showerror("Erro", "A quantidade deve ser um número válido.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

class SelecionarItemParaAcaoWindow(ctk.CTkToplevel):
    def __init__(self, master, obra_id, acao_callback, titulo="Selecionar Item"):
        super().__init__(master)
        self.obra_id = obra_id; self.acao_callback = acao_callback
        self.title(titulo); self.geometry("600x400"); self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=titulo, font=("", 16, "bold")).grid(row=0, column=0, pady=10)
        self.search_entry = ctk.CTkEntry(self, placeholder_text="Buscar item por nome / série..."); self.search_entry.grid(row=1, column=0, padx=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())
        self.list_frame = ctk.CTkScrollableFrame(self); self.list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.refresh_list()
    def refresh_list(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        query = self.search_entry.get().lower()
        items = db.get_items_by_obra(self.obra_id)
        filtered = []
        for row in items:
            nome = row['nome'] or ""
            numero_serie = row.get('numero_serie') or ""
            if (query in nome.lower()) or (query in str(numero_serie).lower()) or not query:
                filtered.append(row)
        for i, item in enumerate(filtered):
            frame = ctk.CTkFrame(self.list_frame); frame.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(frame, text=f"{item['nome']} ({item.get('categoria_nome','')}) - Estoque: {item.get('qtd_estoque',0)}").pack(side="left", padx=10)
            ctk.CTkButton(frame, text="Selecionar", width=100, command=lambda it=item: self.selecionar(it)).pack(side="right", padx=10)
    def selecionar(self, item):
        self.acao_callback(item); self.destroy()

class DevolverItemWindow(ctk.CTkToplevel):
    def __init__(self, master, item, on_save_callback):
        super().__init__(master)
        self.item = item
        self.on_save_callback = on_save_callback
        self.title(f"Devolver ao Estoque: {self.item['nome']}")
        self.geometry("400x300")
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f"Item: {self.item['nome']}\nEm uso: {self.item.get('qtd_em_uso', 0)}",
            font=("", 14)
        ).pack(pady=15)

        ctk.CTkLabel(self, text="Quantidade a devolver:").pack(padx=20, anchor="w")
        self.qtd_entry = ctk.CTkEntry(self)
        self.qtd_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Observação:").pack(padx=20, anchor="w", pady=(10, 0))
        self.obs_textbox = ctk.CTkTextbox(self, height=80)
        self.obs_textbox.pack(padx=20, fill="x")

        ctk.CTkButton(
            self,
            text="Confirmar Devolução",
            command=self.confirmar_devolucao,
            fg_color="#28a745"
        ).pack(side="bottom", pady=20, padx=20, fill="x")

    def confirmar_devolucao(self):
        try:
            quantidade = int(self.qtd_entry.get())
            observacao = self.obs_textbox.get("1.0", "end-1c").strip()

            if quantidade <= 0:
                messagebox.showerror("Erro", "A quantidade deve ser maior que zero.")
                return

            success, msg = db.devolver_item(self.item['id'], quantidade, observacao)
            if success:
                messagebox.showinfo("Sucesso", msg)
                self.on_save_callback()
                self.destroy()
            else:
                messagebox.showerror("Erro", msg)
        except ValueError:
            messagebox.showerror("Erro", "Digite um número válido para a quantidade.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

class TransferirWindow(ctk.CTkToplevel):
    def __init__(self, master, item, obra_id, on_save_callback):
        super().__init__(master)
        self.master = master  # salva master para acessar app depois
        self.item = item
        self.obra_id = obra_id
        self.on_save_callback = on_save_callback

        self.title(f"Transferir: {item['nome']}")
        self.geometry("400x360")
        self.grab_set()

        ctk.CTkLabel(self, text=f"Item: {item['nome']}").pack(pady=10)

        # Quantidade
        ctk.CTkLabel(self, text="Quantidade a transferir:").pack(padx=20, anchor="w")
        self.qtd_entry = ctk.CTkEntry(self)
        self.qtd_entry.pack(padx=20, fill="x")

        # Novo campo: Obra de Destino
        from db import fetch_all
        obras = [o['nome'] for o in fetch_all("SELECT nome FROM obras ORDER BY nome")]
        ctk.CTkLabel(self, text="Destino:").pack(padx=20, anchor="w", pady=(10,0))
        self.obra_destino_var = ctk.StringVar(value=obras[0])
        self.obra_destino_menu = ctk.CTkOptionMenu(self, variable=self.obra_destino_var, values=obras)
        self.obra_destino_menu.pack(padx=20, fill="x")

        # Observação
        ctk.CTkLabel(self, text="Observação:").pack(padx=20, anchor="w", pady=(10,0))
        self.obs_textbox = ctk.CTkTextbox(self, height=80)
        self.obs_textbox.pack(padx=20, fill="x")

        ctk.CTkButton(
            self,
            text="Confirmar Transferência",
            command=self.confirm_transfer
        ).pack(side="bottom", pady=15, padx=20, fill="x")

    def confirm_transfer(self):
        try:
            qtd = int(self.qtd_entry.get())
            obs = self.obs_textbox.get("1.0", "end-1c")
            obra_destino_nome = self.obra_destino_var.get()

            if qtd <= 0:
                messagebox.showerror("Erro", "A quantidade deve ser maior que zero.")
                return

            # Busca ID da obra destino no banco
            obra_destino_id = db.get_obra_id(obra_destino_nome)

            # Faz a transferência
            success, msg = db.transfer_item(
                self.item['id'],               # ID do item
                obra_destino_id,               # NOVA obra destino
                obra_destino_nome,             # Passa nome para log
                qtd,
                obs,
                self.master.app.current_user   # Usuário logado
            )

            if success:
                messagebox.showinfo("Sucesso", msg)
                self.on_save_callback()  # atualiza a lista da obra atual
                self.destroy()
            else:
                messagebox.showerror("Erro", msg)

        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")


# ------------------------------
# ObraWindow (mantida) - janela por obra com Dashboard/Estoque/Relatórios
# ------------------------------
# SUBSTITUA a sua classe ObraWindow por esta
class ObraWindow(ctk.CTkToplevel):
    def __init__(self, master, obra_nome):
        super().__init__(master)
        self.app = app
        self.obra_nome = obra_nome
        self.obra_id = db.get_obra_id(self.obra_nome)
        self.title(f"Controle de Estoque: {self.obra_nome}")
        self.geometry("1100x700")
        self.grab_set()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- MENU LATERAL ---
        menu_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        menu_frame.grid(row=0, column=0, sticky="nsw")
        ctk.CTkLabel(menu_frame, text=self.obra_nome, font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 8), padx=10)
        ctk.CTkButton(menu_frame, text="Dashboard", command=self.show_dashboard_view).pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(menu_frame, text="Estoque", command=self.show_estoque_view).pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(menu_frame, text="Relatórios", command=self.show_relatorios_view).pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(menu_frame, text="Página Principal", fg_color="gray", command=self.destroy).pack(side="bottom", pady=10, padx=10, fill="x")
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.show_dashboard_view()

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()        

    def show_dashboard_view(self):
        self.clear_content_frame()
        stats = db.get_dashboard_stats(self.obra_id)
        stats = {k: stats.get(k, 0) if isinstance(stats, dict) else 0 for k in ['total','em_uso','disponivel','manutencao']} if stats else {'total':0,'em_uso':0,'disponivel':0,'manutencao':0}
        self.content_frame.grid_columnconfigure((0, 1), weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)  # título
        self.content_frame.grid_rowconfigure(1, weight=0)  # cards linha 1
        self.content_frame.grid_rowconfigure(2, weight=0)  # cards linha 2
        self.content_frame.grid_rowconfigure(3, weight=1)  # lista top 5 expande

        # Título mais próximo do conteúdo
        ctk.CTkLabel(
            self.content_frame,
            text="Dashboard da Obra",
            font=("", 22, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 8), sticky="w")
        
        # Cards de KPIs — fundo branco com borda colorida lateral
        card_defs = [
            ("Total de Itens",           stats['total'],      THEME["accent_blue"],   "📦"),
            ("Em Uso",                   stats['em_uso'],     THEME["accent_purple"],  "🔧"),
            ("Disponíveis em Estoque",   stats['disponivel'], THEME["accent_green"],   "✅"),
            ("Manutenção / Quebrados",   stats['manutencao'], THEME["accent_red"],     "⚠️"),
        ]
        for i, (texto, valor, accent, icon) in enumerate(card_defs):
            row, col = divmod(i, 2)
            card = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF",
                                corner_radius=12, border_width=1, border_color="#E2E8F0")
            card.grid(row=row+1, column=col, padx=8, pady=8, sticky="nsew")
            # barra de acento colorida no topo
            ctk.CTkFrame(card, height=4, fg_color=accent, corner_radius=4
                         ).pack(fill="x", padx=0, pady=(0, 0))
            ctk.CTkLabel(card, text=f"{icon}  {texto}",
                         font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"],
                         anchor="w").pack(padx=16, pady=(10, 2), anchor="w")
            ctk.CTkLabel(card, text=str(valor),
                         font=ctk.CTkFont(size=34, weight="bold"), text_color=THEME["text"],
                         anchor="w").pack(padx=16, pady=(0, 14), anchor="w")

        # Frame Top 5
        top_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF",
                                  corner_radius=12, border_width=1, border_color="#E2E8F0")
        top_frame.grid(row=3, column=0, columnspan=2, padx=8, pady=(4, 8), sticky="nsew")
        ctk.CTkLabel(top_frame, text="Itens por Categoria",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text"]
                     ).pack(anchor="w", padx=16, pady=(14, 6))
        ctk.CTkFrame(top_frame, height=1, fg_color="#E2E8F0").pack(fill="x", padx=16, pady=(0, 8))

        try:
            top_perifericos = db.get_top_perifericos(self.obra_id, limit=5) if hasattr(db, 'get_top_perifericos') else []
            lista = top_perifericos or sorted(
                [(c['nome'], db.get_total_por_categoria(self.obra_id, c['id']) if hasattr(db, 'get_total_por_categoria') else 0)
                 for c in db.get_categorias()], key=lambda x: x[1], reverse=True)[:5]
            for nome, qtd in (lista if isinstance(lista[0], tuple) else [(p['nome'], p['qtd']) for p in lista]):
                row_f = ctk.CTkFrame(top_frame, fg_color="transparent")
                row_f.pack(fill="x", padx=16, pady=3)
                ctk.CTkLabel(row_f, text=f"• {nome}", font=ctk.CTkFont(size=13),
                             text_color=THEME["text"], anchor="w").pack(side="left")
                ctk.CTkLabel(row_f, text=str(qtd), font=ctk.CTkFont(size=13, weight="bold"),
                             text_color=THEME["accent_blue"]).pack(side="right")
        except Exception:
            ctk.CTkLabel(top_frame, text="Dados indisponíveis",
                         text_color=THEME["text_secondary"]).pack(padx=16, pady=8, anchor="w")
            
    # >>> INÍCIO (ObraWindow.show_estoque_view - substituir método completo)
    # >>> INÍCIO (ObraWindow.show_estoque_view - substituir método completo)
    # >>> INÍCIO (ObraWindow.show_estoque_view - ajustar configuração de colunas)
# >>> INÍCIO (ObraWindow.show_estoque_view - método completo)
    def show_estoque_view(self):
        self.clear_content_frame()
        
        # Configurar grid principal para expansão
        self.content_frame.grid_rowconfigure(2, weight=1)  # Linha da tabela expande
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # --- Barra de busca ---
        top_frame = ctk.CTkFrame(self.content_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.search_entry = ctk.CTkEntry(
            top_frame,
            placeholder_text="Buscar item por nome ou número de série..."
        )
        self.search_entry.pack(side="left", padx=6, pady=6, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_estoque_list())

        # --- Linha de botões ---
        action_frame = ctk.CTkFrame(self.content_frame)
        action_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkButton(action_frame, text="+ Adicionar Item",
                    command=self.open_add_item_window,
                    width=150, height=32).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(action_frame, text="Dar Baixa",
                    command=self.quick_baixa_action,
                    width=150, height=32).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(action_frame, text="Transferir",
                    command=self.quick_transfer_action,
                    width=150, height=32).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(action_frame, text="↺ Atualizar",
                    command=self.refresh_estoque_list,
                    width=110, height=32,
                    fg_color="gray", hover_color="#555").pack(side="right", padx=5, pady=5)

        # --- Container principal da tabela (ocupa espaço restante) ---
        table_container = ctk.CTkFrame(self.content_frame)
        table_container.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # --- ScrollableFrame preenchendo o container ---
        self.item_list_frame = ctk.CTkScrollableFrame(table_container)
        self.item_list_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configurar colunas da tabela (4 colunas de dados + 1 buffer)
        for col in range(5):
            if col < 4:  # Colunas de dados
                self.item_list_frame.grid_columnconfigure(col, weight=1)
            else:  # Coluna buffer para scrollbar
                self.item_list_frame.grid_columnconfigure(col, minsize=24, weight=0)

        self.refresh_estoque_list()
        # inicia refresh automático a cada 30s (apenas uma vez por sessão)
        if not getattr(self, "_auto_refresh_started", False):
            self._auto_refresh_started = True
            self.after(30000, self.auto_refresh)

    # >>> INÍCIO (ObraWindow.refresh_estoque_list - ajustar apenas os botões)
    # >>> INÍCIO (ObraWindow.refresh_estoque_list - substituir método completo)
    # >>> INÍCIO (ObraWindow.refresh_estoque_list - ajustar apenas o botão Devolver)
    def refresh_estoque_list(self):
        for widget in self.item_list_frame.winfo_children():
            widget.destroy()

        # Busca itens
        items = db.get_items_by_obra(self.obra_id) or []
        q = self.search_entry.get().strip().lower() if hasattr(self, 'search_entry') else ""

        filtered = []
        for r in items:
            nome = (r.get('nome') or "").lower()
            serie = (r.get('numero_serie') or "").lower()
            cat = (r.get('categoria_nome') or "").lower()
            if q and not (q in nome or q in serie or q in cat):
                continue
            filtered.append(r)

        # Cabeçalhos
        headers = ["Item", "Qtd. Estoque", "Status", "Ações"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(
                self.item_list_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            ).grid(row=0, column=i, padx=15, pady=10, sticky="ew")
        
        # Coluna buffer vazia no cabeçalho
        ctk.CTkLabel(self.item_list_frame, text="").grid(row=0, column=4, padx=0, pady=10)

        # Linhas de dados
        for i, item_row in enumerate(filtered, start=1):
            item_data = dict(item_row)

            # COLUNA 0: "Item"
            ctk.CTkLabel(
                self.item_list_frame, 
                text=item_data.get('categoria_nome', ''), 
                anchor="w", 
                justify="left",
                font=ctk.CTkFont(size=13)
            ).grid(row=i, column=0, padx=15, pady=8, sticky="ew")

            # COLUNA 1: "Qtd. Estoque"
            ctk.CTkLabel(
                self.item_list_frame, 
                text=item_data.get('qtd_estoque', 0), 
                anchor="center",
                font=ctk.CTkFont(size=13)
            ).grid(row=i, column=1, padx=15, pady=8, sticky="ew")

            # COLUNA 2: "Status"
            ctk.CTkLabel(
                self.item_list_frame, 
                text=item_data.get('status', ''), 
                anchor="center",
                font=ctk.CTkFont(size=13)
            ).grid(row=i, column=2, padx=15, pady=8, sticky="ew")

            # COLUNA 3: "Ações"
            actions = ctk.CTkFrame(self.item_list_frame, fg_color="transparent")
            actions.grid(row=i, column=3, padx=12, pady=8, sticky="e")
            
            ctk.CTkButton(actions, text="Editar", width=60,
                        command=lambda it=item_data: self.open_edit_item_window(it)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Baixar", width=60,
                        command=lambda it=item_data: self.open_dar_baixa_window(it)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Transf.", width=60,
                        command=lambda it=item_data: self.open_transfer_window(it)).pack(side="left", padx=3)
            # BOTÃO DEVOLVER COM LARGURA AUMENTADA
            ctk.CTkButton(actions, text="Devolver", width=90, fg_color="#28a745",  # Aumentado de 70 para 80
                        command=lambda it=item_data: DevolverItemWindow(
                            self, item=it, on_save_callback=self.refresh_estoque_list
                        )).pack(side="left", padx=3)

            # Coluna buffer vazia na linha
            ctk.CTkLabel(self.item_list_frame, text="").grid(row=i, column=4, sticky="nsew")

        # Spacer final para preencher espaço vazio
        if filtered:
            last_row = len(filtered) + 1
            self.item_list_frame.grid_rowconfigure(last_row, weight=1)
            spacer = ctk.CTkLabel(self.item_list_frame, text="")
            spacer.grid(row=last_row, column=0, columnspan=5, sticky="nsew")
        else:
            self.item_list_frame.grid_rowconfigure(1, weight=1)
            spacer = ctk.CTkLabel(self.item_list_frame, text="Nenhum item encontrado")
            spacer.grid(row=1, column=0, columnspan=5, sticky="nsew")
# <<< FIM

    def auto_refresh(self):
        try:
            self.refresh_estoque_list()
        except Exception:
            pass
        self.after(30000, self.auto_refresh)

    def open_add_item_window(self): ItemEditWindow(self, obra_id=self.obra_id, on_save_callback=self.refresh_estoque_list)
    def open_edit_item_window(self, item): ItemEditWindow(self, obra_id=self.obra_id, item=item, on_save_callback=self.refresh_estoque_list)
    def open_dar_baixa_window(self, item): DarBaixaWindow(self, item=item, on_save_callback=self.refresh_estoque_list)
    def open_transfer_window(self, item):
        TransferirWindow(
            self,
            item=item,
            obra_id=self.obra_id,
            on_save_callback=self.refresh_estoque_list  # ✅ chama o refresh certo após transferência
        )
    def quick_baixa_action(self):
        SelecionarItemParaAcaoWindow(self, self.obra_id, lambda item: DarBaixaWindow(self, item=item, on_save_callback=self.refresh_estoque_list), titulo="Selecionar item para baixa")
    def quick_transfer_action(self):
        SelecionarItemParaAcaoWindow(
            self,
            self.obra_id,
            lambda item: TransferirWindow(
                self,
                item=item,
                obra_id=self.obra_id,
                on_save_callback=self.refresh_estoque_list  # ✅ recarrega lista
            ),
            titulo="Selecionar item para transferir"
        )
    def show_relatorios_view(self):
        import datetime
        self.clear_content_frame()
        self.content_frame.grid_columnconfigure((0, 1), weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)  # título
        self.content_frame.grid_rowconfigure(1, weight=0)  # labels
        self.content_frame.grid_rowconfigure(2, weight=0)  # entries
        self.content_frame.grid_rowconfigure(3, weight=1)  # botões

        ctk.CTkLabel(
            self.content_frame,
            text="Gerar Relatório de Movimentações",
            font=("", 24, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        # Labels
        ctk.CTkLabel(self.content_frame, text="Data de Início (AAAA-MM-DD):").grid(row=1, column=0, padx=(0,5), pady=5, sticky="w")
        ctk.CTkLabel(self.content_frame, text="Data de Fim (AAAA-MM-DD):").grid(row=1, column=1, padx=(5,0), pady=5, sticky="w")

        # Entradas de Data
        self.data_inicio_entry = ctk.CTkEntry(self.content_frame, placeholder_text="Ex: 2025-01-01")
        self.data_inicio_entry.grid(row=2, column=0, padx=(0,5), pady=5, sticky="ew")

        self.data_fim_entry = ctk.CTkEntry(self.content_frame, placeholder_text="Ex: 2025-12-31")
        self.data_fim_entry.grid(row=2, column=1, padx=(5,0), pady=5, sticky="ew")

        # 🔧 Pré-preenche com o mês atual
        hoje = datetime.date.today()
        primeiro_dia = hoje.replace(day=1)
        self.data_inicio_entry.insert(0, str(primeiro_dia))
        self.data_fim_entry.insert(0, str(hoje))

        # Botões
        export_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        export_frame.grid(row=3, column=0, columnspan=2, pady=20, sticky="e")
        ctk.CTkButton(export_frame, text="Exportar para Excel (.xlsx)", command=self.exportar_excel).pack(side="left", padx=5)
        ctk.CTkButton(export_frame, text="Exportar para PDF (.pdf)", command=self.exportar_pdf).pack(side="left", padx=5)


    def exportar_excel(self):
        data_inicio = self.data_inicio_entry.get()
        data_fim = self.data_fim_entry.get()

        if not (data_inicio and data_fim):
            messagebox.showerror("Erro", "Por favor, preencha as datas de início e fim.")
            return

        self.configure(cursor="watch")
        self.update()
        try:
            movimentacoes = db.get_movimentacoes_por_periodo(self.obra_id, data_inicio, data_fim)
        finally:
            self.configure(cursor="")

        if not movimentacoes:
            messagebox.showinfo("Sem Dados", "Nenhuma movimentação encontrada para o período.")
            return

        dados_lista = [dict(row) for row in movimentacoes]

        for row in dados_lista:
            data_str = str(row.get('data_movimentacao') or row.get('data'))
            try:
                if '.' in data_str:
                    data_obj = datetime.datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    data_obj = datetime.datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
                row['data'] = data_obj.strftime('%d/%m/%Y')
            except Exception:
                pass

        df = pd.DataFrame(dados_lista)

        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if not filepath:
            return

        try:
            self.configure(cursor="watch")
            self.update()
            df.to_excel(filepath, index=False, engine='openpyxl')
            self.configure(cursor="")
            messagebox.showinfo("Sucesso", f"Relatório salvo com sucesso em:\n{filepath}")
            if os.name == 'nt':
                os.startfile(filepath)
        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro: {e}")

    def exportar_pdf(self):
        data_inicio = self.data_inicio_entry.get()
        data_fim = self.data_fim_entry.get()
        if not (data_inicio and data_fim):
            messagebox.showerror("Erro", "Por favor, preencha as datas de início e fim.")
            return

        self.configure(cursor="watch")
        self.update()
        try:
            movimentacoes = db.get_movimentacoes_por_periodo(self.obra_id, data_inicio, data_fim)
        finally:
            self.configure(cursor="")

        if not movimentacoes:
            messagebox.showinfo("Sem Dados", "Nenhuma movimentação encontrada para o período selecionado.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if not filepath:
            return
        try:
            self.configure(cursor="watch")
            self.update()
            c = canvas.Canvas(filepath, pagesize=letter)
            width, height = letter
            c.drawString(inch, height - inch, f"Relatório de Movimentações - Obra: {self.obra_nome}")
            c.drawString(inch, height - inch - 20, f"Período: {data_inicio} a {data_fim}")
            y = height - inch * 2
            headers = ["Data", "Item", "Tipo", "Qtd", "Observação"]
            x_offsets = [inch, 2.2*inch, 4*inch, 4.7*inch, 5.2*inch]
            for i, header in enumerate(headers):
                c.drawString(x_offsets[i], y, header)
            y -= 20
            for row in movimentacoes:
                data_completa_str = str(row['data'])
                if '.' in data_completa_str:
                    data_obj = datetime.datetime.strptime(data_completa_str, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    data_obj = datetime.datetime.strptime(data_completa_str, '%Y-%m-%d %H:%M:%S')
                data_formatada_br = data_obj.strftime('%d/%m/%Y')
                c.drawString(x_offsets[0], y, data_formatada_br)
                c.drawString(x_offsets[1], y, str(row.get('nome', ''))[:25])
                c.drawString(x_offsets[2], y, str(row['tipo']))
                c.drawString(x_offsets[3], y, str(row['quantidade']))
                c.drawString(x_offsets[4], y, str(row['observacao'] or '')[:35])
                y -= 15
                if y < inch:
                    c.showPage()
                    y = height - inch
            c.save()
            self.configure(cursor="")
            messagebox.showinfo("Sucesso", f"Relatório PDF salvo com sucesso em:\n{filepath}")
            if os.name == 'nt':
                os.startfile(filepath)
            else:
                subprocess.run(['open' if os.sys.platform == 'darwin' else 'xdg-open', filepath])
        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro ao gerar o PDF: {e}")

# ------------------------------
# ObraCard (usada na seleção de obras)
# ------------------------------
class ObraCard(ctk.CTkFrame):
    def __init__(self, master, obra_nome, callback):
        super().__init__(master, corner_radius=12, border_width=1,
                         border_color=THEME["border"], fg_color="#FFFFFF")
        self.grid_columnconfigure(0, weight=1)
        # Faixa de acento no topo
        ctk.CTkFrame(self, height=4, fg_color=THEME["primary"], corner_radius=4
                     ).grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 0))
        ctk.CTkLabel(self, text="🏗️", font=ctk.CTkFont(size=28)
                     ).grid(row=1, column=0, pady=(16, 4))
        ctk.CTkLabel(self, text=obra_nome, font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=THEME["text"], wraplength=160
                     ).grid(row=2, column=0, padx=16, pady=(0, 12))
        ctk.CTkButton(
            self, text="Acessar →", height=36,
            fg_color=THEME["primary"], hover_color=THEME["primary_hover"],
            font=ctk.CTkFont(size=13), corner_radius=8,
            command=lambda: callback(obra_nome)
        ).grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")

# ------------------------------
# FRAMES PRINCIPAIS: NotebooksFrame, ObrasSelectionFrame, RelatoriosFrame
# ------------------------------
class NotebooksFrame(ctk.CTkFrame):
    def __init__(self, master, open_detail_callback):
        super().__init__(master)
        self.open_detail_callback = open_detail_callback

        # estado do filtro
        self.notebook_filter = {"situacao": "Todas", "obra": "Todas"}

        # layout base
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Inventário de Notebooks",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=THEME["text"]
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="📊 Relatórios", height=36,
            fg_color="transparent", border_width=1, border_color=THEME["border"],
            text_color=THEME["text_secondary"], hover_color=THEME["border"],
            font=ctk.CTkFont(size=13), corner_radius=8,
            command=self.abrir_relatorios_notebooks
        ).grid(row=0, column=3, sticky="e", padx=(6, 0))

        ctk.CTkButton(
            header, text="🔍 Filtros", height=36,
            fg_color="transparent", border_width=1, border_color=THEME["border"],
            text_color=THEME["text_secondary"], hover_color=THEME["border"],
            font=ctk.CTkFont(size=13), corner_radius=8,
            command=self.open_notebook_filters
        ).grid(row=0, column=2, sticky="e", padx=(6, 0))

        ctk.CTkButton(
            header, text="+ Novo Notebook", height=36,
            fg_color=THEME["primary"], hover_color=THEME["primary_hover"],
            font=ctk.CTkFont(size=13), corner_radius=8,
            command=lambda: self.open_detail_callback(None)
        ).grid(row=0, column=1, sticky="e", padx=(6, 0))
            

        # onde ficam os botões/etiquetas dos notebooks
        self.notebook_scroll_frame = ctk.CTkScrollableFrame(self)
        self.notebook_scroll_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.update_notebook_grid()

    # -----------------------
    # Modal simples de filtro
    # -----------------------
    def open_notebook_filters(self):
        win = ctk.CTkToplevel(self)
        win.title("Filtros — Notebooks")
        win.geometry("340x240")
        win.grab_set()

        # Situação
        ctk.CTkLabel(win, text="Situação do Notebook:").pack(padx=20, pady=(18, 6), anchor="w")
        situacoes = ["Todas", "Disponível", "Alocado", "Triagem", "Verificar", "Assistência Técnica"]
        sit_var = ctk.StringVar(value=self.notebook_filter.get("situacao", "Todas"))
        ctk.CTkOptionMenu(win, variable=sit_var, values=situacoes).pack(padx=20, fill="x")

        # Obra
        ctk.CTkLabel(win, text="Obra:").pack(padx=20, pady=(14, 6), anchor="w")
        obras = ["Todas"] + LISTA_OBRAS
        obra_var = ctk.StringVar(value=self.notebook_filter.get("obra", "Todas"))
        ctk.CTkOptionMenu(win, variable=obra_var, values=obras).pack(padx=20, fill="x")

        # Ações
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=20, pady=18)
        ctk.CTkButton(btns, text="Cancelar", fg_color="gray", command=win.destroy)\
            .pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            btns, text="Salvar",
            command=lambda: (self.apply_notebook_filters({
                "situacao": sit_var.get(),
                "obra": obra_var.get(),
            }), win.destroy())
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

    def apply_notebook_filters(self, new_filter: dict):
        self.notebook_filter.update(new_filter or {})
        self.update_notebook_grid()

    # -----------------------
    # Listagem com filtros
    # -----------------------
    def update_notebook_grid(self):
        # limpa a grade
        for w in self.notebook_scroll_frame.winfo_children():
            w.destroy()

        # busca notebooks, incluindo possivelmente o campo 'usuario_atual'
        conn, cursor = db_connect_notebooks()
        try:
            cursor.execute("""
                SELECT placa_id, situacao,
                    COALESCE(obra, setor, '') AS obra,
                    COALESCE(usuario_atual, '') AS usuario_atual
                FROM notebooks
                ORDER BY CAST(placa_id AS INTEGER)
            """)
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception:
            cursor.execute("""
                SELECT placa_id, situacao
                FROM notebooks
                ORDER BY CAST(placa_id AS INTEGER)
            """)
            rows = [dict(r) | {"obra": "", "usuario_atual": ""} for r in cursor.fetchall()]
        finally:
            conn.close()

        # aplica filtros
        sit_filtro = self.notebook_filter.get("situacao", "Todas")
        obra_filtro = self.notebook_filter.get("obra", "Todas")

        filtrados = []
        for r in rows:
            situ = (r.get("situacao") or "").strip()
            obra = (r.get("obra") or "").strip()
            if sit_filtro != "Todas" and situ != sit_filtro:
                continue
            if obra_filtro != "Todas" and obra != obra_filtro:
                continue
            filtrados.append(r)

        # monta grade
        row, col = 0, 0
        for item in filtrados:
            color = STATUS_COLORS.get(item.get('situacao', ''), "#E0E0E0")
            text_color = TEXT_COLORS.get(item.get('situacao', ''), "black")
            placa = str(item.get('placa_id', '')).strip()
            usuario = str(item.get('usuario_atual', '')).strip()

            # exibe o nome da pessoa logo abaixo do número da placa
            if usuario and usuario.lower() not in ("", "none", "null"):
                if len(usuario) > 18:
                    usuario = usuario[:18] + "…"
                texto = f"{placa}\n{usuario}"
            else:
                texto = placa

            btn = ctk.CTkButton(
                self.notebook_scroll_frame,
                text=texto,
                fg_color=color,
                hover_color=color,
                text_color=text_color,
                height=50,  # levemente maior para caber duas linhas
                command=lambda p=placa: self.open_detail_callback(p)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            col = (col + 1) % 5
            if col == 0:
                row += 1

        for i in range(5):
            self.notebook_scroll_frame.grid_columnconfigure(i, weight=1)


    def abrir_relatorios_notebooks(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Relatórios de Notebooks")
        janela.geometry("300x150")
        janela.grab_set()

        ctk.CTkLabel(janela, text="Exportar relatórios:", font=("", 14, "bold")).pack(pady=10)
        ctk.CTkButton(janela, text="Exportar Excel (.xlsx)", command=lambda: (janela.destroy(), self.exportar_notebooks_excel())).pack(pady=5)
        ctk.CTkButton(janela, text="Exportar PDF (.pdf)", command=lambda: (janela.destroy(), self.exportar_notebooks_pdf())).pack(pady=5)

    def exportar_notebooks_excel(self):
        from tkinter import filedialog, messagebox
        import pandas as pd, os

        dados = self._coletar_dados_notebooks()
        if not dados:
            messagebox.showinfo("Sem Dados", "Nenhum notebook encontrado para exportação.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if not filepath:
            return

        try:
            self.configure(cursor="watch")
            self.update()
            df = pd.DataFrame(dados)
            df.to_excel(filepath, index=False, engine="openpyxl")
            self.configure(cursor="")
            messagebox.showinfo("Sucesso", f"Relatório salvo em:\n{filepath}")
            if os.name == "nt":
                os.startfile(filepath)
        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Erro", f"Ocorreu um erro ao gerar Excel: {e}")

    def exportar_notebooks_pdf(self):
        from tkinter import filedialog, messagebox
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        dados = self._coletar_dados_notebooks()
        if not dados:
            messagebox.showinfo("Sem Dados", "Nenhum notebook encontrado para exportação.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if not filepath:
            return

        try:
            self.configure(cursor="watch")
            self.update()
            doc = SimpleDocTemplate(filepath)
            styles = getSampleStyleSheet()
            elements = [Paragraph("Relatório de Notebooks", styles["Title"]), Spacer(1, 12)]

            table_data = [list(dados[0].keys())] + [list(row.values()) for row in dados]
            table = Table(table_data)
            table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
            elements.append(table)

            doc.build(elements)
            self.configure(cursor="")
            messagebox.showinfo("Sucesso", f"Relatório PDF salvo em:\n{filepath}")
            if os.name == "nt":
                os.startfile(filepath)
        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Erro", f"Ocorreu um erro ao gerar PDF: {e}")

    def _coletar_dados_notebooks(self):
        conn, cursor = db_connect_notebooks()
        query = "SELECT placa_id, numero_serie, usuario_anterior, usuario_atual, setor, cargo, nota_fiscal, perifericos, observacao, situacao FROM notebooks"
        filtros = []
        params = []

        if self.notebook_filter.get("situacao") and self.notebook_filter["situacao"] != "Todas":
            filtros.append("situacao = ?")
            params.append(self.notebook_filter["situacao"])
        if self.notebook_filter.get("obra") and self.notebook_filter["obra"] != "Todas":
            filtros.append("obra = ?")
            params.append(self.notebook_filter["obra"])

        if filtros:
            query += " WHERE " + " AND ".join(filtros)

        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows


class ObrasSelectionFrame(ctk.CTkFrame):
    def __init__(self, master, open_obra_callback):
        super().__init__(master)
        self.open_obra_callback = open_obra_callback
        ctk.CTkLabel(self, text="Selecione a Obra para Gerenciar Estoque", font=ctk.CTkFont(size=20, weight="bold")).pack(padx=20, pady=20, anchor="w")
        obras_scroll_frame = ctk.CTkScrollableFrame(self); obras_scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        obras_scroll_frame.grid_columnconfigure((0,1,2,3), weight=1)
        row, col = 0, 0
        for obra_nome in LISTA_OBRAS:
            card = ObraCard(obras_scroll_frame, obra_nome, open_obra_callback)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            col = (col + 1) % 4
            if col == 0: row += 1

from db import get_movimentacoes_por_usuario

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# >>> PATCH: RelatoriosFrame (dashboard melhorado: KPIs + gráficos lado a lado + tabela com rolagem/zebra)
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import datetime

class RelatoriosFrame(ctk.CTkFrame):
    def __init__(self, app):
        """
        app: referência para a classe App (não apenas o frame content).
        Dessa forma podemos acessar current_user e outros atributos do App.
        """
        super().__init__(app.content)  # desenha dentro de app.content
        self.app = app

        # Título
        ctk.CTkLabel(
            self,
            text="Relatórios Gerais",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(padx=20, pady=(15, 5), anchor="w")

        # ----- Barra de filtros (datas) -----
        filtro_frame = ctk.CTkFrame(self)
        filtro_frame.pack(fill="x", padx=20, pady=(5, 10))

        self.data_inicio = ctk.CTkEntry(filtro_frame, placeholder_text="AAAA-MM-DD (Início)", width=150)
        self.data_inicio.pack(side="left", padx=5)

        self.data_fim = ctk.CTkEntry(filtro_frame, placeholder_text="AAAA-MM-DD (Fim)", width=150)
        self.data_fim.pack(side="left", padx=5)

        ctk.CTkButton(filtro_frame, text="Atualizar", command=self.load_data).pack(side="left", padx=10)
        ctk.CTkButton(
        filtro_frame,
        text="Exportar Excel",
        fg_color="#3b82f6",
        hover_color="#2563eb",
        command=self.exportar_excel
    ).pack(side="left", padx=10)

        # Pré-preenche mês corrente
        hoje = datetime.date.today()
        primeiro_dia = hoje.replace(day=1)
        if not self.data_inicio.get():
            self.data_inicio.insert(0, str(primeiro_dia))
        if not self.data_fim.get():
            self.data_fim.insert(0, str(hoje))

        # ----- Área de conteúdo dinâmica -----
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.load_data()

    # Util: formato dd/mm/YYYY hh:mm
    def _fmt_data(self, v: str) -> str:
        try:
            # tenta com microssegundos
            if "." in str(v):
                dt = datetime.datetime.strptime(str(v), "%Y-%m-%d %H:%M:%S.%f")
            else:
                dt = datetime.datetime.strptime(str(v), "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(v)

    def load_data(self):
        # Limpa a área antes de redesenhar
        for w in self.table_frame.winfo_children():
            w.destroy()

        # Guarda datas dos filtros (não filtramos no SQL aqui; exibimos no cabeçalho)
        data_ini = self.data_inicio.get().strip()
        data_fim = self.data_fim.get().strip()

        # --- Segurança: precisa de usuário logado
        username = getattr(self.app, "current_user", None)
        if not username:
            ctk.CTkLabel(self.table_frame, text="Nenhum usuário logado.", text_color="orange").pack(pady=10)
            return

        # --- Busca dados (por usuário)
        try:
            dados = get_movimentacoes_por_usuario(username)
        except Exception as e:
            ctk.CTkLabel(self.table_frame, text=f"Erro ao carregar dados: {e}", text_color="red").pack(pady=10)
            return

        if not dados:
            ctk.CTkLabel(
                self.table_frame,
                text=f"Nenhuma movimentação encontrada para o usuário '{username}'.",
                text_color="gray"
            ).pack(pady=10)
            return

        # DataFrame para facilitar análises/gráficos
        df = pd.DataFrame(dados)

        # Normalizações tolerantes
        if 'data' in df.columns:
            # mantém string formatada para exibição, mas cria coluna auxiliar para ordenação se precisar
            df['_data_fmt'] = df['data'].astype(str).map(self._fmt_data)
        else:
            df['_data_fmt'] = ""

        # Algumas bases (dependendo do teu log) podem trazer 'item' ou apenas 'item_id'
        if 'item' not in df.columns:
            df['item'] = df.get('item_id', "")

        # Quantidade numérica (caso venha como texto)
        if 'quantidade' in df.columns:
            df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce').fillna(0).astype(int)
        else:
            df['quantidade'] = 1  # fallback conservador

        # =========================
        # 1) KPIs (cards de resumo)
        # =========================
        kpi_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=6, pady=(0, 10))

        total_mov = int(len(df))
        itens_unicos = int(df['item'].nunique())
        por_tipo = df['tipo'].value_counts() if 'tipo' in df.columns else pd.Series([], dtype=int)
        n_baixas = int(por_tipo.get('Baixa', 0) or por_tipo.get('baixa', 0))
        n_devol = int(por_tipo.get('Devolução', 0) or por_tipo.get('devolucao', 0) or por_tipo.get('Devolucao', 0))
        # Transferências podem ter rótulos variados; somamos entradas + saídas
        n_transf = int(sum(v for k, v in por_tipo.items() if 'transfer' in str(k).lower()))

        def _kpi(card_parent, titulo, valor):
            card = ctk.CTkFrame(card_parent, corner_radius=10)
            card.pack(side="left", padx=6, pady=6)
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(8, 0))
            ctk.CTkLabel(card, text=str(valor), font=ctk.CTkFont(size=22, weight="bold")).pack(padx=12, pady=(0, 10))

        _kpi(kpi_frame, "Movimentações", total_mov)
        _kpi(kpi_frame, "Itens únicos", itens_unicos)
        _kpi(kpi_frame, "Baixas", n_baixas)
        _kpi(kpi_frame, "Devoluções", n_devol)
        _kpi(kpi_frame, "Transferências", n_transf)

        # Cabeçalho de período (visual)
        if data_ini and data_fim:
            ctk.CTkLabel(
                self.table_frame,
                text=f"Período: {data_ini} a {data_fim}",
                text_color="#A0A0A0"
            ).pack(padx=10, pady=(0, 6), anchor="w")

        # ====================================
        # 2) Gráficos lado a lado (barras + pizza)
        # ====================================
        graficos_frame = ctk.CTkFrame(self.table_frame)
        graficos_frame.pack(fill="x", padx=6, pady=(0, 10))

        # Gráfico 1 — Barras por Tipo (contagem)
        try:
            tipo_counts = (df['tipo'].value_counts() if 'tipo' in df.columns else pd.Series([], dtype=int))
            fig1 = Figure(figsize=(4.8, 2.6), dpi=100)
            ax1 = fig1.add_subplot(111)
            if len(tipo_counts) > 0:
                tipo_counts.plot(kind='bar', ax=ax1)
                ax1.set_title("Movimentações por Tipo")
                ax1.set_ylabel("Quantidade")
                ax1.set_xlabel("Tipo")
            canvas1 = FigureCanvasTkAgg(fig1, master=graficos_frame)
            canvas1.draw()
            canvas1.get_tk_widget().pack(side="left", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(graficos_frame, text=f"[Gráfico 1] Erro: {e}", text_color="red").pack(side="left", padx=8, pady=8)

        # Gráfico 2 — Top 5 Itens (pizza)
        try:
            top_items = df['item'].value_counts().head(5)
            fig2 = Figure(figsize=(4.8, 2.6), dpi=100)
            ax2 = fig2.add_subplot(111)
            if len(top_items) > 0:
                # pizza com percentual inteiro
                ax2.pie(top_items.values, labels=[str(k) for k in top_items.index], autopct="%1.0f%%")
                ax2.set_title("Top 5 Itens Movimentados")
            canvas2 = FigureCanvasTkAgg(fig2, master=graficos_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(side="left", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(graficos_frame, text=f"[Gráfico 2] Erro: {e}", text_color="red").pack(side="left", padx=8, pady=8)

        # ==============================
        # 3) Tabela com rolagem + zebra
        # ==============================
        # Header
        header = ctk.CTkFrame(self.table_frame)
        header.pack(fill="x", padx=10, pady=(4, 0))
        ctk.CTkLabel(header, text="Data", width=150, font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Item", width=250, font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Tipo", width=180, font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Quantidade", width=120, font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Saída / Responsável", width=220, font=ctk.CTkFont(weight="bold")).pack(side="left")  

        # ScrollableFrame
        scroll = ctk.CTkScrollableFrame(self.table_frame)
        scroll.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        # Linhas com zebra
        for i, row in df.iterrows():
            bg = "#2b2b2b" if i % 2 == 0 else "#1f1f1f"
            linha = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=0)
            linha.pack(fill="x", pady=1)

            ctk.CTkLabel(linha, text=str(row.get('_data_fmt', ''))[:16], width=150, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left", padx=(6, 0))
            # tenta converter ID em nome do item (se possível)
            item_valor = str(row.get('item', ''))
            try:
                # converte ID numérico em nome do item usando a função do módulo db
                if item_valor.isdigit():
                    nome_item = db.get_item_nome(int(item_valor))
                    if nome_item:
                        item_valor = nome_item
            except Exception:
                pass

            # Coluna final: destino ou responsável
            saida_resp = ""
            tipo_mov = str(row.get('tipo', '')).lower()
            obs = str(row.get('observacao', ''))
            resp = str(row.get('responsavel', ''))

            if "saída" in tipo_mov or "saida" in tipo_mov:
                # tenta extrair "Destino: ..." da observação
                if "destino:" in obs.lower():
                    try:
                        saida_resp = obs.split("Destino:")[-1].strip()
                    except Exception:
                        saida_resp = obs.strip()
                else:
                    saida_resp = obs or "-"
            else:
                saida_resp = resp or "-"

            ctk.CTkLabel(
                linha,
                text=saida_resp,
                width=220,
                anchor="center",
                font=ctk.CTkFont(size=12)
            ).pack(side="left")


            ctk.CTkLabel(
                linha,
                text=item_valor,
                width=250,
                anchor="center",  # centraliza o texto na coluna
                font=ctk.CTkFont(size=12)
            ).pack(side="left")
            ctk.CTkLabel(linha, text=str(row.get('tipo', '')), width=180, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(linha, text=str(row.get('quantidade', '')), width=120, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")
            

    from tkinter import filedialog, messagebox
    import os

    def exportar_excel(self):
        try:
            username = getattr(self.app, "current_user", None)
            if not username:
                messagebox.showwarning("Aviso", "Nenhum usuário logado.")
                return

            self.configure(cursor="watch")
            self.update()
            dados = get_movimentacoes_por_usuario(username)
            self.configure(cursor="")
            if not dados:
                messagebox.showinfo("Sem dados", "Nenhuma movimentação encontrada.")
                return

            import pandas as pd
            import db  # garante acesso às funções de banco

            df = pd.DataFrame(dados)

            # 🆕 Substitui 'item_id' pelo nome do item, se aplicável
            if 'item_id' in df.columns and 'item' not in df.columns:
                nomes_cache = {}

                def get_nome_by_id(i):
                    if i in nomes_cache:
                        return nomes_cache[i]
                    try:
                        nome = db.get_item_nome(int(i))
                        nomes_cache[i] = nome
                        return nome
                    except Exception:
                        return str(i)

                df['item'] = df['item_id'].apply(get_nome_by_id)
                df.drop(columns=['item_id'], inplace=True)

            # Ordena colunas para deixar 'item' e 'tipo' no início
            cols = list(df.columns)
            for c in ['item', 'tipo']:
                if c in cols:
                    cols.insert(0, cols.pop(cols.index(c)))
            df = df[cols]

            # Caminho de salvamento
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Planilha Excel", "*.xlsx")],
                title="Salvar relatório em Excel"
            )
            if not filepath:
                return

            # Exporta
            df.to_excel(filepath, index=False, engine="openpyxl")
            messagebox.showinfo("Sucesso", f"Relatório exportado com sucesso para:\n{filepath}")

            # Abre o arquivo automaticamente (Windows / macOS / Linux)
            if os.name == "nt":
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.run(["open" if os.sys.platform == "darwin" else "xdg-open", filepath])

        except Exception as e:
            self.configure(cursor="")
            messagebox.showerror("Erro", f"Ocorreu um erro ao exportar: {e}")


# <<< PATCH


# --- Novo Frame de Configurações ---
class ConfigFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app

        ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)

        ctk.CTkButton(self, text="Alternar Tema (Claro/Escuro)", command=self.toggle_theme).pack(pady=10)

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        novo_modo = "dark" if current_mode == "Light" else "light"
        ctk.set_appearance_mode(novo_modo)

        # Salva no banco
        try:
            import db
            db.execute_query(
                """
                INSERT INTO preferencias_usuarios (username, tema)
                VALUES (%s, %s)
                ON CONFLICT (username) DO UPDATE SET tema = EXCLUDED.tema
                """,
                (self.app.current_user, novo_modo)
            )
            print(f"[INFO] Tema '{novo_modo}' salvo para {self.app.current_user}")
        except Exception as e:
            print(f"[ERRO] Falha ao salvar tema: {e}")

# --- Helper: olhinho dentro do CTkEntry de senha ---
# ==== helper: olhinho dentro do CTkEntry de senha ====
class _PasswordEyeToggle:
    def __init__(self, entry: ctk.CTkEntry, emoji_show="👁", emoji_hide="🙈"):
        self.entry = entry
        self.emoji_show = emoji_show
        self.emoji_hide = emoji_hide
        self.visible = False

        # botão "flutuando" dentro do entry
        self.btn = ctk.CTkButton(
            entry,                     # importante: dentro do Entry
            text=self.emoji_show,      # mostra o emoji
            width=28, height=22,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#e6e6e6",
            text_color=("black", "white"),
            command=self.toggle,
        )
        entry.bind("<Configure>", lambda e: self._place())
        self._place()

    def _place(self):
        # ancora no canto direito dentro do entry
        try:
            self.btn.place(in_=self.entry, relx=1.0, x=-6, rely=0.5, anchor="e")
        except Exception:
            self.btn.place(relx=1.0, x=-6, rely=0.5, anchor="e")

    def toggle(self):
        self.visible = not self.visible
        self.entry.configure(show="" if self.visible else "*")
        self.btn.configure(text=self.emoji_hide if self.visible else self.emoji_show)

def add_password_eye(entry: ctk.CTkEntry):
    """Adiciona um botão-olho dentro do CTkEntry de senha."""
    # container absoluto para sobrepor o botão no canto direito
    container = ctk.CTkFrame(entry.master, fg_color="transparent")
    container.place(in_=entry, relx=1.0, x=-3, rely=0.5, anchor="e")

    state = {"visible": False}

    def toggle():
        state["visible"] = not state["visible"]
        entry.configure(show="" if state["visible"] else "*")
        btn.configure(text="🙈" if state["visible"] else "👁️")

    btn = ctk.CTkButton(
        container, text="👁️", width=20, height=20,
        command=toggle, fg_color="transparent",
        hover_color="#e0e0e0", text_color=("black", "white")
    )
    btn.pack()
    return btn


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master, on_login, obrigatorio: bool = False):
        super().__init__(master)
        self.on_login = on_login
        self.obrigatorio = obrigatorio
        self._showing_password = False

        self.title("DOMMA — Acesso ao Sistema")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Return>", lambda _e: self.try_login())
        self.configure(fg_color="#FFFFFF")

        # ── Faixa do topo (brand) ──
        brand = ctk.CTkFrame(self, fg_color=THEME["sidebar_bg"],
                              corner_radius=0, height=120)
        brand.pack(fill="x")
        brand.pack_propagate(False)
        ctk.CTkLabel(brand, text="DOMMA",
                     font=ctk.CTkFont(size=34, weight="bold"),
                     text_color="#FFFFFF").pack(pady=(22, 2))
        ctk.CTkLabel(brand, text="Controle de Estoque  ·  T.I.",
                     font=ctk.CTkFont(size=11), text_color="#475569").pack()

        # ── Formulário ──
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=36, pady=(22, 0))
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Usuário", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=THEME["text_secondary"], anchor="w"
                     ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.user_entry = ctk.CTkEntry(
            form, height=42, font=ctk.CTkFont(size=14),
            placeholder_text="Seu usuário",
            border_color=THEME["border"], border_width=1,
        )
        self.user_entry.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(form, text="Senha", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=THEME["text_secondary"], anchor="w"
                     ).grid(row=2, column=0, sticky="w", pady=(14, 5))

        pass_row = ctk.CTkFrame(form, fg_color="transparent")
        pass_row.grid(row=3, column=0, sticky="ew")
        pass_row.grid_columnconfigure(0, weight=1)

        self.pass_entry = ctk.CTkEntry(
            pass_row, show="*", height=42, font=ctk.CTkFont(size=14),
            placeholder_text="Sua senha",
            border_color=THEME["border"], border_width=1,
        )
        self.pass_entry.grid(row=0, column=0, sticky="ew")

        self.eye_btn = ctk.CTkButton(
            pass_row, text="👁", width=42, height=42,
            fg_color=THEME["border"], hover_color="#CBD5E1",
            text_color=THEME["text_secondary"], corner_radius=8,
            command=self._toggle_password_eye,
        )
        self.eye_btn.grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            form, text="Entrar no Sistema", height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME["primary"], hover_color=THEME["primary_hover"],
            corner_radius=10, command=self.try_login,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(20, 0))

        ctk.CTkLabel(
            form, text="DOMMA Incorporações  ·  T.I.",
            font=ctk.CTkFont(size=10), text_color="#CBD5E1"
        ).grid(row=5, column=0, columnspan=2, pady=(16, 0))

        # centraliza na tela após renderizar
        self.after(10, self._center_and_focus)

    def _center_and_focus(self):
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        # garante tamanho mínimo confortável
        w = max(w, 440)
        h = max(h, 480)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = max(40, (sh - h) // 2 - 40)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.lift()
        self.focus_force()
        self.user_entry.focus_set()

    def _toggle_password_eye(self):
    # segurança caso a flag não exista
        if not hasattr(self, "_showing_password"):
            self._showing_password = False

        self._showing_password = not self._showing_password
        self.pass_entry.configure(show="" if self._showing_password else "*")
        self.eye_btn.configure(
            text="🙈" if self._showing_password else "👁",
            text_color=("black", "#FFFFFF")
        )

    def _on_close(self):
        if self.obrigatorio and not getattr(self.master, "current_user", None):
            try:
                self.master.destroy()
            finally:
                self.destroy()
        else:
            self.destroy()

    def try_login(self):
        from tkinter import messagebox
        user = self.user_entry.get().strip()
        senha = self.pass_entry.get().strip()

        if not user or not senha:
            messagebox.showwarning("Erro", "Preencha usuário e senha.")
            return

        if callable(self.on_login):
            self.on_login(user)

        self.destroy()

# ------------------------------
# APLICATIVO PRINCIPAL (refatorado com Sidebar + Header)
# ------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Estado inicial ---
        self.current_user = None

        # --- Configuração da Janela ---
        self.title("Controle de Estoque T.I. — Painel")
        self.geometry("1200x750")

        # --- Preparação do Banco de Dados ---
        db_setup_notebooks()

        try:
            db.setup_database()
        except Exception as e:
            messagebox.showwarning(
                "Banco Indisponível",
                f"Não foi possível conectar ao banco de dados PostgreSQL.\n\n"
                f"Verifique o arquivo .env e a conectividade com o Supabase.\n\n"
                f"Erro: {e}\n\nAlgumas funções estarão indisponíveis."
            )

        try:
            db.ensure_notebook_schema()
        except Exception as e:
            print(f"[WARN] Falha ao garantir schema de notebooks: {e}")

        # --- Estrutura principal ---
        self.sidebar = ctk.CTkFrame(self, width=248, corner_radius=0,
                                     fg_color=THEME["sidebar_bg"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main_area = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_area.pack(side="right", expand=True, fill="both")

        # Header
        self.header = ctk.CTkFrame(self.main_area, height=58, corner_radius=0,
                                    fg_color=THEME["header_bg"],
                                    border_width=1, border_color=THEME["border"])
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        # Área de conteúdo
        self.content = ctk.CTkFrame(self.main_area, fg_color=THEME["content_bg"], corner_radius=0)
        self.content.pack(expand=True, fill="both")

        # === SIDEBAR: Marca ===
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(22, 6))
        ctk.CTkLabel(brand_frame, text="DOMMA",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#FFFFFF", anchor="w").pack(fill="x")
        ctk.CTkLabel(brand_frame, text="Controle de Estoque T.I.",
                     font=ctk.CTkFont(size=11), text_color="#475569", anchor="w").pack(fill="x")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=THEME["sidebar_sep"]
                     ).pack(fill="x", padx=18, pady=(12, 10))

        # === SIDEBAR: Navegação ===
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10)

        def _nav_btn(icon, label, cmd):
            return ctk.CTkButton(
                nav_frame, text=f"  {icon}   {label}", anchor="w",
                fg_color="transparent",
                text_color=THEME["sidebar_text"],
                hover_color=THEME["sidebar_item_hover"],
                font=ctk.CTkFont(size=13),
                height=44, corner_radius=8,
                command=cmd, width=224,
            )

        self.btn_notebooks = _nav_btn("💻", "Notebooks",     self.show_notebooks)
        self.btn_notebooks.pack(pady=2, fill="x")

        self.btn_obras = _nav_btn("🏗️", "Obras",            self.show_obras)
        self.btn_obras.pack(pady=2, fill="x")

        self.btn_relat = _nav_btn("📊", "Relatórios",        self.show_relat)
        self.btn_relat.pack(pady=2, fill="x")

        self.btn_config = _nav_btn("⚙️", "Configurações",   self.show_config)
        self.btn_config.pack(pady=2, fill="x")

        self._nav_btns = [self.btn_notebooks, self.btn_obras, self.btn_relat, self.btn_config]
        self._nav_labels = ["Notebooks", "Obras", "Relatórios", "Configurações"]

        # === SIDEBAR: Rodapé ===
        # Info do usuário logado
        self.user_card = ctk.CTkFrame(self.sidebar, fg_color="#1E293B", corner_radius=10)
        self.user_card.pack(side="bottom", fill="x", padx=10, pady=(4, 10))
        ctk.CTkLabel(self.user_card, text="⬤", text_color="#22C55E",
                     font=ctk.CTkFont(size=9)).pack(side="left", padx=(12, 6), pady=12)
        self.user_name_label = ctk.CTkLabel(
            self.user_card, text="Não logado",
            font=ctk.CTkFont(size=12), text_color="#64748B", anchor="w"
        )
        self.user_name_label.pack(side="left", pady=12)

        # Sair
        self.btn_sair = ctk.CTkButton(
            self.sidebar, text="  ⏻   Sair", anchor="w",
            fg_color="transparent", text_color="#EF4444",
            hover_color="#1E293B",
            font=ctk.CTkFont(size=13), height=44, corner_radius=8,
            command=self.quit, width=224,
        )
        self.btn_sair.pack(side="bottom", padx=10, pady=(0, 2), fill="x")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=THEME["sidebar_sep"]
                     ).pack(side="bottom", fill="x", padx=18, pady=(0, 6))

        # === HEADER: Título + usuário ===
        self.title_label = ctk.CTkLabel(
            self.header, text="Notebooks",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=THEME["text"], anchor="w"
        )
        self.title_label.pack(side="left", padx=20)

        # --- Frames principais ---
        self.current_frame = None
        # GARANTE que os callbacks existam como atributos antes de passar para o frame
        if not hasattr(self, "open_notebook_detail"):
            def _open_detail_proxy(placa_id=None):
                try:
                    if placa_id is None:
                        AtivoDetailWindow(self, None, on_close_callback=self.on_notebook_window_close)
                    else:
                        AtivoDetailWindow(self, placa_id, on_close_callback=self.on_notebook_window_close)
                except Exception as e:
                    print(f"[ERRO] Falha ao abrir detalhes do notebook: {e}")
            self.open_notebook_detail = _open_detail_proxy

        if not hasattr(self, "on_notebook_window_close"):
            def _on_close_proxy():
                try:
                    self.notebooks_frame.update_notebook_grid()
                except Exception as e:
                    print(f"[ERRO] Falha ao atualizar notebooks após fechar janela: {e}")
            self.on_notebook_window_close = _on_close_proxy

        if not hasattr(self, "open_obra_window"):
            def _open_obra_proxy(obra_nome):
                try:
                    win = ObraWindow(self, obra_nome)
                    try:
                        db.start_realtime_listener(self.refresh_estoque_list)  # callback só roda quando há evento
                    except Exception as e:
                        print(f"[WARN] Listener desativado: {e}")
                except Exception as e:
                    print(f"[ERRO] abrir obra: {e}")
            self.open_obra_window = _open_obra_proxy

        self.notebooks_frame = NotebooksFrame(self.content, open_detail_callback=self.open_notebook_detail)
        self.obras_frame = ObrasSelectionFrame(self.content, open_obra_callback=self.open_obra_window)
        self.relat_frame = RelatoriosFrame(self)                 # precisa de acesso a current_user
        self.config_frame = ConfigFrame(self.content, app=self)  # tem o ThemeSwitcher dentro

        # View inicial
        self.show_notebooks()

        # ---- Controle de habilitar/desabilitar UI até logar ----
        def set_ui_enabled(enabled: bool):
            state = "normal" if enabled else "disabled"
            for btn in [self.btn_notebooks, self.btn_obras, self.btn_relat, self.btn_config]:
                btn.configure(state=state)
        self.set_ui_enabled = set_ui_enabled

        # começa desabilitado e obriga login
        self.set_ui_enabled(False)
        self.after_idle(lambda: self.abrir_login(obrigatorio=True))

    # --- Métodos de troca de view ---
    def _trocar_frame(self, novo_frame, titulo="Painel", nav_btn=None):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.current_frame = novo_frame
        self.current_frame.pack(expand=True, fill="both")
        try:
            self.title_label.configure(text=titulo)
        except Exception:
            pass
        if nav_btn:
            self._set_nav_active(nav_btn)

    def _set_nav_active(self, btn_ativo):
        for b in getattr(self, "_nav_btns", []):
            b.configure(fg_color="transparent", text_color=THEME["sidebar_text"],
                        hover_color=THEME["sidebar_item_hover"])
        try:
            btn_ativo.configure(fg_color=THEME["sidebar_active_bg"],
                                text_color=THEME["sidebar_active_text"],
                                hover_color=THEME["primary_hover"])
        except Exception:
            pass

    def show_notebooks(self):
        self._trocar_frame(self.notebooks_frame, "Notebooks", self.btn_notebooks)

    def show_obras(self):
        self._trocar_frame(self.obras_frame, "Obras", self.btn_obras)

    def set_logged_user(self, username):
        self.current_user = username
        # carrega tema do Postgres
        tema = db.get_user_theme(username)
        if tema:
            ctk.set_appearance_mode(tema)

        # (carregar tema do usuário, se já faz isso aqui)


        # Busca tema salvo para esse usuário
        try:
            result = db.fetch_all(
                "SELECT tema FROM preferencias_usuarios WHERE username = %s",
                (username,)
            )
            if result and result[0]['tema']:
                tema = result[0]['tema']
                ctk.set_appearance_mode(tema)
                print(f"[INFO] Tema carregado para {username}: {tema}")
        except Exception as e:
            print(f"[ERRO] Falha ao carregar tema: {e}")

        # Reabilita UI após login
        self.set_ui_enabled(True)

    def show_relat(self):
        self._trocar_frame(self.relat_frame, "Relatórios", self.btn_relat)

    def show_config(self):
        self._trocar_frame(self.config_frame, "Configurações", self.btn_config)

    def _set_sidebar_locked(self, locked: bool = True):
        """Habilita/desabilita os botões da sidebar."""
        state = "disabled" if locked else "normal"
        for b in (self.btn_notebooks, self.btn_obras, self.btn_relat, self.btn_config):
            try:
                b.configure(state=state)
            except Exception:
                pass

    def _on_login_ok(self, username: str):
        self.current_user = username
        try:
            self.user_name_label.configure(text=username, text_color="#F1F5F9")
        except Exception:
            pass
        try:
            tema_salvo = db.get_user_theme(username)
            if tema_salvo:
                ctk.set_appearance_mode(tema_salvo)
        except Exception as e:
            print(f"[ERRO] Falha ao carregar tema: {e}")
        self._set_sidebar_locked(False)
        self.show_notebooks()


    def abrir_login(self, obrigatorio: bool = False):
        """Abre a tela de login e bloqueia a interface até autenticar."""
        # Evita abrir se já está logado
        if self.current_user:
            return

        self._set_sidebar_locked(True)

        win = LoginWindow(self, on_login=self._on_login_ok, obrigatorio=obrigatorio)

        # Centraliza
        self.update_idletasks()
        w, h = 360, 240
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

        self.wait_window(win)  # Bloqueia até fechar login

        # Se o usuário não logou e o login era obrigatório, o app fecha no próprio LoginWindow
        if not self.current_user and obrigatorio:
            self.destroy()



def open_notebook_detail(self, placa_id=None):
    """Abre a janela de detalhes do notebook e registra callback para atualizar a grade."""
    try:
        if placa_id is None:
            AtivoDetailWindow(self, None, on_close_callback=self.on_notebook_window_close)
        else:
            AtivoDetailWindow(self, placa_id, on_close_callback=self.on_notebook_window_close)
    except Exception as e:
        print(f"[ERRO] Falha ao abrir detalhes do notebook: {e}")

def on_notebook_window_close(self):
    """Atualiza a grid de notebooks quando a janela de detalhe for fechada."""
    try:
        self.notebooks_frame.update_notebook_grid()
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar notebooks após fechar janela: {e}")

def open_obra_window(self, obra_nome):
    """Abre a janela de detalhes da obra selecionada e tenta ligar o listener em tempo real."""
    try:
        win = ObraWindow(self, obra_nome)
        try:
            print(f"[INFO] Listener em tempo real iniciado para a obra: {obra_nome}")
        except Exception as e:
            print(f"[ERRO] Não foi possível iniciar listener de tempo real: {e}")
    except Exception as e:
        print(f"[ERRO] Falha ao abrir obra '{obra_nome}': {e}")


    def salvar_tema(self, tema: str):
        """Aplica e persiste o tema escolhido para o usuário logado."""
        if not getattr(self, "current_user", None):
            messagebox.showwarning("Tema", "Faça login para salvar sua preferência de tema.")
            return
        try:
            db.upsert_user_theme(self.current_user, tema)
            ctk.set_appearance_mode(tema)  # aplica imediatamente
            print(f"[INFO] Tema '{tema}' salvo para {self.current_user}")
        except Exception as e:
            print(f"[ERRO] Falha ao salvar tema: {e}")

    def force_login_on_start(self):
        """Abre a janela de login de forma modal e bloqueia a UI até autenticar."""
        # trava a sidebar
        try:
            self._lock_sidebar(True)
        except Exception:
            for b in (self.btn_notebooks, self.btn_obras, self.btn_relat, self.btn_config):
                try: b.configure(state="disabled")
                except: pass

        # cria a janela de login
        win = LoginWindow(self, on_login=self.set_logged_user)

        # centraliza em relação ao app
        self.update_idletasks()
        w, h = 360, 240
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

        # bloqueia até o login fechar
        self.wait_window(win)

        # se fechou sem logar, o LoginWindow já destruiu o app; se ainda estiver aqui:
        if not getattr(self, "current_user", None):
            return

        # libera a sidebar
        try:
            self._lock_sidebar(False)
        except Exception:
            for b in (self.btn_notebooks, self.btn_obras, self.btn_relat, self.btn_config):
                try: b.configure(state="normal")
                except: pass

def _set_sidebar_locked(self, locked: bool):
    state = "disabled" if locked else "normal"
    for b in (self.btn_notebooks, self.btn_obras, self.btn_relat, self.btn_config):
        try:
            b.configure(state=state)
        except Exception:
            pass

def _on_login_ok(self, username: str):
    # define usuário logado, aplica preferências, etc.
    self.set_logged_user(username)
    self._set_sidebar_locked(False)
            

class ThemeSwitcher(ctk.CTkFrame):
    def __init__(self, master, on_change):
        super().__init__(master)
        self.on_change = on_change
        ctk.CTkLabel(self, text="Tema do aplicativo").pack(anchor="w", pady=(0, 6))
        self.var = ctk.StringVar(value=ctk.get_appearance_mode().lower())
        ctk.CTkRadioButton(self, text="Claro", variable=self.var, value="light",
                           command=self._apply).pack(side="left", padx=6)
        ctk.CTkRadioButton(self, text="Escuro", variable=self.var, value="dark",
                           command=self._apply).pack(side="left", padx=6)

    def _apply(self):
        self.on_change(self.var.get())    

# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    app = App() 
    app.mainloop()
