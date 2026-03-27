import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Santas Tracker & CRM", page_icon="🛡️", layout="wide")

# 2. CONEXIÓN A BASE DE DATOS
if "db" not in st.session_state:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(url, key)
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}")
        st.stop()

db = st.session_state.db

# 3. FUNCIONES DE APOYO
def check_login():
    st.sidebar.title("🔐 Acceso Admin Santas")
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Conectada como: {st.session_state.admin_name}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        return True

    with st.sidebar.form("login_form"):
        usuario = st.text_input("Usuario (Email)")
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            try:
                res = db.table("administradores").select("*").eq("email", usuario).eq("password", clave).execute()
                if res.data:
                    st.session_state.logged_in = True
                    st.session_state.admin_name = res.data[0]["nombre"]
                    st.rerun()
                else:
                    st.sidebar.error("Credenciales incorrectas")
            except:
                st.sidebar.error("Error de base de datos")
    return False

def check_cumpleanos(participantes):
    hoy = datetime.now()
    cumples = [p["nombre"] for p in participantes if p.get("fecha_nacimiento") and 
               datetime.strptime(p["fecha_nacimiento"], "%Y-%m-%d").month == hoy.month and 
               datetime.strptime(p["fecha_nacimiento"], "%Y-%m-%d").day == hoy.day]
    if cumples:
        st.balloons()
        st.warning(f"🎉 **CUMPLEAÑOS HOY**: {', '.join(cumples)}")

def mostrar_crm():
    st.header("👥 CRM - Gestión de Santas")
    res = db.table("participantes").select("*").order("nombre").execute()
    participantes = res.data
    if not participantes:
        st.info("No hay perfiles registrados.")
        return

    check_cumpleanos(participantes)
    
    st.markdown("### 🔍 Buscar Perfil")
    nombres = [p["nombre"] for p in participantes]
    seleccion = st.selectbox("Nombre de la niña:",
