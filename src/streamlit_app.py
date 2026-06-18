import io
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

# ── injeta secrets do Streamlit Cloud como env vars (para db.py) ──────────────
try:
    for _k in ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_PORT"]:
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass  # rodando local — credenciais vêm do .env

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import db
import db_notebooks

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DOMMA · Estoque",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
STATUS_COLORS = {
    "Disponível":          "#22C55E",
    "Em Uso":              "#3B82F6",
    "Em Manutenção":       "#F59E0B",
    "Quebrado":            "#EF4444",
    "Alocado":             "#3B82F6",
    "Triagem":             "#8B5CF6",
    "Assistência Técnica": "#F97316",
    "Verificar":           "#EAB308",
    "Não definido":        "#94A3B8",
}

_OBRAS_FALLBACK = [
    "Domma", "Seleto Primavera", "Unic São Gonçalo",
    "PRIME Caxias", "LIV Primavera", "Reserva Equitativa",
    "Encantado", "Seleto Inhaúma",
]

NAV_ITEMS = {
    "obras":         ("🏗️", "Obras"),
    "notebooks":     ("💻", "Notebooks"),
    "relatorios":    ("📊", "Relatórios"),
    "configuracoes": ("⚙️", "Configurações"),
}

# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Tipografia global ── */
html, body, [class*="css"], .stMarkdown, .stText, p, span, div, label, h1, h2, h3 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── Remove chrome do Streamlit ── */
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] {
    display: none !important;
}
header[data-testid="stHeader"] { display: none !important; }

/* ── Conteúdo principal ── */
.main .block-container {
    padding: 2.2rem 2.8rem 3rem !important;
    max-width: 1280px !important;
}

/* ══ SIDEBAR ══════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: 1px solid #1E293B !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
    opacity: 1 !important;
    margin: 6px 0 !important;
}

/* Nav — botão inativo */
[data-testid="stSidebar"] .stButton > button {
    font-family: 'Inter', sans-serif !important;
    background: transparent !important;
    border: none !important;
    color: #94A3B8 !important;
    text-align: left !important;
    width: 100% !important;
    height: 42px !important;
    padding: 0 14px !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    letter-spacing: 0.1px !important;
    transition: background 0.15s, color 0.15s !important;
    margin: 1px 0 !important;
    justify-content: flex-start !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1E293B !important;
    color: #F1F5F9 !important;
}
[data-testid="stSidebar"] .stButton > button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* ══ MÉTRICAS (KPI cards) ═══════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 24px !important;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
    transition: box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 16px rgba(15,23,42,.09) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 30px !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    color: #64748B !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ══ BOTÕES ═══════════════════════════════════════════════════════════════ */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    letter-spacing: 0.1px !important;
    transition: all 0.15s !important;
}
[data-testid="baseButton-primary"],
.stButton > button[kind="primary"] {
    font-weight: 600 !important;
}
[data-testid="stFormSubmitButton"] > button {
    font-family: 'Inter', sans-serif !important;
    border-radius: 8px !important;
}

/* ══ TABS ═════════════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 2px solid #E2E8F0 !important;
    gap: 0 !important;
    padding-bottom: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    color: #64748B !important;
    border: none !important;
    border-radius: 0 !important;
    letter-spacing: 0.1px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #2563EB !important;
    border-bottom: 2px solid #2563EB !important;
    margin-bottom: -2px !important;
}

/* ══ DATAFRAMES ══════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] thead th {
    font-family: 'Inter', sans-serif !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
    color: #64748B !important;
    background: #F8FAFC !important;
}
[data-testid="stDataFrame"] tbody td {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}

/* ══ FORMULÁRIOS ═════════════════════════════════════════════════════════ */
[data-testid="stForm"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 14px !important;
    padding: 24px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,.05) !important;
}
[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(15,23,42,.04) !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}

/* ══ INPUTS ══════════════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    font-family: 'Inter', sans-serif !important;
    border-radius: 8px !important;
    border-color: #E2E8F0 !important;
    font-size: 14px !important;
    color: #0F172A !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
}
[data-testid="stSelectbox"] > div > div {
    font-family: 'Inter', sans-serif !important;
    border-radius: 8px !important;
    border-color: #E2E8F0 !important;
    font-size: 14px !important;
}
label[data-testid="stWidgetLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #374151 !important;
}

/* ══ ALERTAS ═════════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
}

/* ══ DIVISORES ═══════════════════════════════════════════════════════════ */
hr { border-color: #E2E8F0 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "user":              None,
    "page":              "obras",
    "obra_atual":        None,
    # flags de modal
    "show_add_item":     False,
    "show_edit_item":    False,
    "show_baixa":        False,
    "show_devolver":     False,
    "show_transferir":   False,
    "show_delete_item":  False,
    "item_edit":         None,
    "item_baixa":        None,
    "item_devolver":     None,
    "item_transferir":   None,
    "item_delete":       None,
    "nb_edit_id":        None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_obras():
    try:
        return db.get_obras() or _OBRAS_FALLBACK
    except Exception:
        return _OBRAS_FALLBACK


def badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#94A3B8")
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'font-size:12px;font-weight:600;color:white;background:{color}">{status}</span>'
    )


