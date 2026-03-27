import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import urllib.parse

# 1. SETUP INICIAL
st.set_page_config(page_title="Santas Admin Pro", page_icon="⚽", layout="wide")

# LILA VIBRANTE (Estilo Santas FC)
st.markdown("""
<style>
    .stApp { background-color: #e0b0ff; }
    .stMetric { background-color: rgba(255,255,255,0.6); padding: 15px; border-radius: 15px; }
    h1, h2, h3 { color: #4a235a !important; font-weight: bold; }
    .stButton>button { border-radius: 20px; background-color: #8e44ad; color: white; border: none; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN
if "db" not in st.session_state:
    u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    st.session_state.db = create_client(u, k)
db = st.session_state.db

# 3. LOGIN
def check_login():
    st.sidebar.title("🔐 Acceso Admin")
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Hola: {st.session_state.admin_name}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.logged_in = False; st.rerun()
        return True
    with st.sidebar.form("login"):
        user = st.text_input("Usuario"); passw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", user).eq("password", passw).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.admin_name = True, res.data[0]["nombre"]
                st.rerun()
    return False

# 4. ALERTA CUMPLES Y WHATSAPP
def alerta_cumples(chicas):
    hoy = datetime.now()
    for c in chicas:
        if c.get("fecha_nacimiento"):
            try:
                fn = datetime.strptime(c["fecha_nacimiento"], "%Y-%m-%d")
                ca = fn.replace(year=hoy.year)
                if 0 <= (ca - hoy).days <= 2:
                    st.warning(f"🎂 **PROXIMO CUMPLE:** {c['nombre']} ({ca.strftime('%d/%m')})")
                    t = urllib.parse.quote(f"¡Hola equipo! 💜 El {ca.strftime('%d/%m')} es el cumple de {c['nombre']}. ¿Lista la publicidad? ⚽")
                    st.markdown(f'<a href="https://wa.me/?text={t}" target="_blank"><button style="background-color:#25
