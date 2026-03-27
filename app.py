import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Santas Admin", page_icon="🛡️", layout="wide")

# 2. CONEXIÓN DB
if "db" not in st.session_state:
    try:
        u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(u, k)
    except Exception as e:
        st.error(f"Error DB: {e}"); st.stop()

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
        user = st.text_input("Usuario")
        passw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", user).eq("password", passw).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.admin_name = True, res.data[0]["nombre"]
                st.rerun()
            else: st.sidebar.error("Error de acceso")
    return False

# 4. CRM Y FICHA COMPLETA
def mostrar_crm():
    st.header("👥 CRM Santas")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas: st.info("Sin registros"); return

    sel = st.selectbox("Buscar niña:", ["-- Seleccionar --"] + [c["nombre"] for c in chicas])
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        st.markdown(f"## ⚠️ Disciplina: {p['nombre']}")
        
        an, ad = p.get('amarillas_normales', 0) or 0, p.get('amarillas_directas', 0) or 0
        multa = ((an // 3) * 100000) + (ad * 100000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", an); c2.metric("🟥 Directas", ad); c3.metric("💸 Multa", f"${multa:,.0f}")

        col_b1, col_b2 = st.columns(2)
        if col_b1.button("➕ Amarilla Normal"):
            db.table("participantes").update({"amarillas_normales": an + 1}).eq("id", p["id"]).execute(); st.rerun()
        if col_b2.button("➕ Amarilla Directa"):
            db.table("participantes").update({"amarillas_directas": ad + 1}).eq("id", p["id"]).execute(); st.rerun()

        st.divider()
        with st.form("ficha_extensa"):
            st.subheader(f"📝 Ficha Técnica Completa: {p['nombre']}")
            
            col_a, col_b = st.columns(2)