def fmt_dt(v) -> str:
    if not v:
        return ""
    try:
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", ""))
        return v.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(v)


def excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()


def page_header(title: str, subtitle: str = "", breadcrumb: str = ""):
    bc = (f'<div style="font-size:11.5px;font-weight:500;color:#94A3B8;'
          f'letter-spacing:.3px;margin-bottom:6px;text-transform:uppercase">'
          f'{breadcrumb}</div>') if breadcrumb else ""
    sub = (f'<p style="font-size:14px;color:#64748B;margin:4px 0 0;font-weight:400">'
           f'{subtitle}</p>') if subtitle else ""
    st.markdown(
        f'<div style="margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid #E2E8F0">'
        f'{bc}'
        f'<h1 style="font-size:22px;font-weight:700;color:#0F172A;margin:0;'
        f'font-family:Inter,sans-serif;letter-spacing:-.3px">{title}</h1>'
        f'{sub}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, accent: str = "#2563EB", icon: str = "") -> str:
    return (
        f'<div style="background:#FFF;border:1px solid #E2E8F0;border-radius:12px;'
        f'border-top:3px solid {accent};padding:20px 24px;'
        f'box-shadow:0 1px 3px rgba(15,23,42,.05);height:100%">'
        f'<div style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;'
        f'letter-spacing:.5px;margin-bottom:10px">{icon} {label}</div>'
        f'<div style="font-size:30px;font-weight:700;color:#0F172A;'
        f'font-family:Inter,sans-serif;line-height:1">{value}</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    # fundo cinza para a página inteira
    st.markdown("""
    <style>
    .main { background: #F1F5F9 !important; }
    .main .block-container { display:flex; align-items:center; min-height:90vh;
        justify-content:center; padding:2rem !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        # card container
        st.markdown("""
        <div style="background:#FFF;border-radius:20px;overflow:hidden;
                    box-shadow:0 8px 40px rgba(15,23,42,.12);margin-top:40px">
            <div style="background:#0F172A;padding:40px 44px 32px;text-align:center">
                <div style="font-size:36px;font-weight:800;color:#FFF;
                            letter-spacing:4px;font-family:Inter,sans-serif">DOMMA</div>
                <div style="font-size:12px;color:#475569;margin-top:8px;
                            font-weight:500;letter-spacing:.5px">
                    CONTROLE DE ESTOQUE · T.I.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # form dentro de um card branco (continuação visual)
        st.markdown("""
        <div style="background:#FFF;border-radius:0 0 20px 20px;
                    box-shadow:0 8px 40px rgba(15,23,42,.12);padding:28px 40px 32px;
                    margin-top:-4px">
        </div>
        <style>
        /* Remove borda padrão do form nesta tela */
        [data-testid="stForm"] { background:transparent!important;
            border:none!important; box-shadow:none!important; padding:0!important; }
        </style>
        """, unsafe_allow_html=True)

        with st.form("login", clear_on_submit=False):
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha    = st.text_input("Senha",   placeholder="Digite sua senha",
                                     type="password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            ok = st.form_submit_button("Entrar no Sistema",
                                       use_container_width=True, type="primary")
            if ok:
                if not username.strip() or not senha.strip():
                    st.error("Preencha usuário e senha.")
                else:
                    st.session_state.user = username.strip()
                    st.rerun()

        st.markdown(
            "<p style='text-align:center;color:#CBD5E1;font-size:11px;"
            "margin-top:16px;font-weight:500'>DOMMA Incorporações · T.I.</p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
_NAV_ACTIVE_STYLE = (
    "background:#2563EB;border-radius:8px;"
    "height:42px;display:flex;align-items:center;padding:0 14px;"
    "color:#FFF;font-family:'Inter',sans-serif;"
    "font-size:13.5px;font-weight:600;letter-spacing:.1px;"
    "margin:1px 0;gap:8px;cursor:default"
)

def show_sidebar():
    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────────────────
        st.markdown("""
        <div style="padding:28px 16px 16px">
            <div style="font-size:22px;font-weight:800;color:#FFFFFF;
                        letter-spacing:3px;font-family:'Inter',sans-serif">DOMMA</div>
            <div style="font-size:10.5px;font-weight:500;color:#334155;
                        margin-top:3px;letter-spacing:.5px;text-transform:uppercase">
                Controle de Estoque
            </div>
        </div>
        <hr style="border:none;border-top:1px solid #1E293B;margin:0 0 8px">
        """, unsafe_allow_html=True)

        # ── Nav ─────────────────────────────────────────────────────────────
        for page_id, (icon, label) in NAV_ITEMS.items():
            if st.session_state.page == page_id:
                st.markdown(
                    f'<div style="{_NAV_ACTIVE_STYLE}">'
                    f'<span style="font-size:15px">{icon}</span>'
                    f'<span>{label}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"{icon}  {label}", key=f"nav_{page_id}",
                             use_container_width=True):
                    st.session_state.page = page_id
                    st.session_state.obra_atual = None
                    st.rerun()

        # ── User card ────────────────────────────────────────────────────────
        st.markdown("""
        <div style="position:absolute;bottom:0;left:0;right:0;
                    padding:0 8px 16px;border-top:1px solid #1E293B;padding-top:12px">
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='flex:1;min-height:60px'></div>", unsafe_allow_html=True)
        st.markdown("<hr style='border:none;border-top:1px solid #1E293B;margin:8px 0'>",
                    unsafe_allow_html=True)
        # avatar + nome
        initials = (st.session_state.user or "?")[:2].upper()
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:6px 8px">'
            f'<div style="width:32px;height:32px;border-radius:50%;background:#2563EB;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:12px;font-weight:700;color:#FFF;flex-shrink:0">{initials}</div>'
            f'<div><div style="font-size:13px;color:#E2E8F0;font-weight:600;'
            f'font-family:Inter,sans-serif">{st.session_state.user}</div>'
            f'<div style="font-size:10.5px;color:#475569;font-weight:400">T.I. · DOMMA</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("""
        <style>
        /* Botão de sair — estilo vermelho suave */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:last-of-type
            .stButton > button {
            color: #F87171 !important;
            margin-top: 4px !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:last-of-type
            .stButton > button:hover {
            background: rgba(239,68,68,.12) !important;
            color: #FCA5A5 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("🚪  Sair da conta", key="logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: OBRAS (seleção)
# ══════════════════════════════════════════════════════════════════════════════
def show_obras():
    page_header("Obras", "Selecione uma obra para gerenciar o estoque")
    obras = get_obras()

    cols = st.columns(4)
    for i, obra in enumerate(obras):
        with cols[i % 4]:
            try:
                oid    = db.get_obra_id(obra)
                stats  = db.get_dashboard_stats(oid)
                total  = int(stats.get("total_items") or 0)
                em_uso = int(stats.get("em_uso") or 0)
            except Exception:
                total = em_uso = 0

            # Calcula cor do accent ciclicamente
            accents = ["#2563EB","#8B5CF6","#10B981","#F59E0B",
                       "#EF4444","#06B6D4","#EC4899","#6366F1"]
            accent = accents[i % len(accents)]

            st.markdown(
                f'<div style="background:#FFF;border:1px solid #E2E8F0;border-radius:14px;'
                f'border-left:4px solid {accent};padding:20px 20px 16px;margin-bottom:4px;'
                f'box-shadow:0 1px 4px rgba(15,23,42,.05);">'
                f'<div style="font-size:22px;margin-bottom:10px">🏗️</div>'
                f'<div style="font-size:15px;font-weight:700;color:#0F172A;'
                f'font-family:Inter,sans-serif;line-height:1.3">{obra}</div>'
                f'<div style="display:flex;gap:12px;margin-top:10px">'
                f'<span style="font-size:11px;color:#64748B;font-weight:500">'
                f'<b style="color:#0F172A">{total}</b> itens</span>'
                f'<span style="font-size:11px;color:#64748B;font-weight:500">'
                f'<b style="color:#3B82F6">{em_uso}</b> em uso</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Acessar →", key=f"obra_{i}", use_container_width=True):
                st.session_state.obra_atual = obra
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: DETALHE DA OBRA (tabs)
# ══════════════════════════════════════════════════════════════════════════════
def show_obra_detail():
    obra_nome = st.session_state.obra_atual

    c1, c2 = st.columns([1, 12])
    with c1:
        if st.button("← Voltar", key="btn_voltar_obra"):
            st.session_state.obra_atual = None
            st.rerun()
    with c2:
        page_header(f"🏗️ {obra_nome}", breadcrumb="Obras")

    try:
        obra_id = db.get_obra_id(obra_nome)
    except Exception as e:
        st.error(f"Erro ao carregar obra: {e}")
        return

    t_dash, t_est, t_hist, t_rel = st.tabs(
        ["📊 Dashboard", "📦 Estoque", "📋 Histórico", "📈 Relatórios"]
    )
    with t_dash: _obra_dashboard(obra_id)
    with t_est:  _obra_estoque(obra_id, obra_nome)
    with t_hist: _obra_historico(obra_id)
    with t_rel:  _obra_relatorios(obra_id, obra_nome)


# ── Dashboard ──────────────────────────────────────────────────────────────
def _obra_dashboard(obra_id: int):
    try:
        stats = db.get_dashboard_stats(obra_id)
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    total      = int(stats.get("total_items")   or 0)
    em_uso     = int(stats.get("em_uso")         or 0)
    disponivel = int(stats.get("disponivel")     or 0)
    manutencao = int(stats.get("em_manutencao")  or 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Total de Itens", total, "#2563EB", "📦"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Em Uso", em_uso, "#3B82F6", "🔵"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Disponível", disponivel, "#22C55E", "🟢"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Manutenção", manutencao, "#EF4444", "🔴"),
                    unsafe_allow_html=True)

    try:
        import plotly.express as px
        items = db.get_items_by_obra(obra_id)
        if items:
            df = pd.DataFrame(items)
            if "categoria_nome" in df.columns and "qtd_total" in df.columns:
                cat = (
                    df.groupby("categoria_nome")["qtd_total"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(8)
                    .reset_index()
                )
                cat.columns = ["Categoria", "Quantidade"]
                if not cat.empty:
                    st.markdown("---")
                    st.markdown("#### Itens por Categoria")
                    fig = px.bar(
                        cat, x="Quantidade", y="Categoria",
                        orientation="h",
                        color_discrete_sequence=["#2563EB"],
                    )
                    fig.update_layout(
                        height=300,
                        plot_bgcolor="white", paper_bgcolor="white",
                        showlegend=False,
                        margin=dict(l=0, r=0, t=8, b=0),
                    )
                    fig.update_yaxes(categoryorder="total ascending")
                    st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass


# ── Estoque ────────────────────────────────────────────────────────────────
def _obra_estoque(obra_id: int, obra_nome: str):
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        search = st.text_input("🔍 Buscar", placeholder="Nome, categoria, série...",
                               key=f"srch_{obra_id}", label_visibility="collapsed")
    with sc2:
        if st.button("➕ Adicionar Item", type="primary", use_container_width=True,
                     key="btn_add_item"):
            st.session_state.show_add_item  = not st.session_state.show_add_item
            st.session_state.show_edit_item = False
            st.session_state.item_edit      = None

    # ── Formulário novo item ─────────────────────────────────────────────────
    if st.session_state.show_add_item:
        with st.expander("📝 Novo Item", expanded=True):
            _item_form(obra_id)

    # ── Carrega tabela ───────────────────────────────────────────────────────
    try:
        items = db.get_items_by_obra(obra_id, search_term=search or "")
    except Exception as e:
        st.error(f"Erro ao carregar itens: {e}")
        return

    if not items:
        st.info("Nenhum item cadastrado nesta obra.")
        return

    df = pd.DataFrame(items)
    col_map = {
        "categoria_nome": "Categoria",
        "nome":           "Nome",
        "numero_serie":   "N° Série",
        "qtd_estoque":    "Estoque",
        "qtd_em_uso":     "Em Uso",
        "qtd_total":      "Total",
        "status":         "Status",
        "condicao":       "Condição",
    }
    existing = [c for c in col_map if c in df.columns]
    st.dataframe(
        df[existing].rename(columns=col_map),
        use_container_width=True,
        hide_index=True,
    )

    # ── Ações ────────────────────────────────────────────────────────────────
    st.markdown("#### Ações")
    opts = {
        f"{r.get('categoria_nome','')} › {r.get('nome','')}  (id {r.get('id')})": r
        for r in items
    }
    sel_label = st.selectbox("Selecionar item", list(opts.keys()),
                             key=f"sel_{obra_id}", label_visibility="collapsed")
    sel = opts[sel_label]

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        if st.button("✏️ Editar", key="act_edit", use_container_width=True):
            st.session_state.item_edit      = sel
            st.session_state.show_edit_item = True
            st.session_state.show_add_item  = False
    with a2:
        if st.button("⬇️ Dar Baixa", key="act_baixa", use_container_width=True):
            st.session_state.item_baixa  = sel
            st.session_state.show_baixa  = True
    with a3:
        if st.button("↩️ Devolver", key="act_dev", use_container_width=True):
            st.session_state.item_devolver  = sel
            st.session_state.show_devolver  = True
    with a4:
        if st.button("🔄 Transferir", key="act_transf", use_container_width=True):
            st.session_state.item_transferir  = sel
            st.session_state.show_transferir  = True
    with a5:
        if st.button("🗑️ Excluir", key="act_del", use_container_width=True):
            st.session_state.item_delete      = sel
            st.session_state.show_delete_item = True

    # ── Formulário edição ────────────────────────────────────────────────────
    if st.session_state.show_edit_item and st.session_state.item_edit:
        with st.expander("✏️ Editar Item", expanded=True):
            _item_form(obra_id, st.session_state.item_edit)

    # ── Modais de ação ───────────────────────────────────────────────────────
    _modal_baixa()
    _modal_devolver()
    _modal_transferir(obra_nome)
    _modal_excluir_item()


def _item_form(obra_id: int, item_data: dict | None = None):
    is_edit  = item_data is not None
    form_key = f"item_{'edit' if is_edit else 'new'}_{obra_id}_{id(item_data)}"

    try:
        cats     = db.get_categorias()
        cat_nms  = [c["nome"] for c in cats]
        cat_map  = {c["nome"]: c["id"] for c in cats}
    except Exception:
        cat_nms, cat_map = [], {}

    with st.form(form_key, clear_on_submit=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            default_cat = item_data.get("categoria_nome", cat_nms[0] if cat_nms else "") if is_edit else (cat_nms[0] if cat_nms else "")
            ci = cat_nms.index(default_cat) if default_cat in cat_nms else 0
            categoria = st.selectbox("Categoria *", cat_nms, index=ci)
        with r1c2:
            nome = st.text_input("Nome do Item *",
                                 value=item_data.get("nome", "") if is_edit else "")

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            numero_serie = st.text_input("Número de Série",
                                         value=item_data.get("numero_serie", "") if is_edit else "")
        with r2c2:
            conds  = ["Novo", "Usado", "Com defeito"]
            def_c  = item_data.get("condicao", "Novo") if is_edit else "Novo"
            ci_c   = conds.index(def_c) if def_c in conds else 0
            condicao = st.selectbox("Condição", conds, index=ci_c)

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            qtd_uso = st.number_input("Qtd. Em Uso", min_value=0,
                                       value=int(item_data.get("qtd_em_uso", 0)) if is_edit else 0)
        with r3c2:
            qtd_est = st.number_input("Qtd. Em Estoque", min_value=0,
                                       value=int(item_data.get("qtd_estoque", 0)) if is_edit else 0)

        sts_opts = ["Disponível", "Em Uso", "Em Manutenção", "Quebrado"]
        def_s    = item_data.get("status", "Disponível") if is_edit else "Disponível"
        si       = sts_opts.index(def_s) if def_s in sts_opts else 0
        status   = st.selectbox("Status", sts_opts, index=si)

        obs = st.text_area("Observação",
                           value=item_data.get("observacao", "") if is_edit else "")

        fc1, fc2 = st.columns(2)
        with fc1:
            save_btn   = st.form_submit_button("💾 Salvar", type="primary",
                                               use_container_width=True)
        with fc2:
            cancel_btn = st.form_submit_button("Cancelar", use_container_width=True)

        if save_btn:
            if not nome.strip():
                st.error("Nome é obrigatório.")
            else:
                data = {
                    "obra_id":      obra_id,
                    "categoria_id": cat_map.get(categoria),
                    "nome":         nome.strip(),
                    "numero_serie": numero_serie.strip() or None,
                    "qtd_uso":      qtd_uso,
                    "qtd_estoque":  qtd_est,
                    "qtd_total":    qtd_uso + qtd_est,
                    "condicao":     condicao,
                    "status":       status,
                    "observacao":   obs.strip() or None,
                }
                try:
                    if is_edit:
                        data["id"] = item_data["id"]
                        db.update_item(data, resp=st.session_state.user)
                    else:
                        db.add_item(data, resp=st.session_state.user)
                    st.success("✅ Item salvo com sucesso!")
                    st.session_state.show_add_item  = False
                    st.session_state.show_edit_item = False
                    st.session_state.item_edit      = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        if cancel_btn:
            st.session_state.show_add_item  = False
            st.session_state.show_edit_item = False
            st.session_state.item_edit      = None
            st.rerun()


def _modal_baixa():
    if not (st.session_state.show_baixa and st.session_state.item_baixa):
        return
    item = st.session_state.item_baixa
    with st.expander(f"⬇️ Dar Baixa — {item.get('nome')}", expanded=True):
        with st.form("f_baixa", clear_on_submit=True):
            qtd = st.number_input("Quantidade", min_value=1,
                                  max_value=max(1, int(item.get("qtd_estoque") or 1)))
            obs = st.text_area("Observação")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("Confirmar", type="primary",
                                         use_container_width=True):
                    ok, msg = db.dar_baixa_item(
                        item["id"], qtd, obs, st.session_state.user
                    )
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.session_state.show_baixa  = False
                        st.session_state.item_baixa  = None
                        st.rerun()
            with c2:
                if st.form_submit_button("Cancelar", use_container_width=True):
                    st.session_state.show_baixa = False
                    st.rerun()


def _modal_devolver():
    if not (st.session_state.show_devolver and st.session_state.item_devolver):
        return
    item = st.session_state.item_devolver
    with st.expander(f"↩️ Devolver — {item.get('nome')}", expanded=True):
        with st.form("f_dev", clear_on_submit=True):
            qtd = st.number_input("Quantidade", min_value=1,
                                  max_value=max(1, int(item.get("qtd_em_uso") or 1)))
            obs = st.text_area("Observação")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("Confirmar", type="primary",
                                         use_container_width=True):
                    ok, msg = db.devolver_item(
                        item["id"], qtd, obs, st.session_state.user
                    )
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.session_state.show_devolver  = False
                        st.session_state.item_devolver  = None
                        st.rerun()
            with c2:
                if st.form_submit_button("Cancelar", use_container_width=True):
                    st.session_state.show_devolver = False
                    st.rerun()


def _modal_transferir(obra_nome: str):
    if not (st.session_state.show_transferir and st.session_state.item_transferir):
        return
    item        = st.session_state.item_transferir
    outras_obras = [o for o in get_obras() if o != obra_nome]
    with st.expander(f"🔄 Transferir — {item.get('nome')}", expanded=True):
        with st.form("f_transf", clear_on_submit=True):
            destino = st.selectbox("Obra destino", outras_obras)
            qtd     = st.number_input("Quantidade", min_value=1,
                                       max_value=max(1, int(item.get("qtd_estoque") or 1)))
            obs     = st.text_area("Observação")
            c1, c2  = st.columns(2)
            with c1:
                if st.form_submit_button("Confirmar", type="primary",
                                         use_container_width=True):
                    try:
                        dest_id = db.get_obra_id(destino)
                        ok, msg = db.transfer_item(
                            item["id"], dest_id, destino,
                            qtd, obs, st.session_state.user,
                        )
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.session_state.show_transferir  = False
                            st.session_state.item_transferir  = None
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
            with c2:
                if st.form_submit_button("Cancelar", use_container_width=True):
                    st.session_state.show_transferir = False
                    st.rerun()


def _modal_excluir_item():
    if not (st.session_state.show_delete_item and st.session_state.item_delete):
        return
    item = st.session_state.item_delete
    st.warning(
        f"⚠️ Excluir **{item.get('nome')}**? "
        "Todo o histórico de movimentações também será removido."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Confirmar Exclusão", type="primary",
                     use_container_width=True, key="confirm_del"):
            ok, msg = db.delete_item(item["id"])
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.session_state.show_delete_item = False
                st.session_state.item_delete      = None
                st.rerun()
    with c2:
        if st.button("Cancelar", use_container_width=True, key="cancel_del"):
            st.session_state.show_delete_item = False
            st.rerun()


# ── Histórico da Obra ─────────────────────────────────────────────────────
def _obra_historico(obra_id: int):
    try:
        items = db.get_items_by_obra(obra_id)
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    if not items:
        st.info("Nenhum item encontrado.")
        return

    all_mov: list[dict] = []
    for item in items:
        try:
            for m in db.get_movimentacoes_do_item(item["id"], limit=100):
                m["_item"]      = item.get("nome", "")
                m["_categoria"] = item.get("categoria_nome", "")
                all_mov.append(m)
        except Exception:
            pass

    if not all_mov:
        st.info("Nenhuma movimentação registrada.")
        return

    df = pd.DataFrame(all_mov)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y %H:%M")

    col_map = {
        "data":        "Data",
        "_item":       "Item",
        "_categoria":  "Categoria",
        "tipo":        "Tipo",
        "quantidade":  "Qtd",
        "responsavel": "Responsável",
        "observacao":  "Observação",
    }
    existing = [c for c in col_map if c in df.columns]
    st.dataframe(
        df[existing].rename(columns=col_map).sort_values("Data", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


# ── Relatórios da Obra ────────────────────────────────────────────────────
def _obra_relatorios(obra_id: int, obra_nome: str):
    st.markdown("#### Exportar Movimentações por Período")
    c1, c2 = st.columns(2)
    with c1:
        ini = st.date_input("Data inicial", value=date.today().replace(day=1))
    with c2:
        fim = st.date_input("Data final",   value=date.today())

    if st.button("🔍 Carregar", type="primary"):
        try:
            movs = db.get_movimentacoes_por_periodo(obra_id, ini, fim)
        except Exception as e:
            st.error(f"Erro: {e}")
            return

        if not movs:
            st.info("Nenhuma movimentação no período.")
            return

        df = pd.DataFrame(movs)
        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y %H:%M")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Baixar Excel",
            data=excel_bytes(df),
            file_name=f"relatorio_{obra_nome}_{ini}_{fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: NOTEBOOKS
# ══════════════════════════════════════════════════════════════════════════════
def show_notebooks():
    page_header("💻 Notebooks", "Inventário de notebooks e equipamentos T.I.")

    db_notebooks.setup()

    fc1, fc2, fc3, fc4 = st.columns([2, 2, 3, 1])
    with fc1:
        sit_opts   = ["Todos", "Disponível", "Alocado", "Triagem",
                      "Assistência Técnica", "Verificar"]
        filt_sit   = st.selectbox("Status", sit_opts, key="nb_sit")
    with fc2:
        obra_opts  = ["Todos"] + get_obras()
        filt_obra  = st.selectbox("Obra", obra_opts, key="nb_obra")
    with fc3:
        busca      = st.text_input("🔍", placeholder="Buscar placa, usuário...",
                                   key="nb_search", label_visibility="collapsed")
    with fc4:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        if st.button("➕ Novo", type="primary", use_container_width=True):
            st.session_state.nb_edit_id = "__NEW__"

    # Formulário
    if st.session_state.nb_edit_id:
        pid   = st.session_state.nb_edit_id
        title = "Novo Notebook" if pid == "__NEW__" else f"Editar: {pid}"
        with st.expander(f"📝 {title}", expanded=True):
            _notebook_form(None if pid == "__NEW__" else pid)

    # Tabela
    try:
        nbs = db_notebooks.get_all(
            situacao=None if filt_sit  == "Todos" else filt_sit,
            obra    =None if filt_obra == "Todos" else filt_obra,
            search  =busca or None,
        )
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    if not nbs:
        st.info("Nenhum notebook encontrado.")
        return

    df = pd.DataFrame(nbs)
    col_map = {
        "placa_id":       "Placa",
        "usuario_atual":  "Usuário Atual",
        "situacao":       "Status",
        "obra":           "Obra",
        "setor":          "Setor",
        "cargo":          "Cargo",
        "numero_serie":   "N° Série",
    }
    existing = [c for c in col_map if c in df.columns]
    st.dataframe(
        df[existing].rename(columns=col_map),
        use_container_width=True,
        hide_index=True,
    )

    # Editar selecionado
    st.markdown("#### Editar Notebook")
    sel_nb = st.selectbox("Selecionar", df["placa_id"].tolist(),
                          key="nb_sel", label_visibility="collapsed")
    b1, _ = st.columns([1, 5])
    with b1:
        if st.button("✏️ Editar selecionado", key="nb_edit_btn"):
            st.session_state.nb_edit_id = sel_nb
            st.rerun()

    # Exportar
    st.markdown("---")
    st.download_button(
        "📥 Exportar Excel",
        data=excel_bytes(df[existing].rename(columns=col_map)),
        file_name=f"notebooks_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _notebook_form(placa_id: str | None):
    is_edit  = placa_id is not None
    existing = db_notebooks.get_one(placa_id) if is_edit else {}
    obras    = get_obras()
    sits     = ["Disponível", "Alocado", "Triagem",
                "Assistência Técnica", "Verificar", "Não definido"]

    with st.form(f"nb_{'e' if is_edit else 'n'}_{placa_id}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            placa   = st.text_input("Placa ID *",
                                    value=existing.get("placa_id", ""),
                                    disabled=is_edit)
        with c2:
            ns      = st.text_input("Número de Série",
                                    value=existing.get("numero_serie", ""))
        c3, c4 = st.columns(2)
        with c3:
            ua      = st.text_input("Usuário Atual",
                                    value=existing.get("usuario_atual", ""))
        with c4:
            uant    = st.text_input("Usuário Anterior",
                                    value=existing.get("usuario_anterior", ""))
        c5, c6 = st.columns(2)
        with c5:
            setor   = st.text_input("Setor",  value=existing.get("setor", ""))
        with c6:
            cargo   = st.text_input("Cargo",  value=existing.get("cargo", ""))
        c7, c8 = st.columns(2)
        with c7:
            sit_i   = sits.index(existing.get("situacao", "Disponível")) \
                      if existing.get("situacao") in sits else 0
            sit     = st.selectbox("Situação", sits, index=sit_i)
        with c8:
            ob_i    = obras.index(existing.get("obra", obras[0])) \
                      if existing.get("obra") in obras else 0
            obra    = st.selectbox("Obra", obras, index=ob_i)
        nf          = st.text_input("Nota Fiscal", value=existing.get("nota_fiscal", ""))
        obs         = st.text_area("Observação",   value=existing.get("observacao", ""))

        s1, s2 = st.columns(2)
        with s1:
            saved   = st.form_submit_button("💾 Salvar", type="primary",
                                            use_container_width=True)
        with s2:
            cancel  = st.form_submit_button("Cancelar", use_container_width=True)

        if saved:
            pid = placa_id if is_edit else placa.strip()
            if not pid:
                st.error("Placa ID é obrigatório.")
            else:
                db_notebooks.save({
                    "placa_id":         pid,
                    "numero_serie":     ns,
                    "usuario_atual":    ua,
                    "usuario_anterior": uant,
                    "setor":            setor,
                    "cargo":            cargo,
                    "situacao":         sit,
                    "obra":             obra,
                    "nota_fiscal":      nf,
                    "observacao":       obs,
                })
                st.success("✅ Notebook salvo!")
                st.session_state.nb_edit_id = None
                st.rerun()
        if cancel:
            st.session_state.nb_edit_id = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════════════
def show_relatorios():
    page_header("📊 Relatórios", f"Movimentações do usuário {st.session_state.user}")

    try:
        movs = db.get_movimentacoes_por_usuario(st.session_state.user)
    except Exception as e:
        st.error(f"Erro ao carregar movimentações: {e}")
        return

    if not movs:
        st.info("Nenhuma movimentação registrada pelo seu usuário.")
        return

    df = pd.DataFrame(movs)
    tipos = df["tipo"].value_counts() if "tipo" in df.columns else pd.Series(dtype=int)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total",         len(df))
    c2.metric("📦 Itens únicos",  int(df["item_id"].nunique()) if "item_id" in df.columns else 0)
    c3.metric("⬇️ Baixas",        int(tipos.get("Baixa", 0)))
    c4.metric("↩️ Devoluções",    int(tipos.get("Devolução", 0)))
    c5.metric("🔄 Transferências", int(tipos.get("Transferência (Saída)", 0)))

    st.markdown("---")

    try:
        import plotly.express as px

        g1, g2 = st.columns(2)
        with g1:
            if not tipos.empty:
                st.markdown("#### Por Tipo")
                fig = px.bar(
                    x=tipos.index, y=tipos.values,
                    color_discrete_sequence=["#2563EB"],
                    labels={"x": "", "y": "Qtd"},
                )
                fig.update_layout(height=260, plot_bgcolor="white",
                                  paper_bgcolor="white", showlegend=False,
                                  margin=dict(l=0, r=0, t=8, b=0))
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            if "item_id" in df.columns:
                st.markdown("#### Top 5 Itens")
                ic = df["item_id"].value_counts().head(5)
                labels = []
                for iid in ic.index:
                    try:
                        labels.append(db.get_item_nome(int(iid)) or str(iid))
                    except Exception:
                        labels.append(str(iid))
                fig2 = px.pie(values=ic.values, names=labels,
                              color_discrete_sequence=px.colors.qualitative.Bold)
                fig2.update_layout(height=260, margin=dict(l=0, r=0, t=8, b=0))
                st.plotly_chart(fig2, use_container_width=True)
    except Exception:
        pass

    st.markdown("#### Histórico Completo")
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "📥 Exportar Excel",
        data=excel_bytes(df),
        file_name=f"relatorio_{st.session_state.user}_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
def show_configuracoes():
    page_header("⚙️ Configurações", "Preferências do sistema")

    st.markdown("#### Conta")
    st.info(f"Logado como: **{st.session_state.user}**")

    st.markdown("---")
    st.markdown("#### Aparência")
    tema = st.radio("Tema", ["Claro", "Escuro"], horizontal=True)
    if st.button("Salvar preferência"):
        try:
            db.upsert_user_theme(
                st.session_state.user,
                "light" if tema == "Claro" else "dark",
            )
            st.success("Preferência salva!")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.markdown("---")
    st.caption("DOMMA Controle de Estoque v2.0 · Streamlit")


# ══════════════════════════════════════════════════════════════════════════════
# ROTEADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not st.session_state.user:
        show_login()
        return

    show_sidebar()

    page = st.session_state.page
    if page == "obras":
        if st.session_state.obra_atual:
            show_obra_detail()
        else:
            show_obras()
    elif page == "notebooks":
        show_notebooks()
    elif page == "relatorios":
        show_relatorios()
    elif page == "configuracoes":
        show_configuracoes()


if __name__ == "__main__":
    main()
