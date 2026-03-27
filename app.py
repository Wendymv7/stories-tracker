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
        st.warning(f"🎉 **¡CUMPLEAÑOS HOY!**: {', '.join(cumples)}")

# 4. VISTA DEL CRM COMPLETA
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
    seleccion = st.selectbox("Escribe el nombre de la niña:", ["-- Seleccionar --"] + nombres)
    
    if seleccion != "-- Seleccionar --":
        perfil = next(p for p in participantes if p["nombre"] == seleccion)
        
        # --- PANEL DISCIPLINARIO (SISTEMA DE MULTAS) ---
        st.markdown(f"## ⚠️ Panel Disciplinario: {perfil['nombre']}")
        amarillas_n = perfil.get('amarillas_normales', 0) or 0
        amarillas_d = perfil.get('amarillas_directas', 0) or 0
        multa = ((amarillas_n // 3) * 100000) + (amarillas_d * 100000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Amarillas Normales", amarillas_n)
        c2.metric("🟥 Amarillas Directas", amarillas_d)
        c3.metric("💸 Multa Acumulada", f"${multa:,.0f} COP")

        with st.expander("➕ Registrar Amonestación"):
            tipo = st.radio("Causa:", ["Amarilla Normal (Retraso, Uniforme, Comida)", "Amarilla Directa (Inasistencia a evento, salida sin permiso)"])
            if st.button("Guardar Amonestación"):
                db.table("participantes").update({
                    "amarillas_normales": amarillas_n + 1 if "Normal" in tipo else amarillas_n,
                    "amarillas_directas": amarillas_d + 1 if "Directa" in tipo else amarillas_d
                }).eq("id", perfil["id"]).execute()
                st.success("Amonestación registrada.")
                st.rerun()

        st.markdown("---")
        
        # --- FICHA TÉCNICA COMPLETA ---
        with st.form("ficha_completa"):
            st.subheader(f"Ficha Técnica: {perfil['nombre']}")
            
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre Completo", value=perfil.get("nombre", ""))
                handle = st.text_input("Instagram Handle", value=perfil.get("handle", ""))
                tiktok = st.text_input("Usuario de TikTok", value=perfil.get("tiktok", "") or "")
                cedula = st.text_input("Documento de Identidad", value=perfil.get("cedula", "") or "")
                correo = st.text_input("Correo Electrónico", value=perfil.get("correo", "") or "")
                
            with col2:
                rol_actual = perfil.get("rol", "futbolista")
                rol = st.selectbox("Rol en Santas", ["futbolista", "modelo"], index=0 if rol_actual == "futbolista" else 1)
                profesion = st.text_input("Profesión / Ocupación", value=perfil.get("profesion", "") or "")
                tipo_sangre = st.text_input("Tipo de Sangre", value=perfil.get("tipo_sangre", "") or "")
                direccion = st.text_input("Dirección", value=perfil.get("direccion", "") or "")
                
            col3, col4 = st.columns(2)
