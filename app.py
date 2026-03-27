import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Santas Tracker", page_icon="🛡️", layout="wide")

# 2. CONEXIÓN
if "db" not in st.session_state:
    try:
        url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(url, key)
    except Exception as e:
        st.error(f"Error DB: {e}"); st.stop()

db = st.session_state.db

# 3. SEGURIDAD
def check_login():
    st.sidebar.title("🔐 Acceso Admin")
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Hola: {st.session_state.admin_name}")
        if st.sidebar.button("Salir"):
            st.session_state.logged_in = False; st.rerun()
        return True
    with st.sidebar.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", u).eq("password", p).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.admin_name = True, res.data[0]["nombre"]
                st.rerun()
            else: st.sidebar.error("Error de acceso")
    return False

# 4. CRM Y MULTAS
def mostrar_crm():
    st.header("👥 CRM Santas")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas: st.info("Sin registros"); return

    # Buscador corregido
    nombres = [c["nombre"] for c in chicas]
    sel = st.selectbox("Nombre:", ["-- Seleccionar --"] + nombres)
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        st.markdown(f"## ⚠️ Disciplina: {p['nombre']}")
        an, ad = p.get('amarillas_normales', 0) or 0, p.get('amarillas_directas', 0) or 0
        m = ((an // 3) * 100000) + (ad * 100000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", an); c2.metric("🟥 Directas", ad); c3.metric("💸 Multa", f"${m:,.0f}")

        with st.expander("➕ Registrar Falta"):
            tipo = st.radio("Causa:", ["Normal", "Directa"])
            if st.button("Guardar"):
                db.table("participantes").update({
                    "amarillas_normales": an + 1 if tipo == "Normal" else an,
                    "amarillas_directas": ad + 1 if tipo == "Directa" else ad
                }).eq("id", p["id"]).execute(); st.rerun()

        st.markdown("---")
        with st.form("ficha"):
            st.subheader("Ficha Técnica")
            col1, col2 = st.columns(2)
            n = col1.text_input("Nombre", value=p["nombre"])
            h = col2.text_input("Instagram", value=p["handle"])
            cor = col1
