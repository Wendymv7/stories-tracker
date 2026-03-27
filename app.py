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
        st.error(f"Error de conexión: {e}")
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

# 4. VISTA DEL CRM
def mostrar_crm():
    st.header("👥 CRM - Gestión de Santas")
    res = db.table("participantes").select("*").order("nombre").execute()
    participantes = res.data
    if not participantes:
        st.info("No hay perfiles.")
        return

    check_cumpleanos(participantes)
    
    st.markdown("### 🔍 Buscar Perfil")
    nombres = [p["nombre"] for p in participantes]
    seleccion = st.selectbox("Escribe para buscar:", ["-- Seleccionar --"] + nombres)
    
    if seleccion != "-- Seleccionar --":
        perfil = next(p for p in participantes if p["nombre"] == seleccion)
        
        # --- SISTEMA DE MULTAS ---
        st.markdown(f"## ⚠️ Panel Disciplinario: {perfil['nombre']}")
        amarillas_n = perfil.get('amarillas_normales', 0) or 0
        amarillas_d = perfil.get('amarillas_directas', 0) or 0
        multa = ((amarillas_n // 3) * 100000) + (amarillas_d * 100000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", amarillas_n)
        c2.metric("🟥 Directas", amarillas_d)
        c3.metric("💸 Multa", f"${multa:,.0f} COP")

        with st.expander("➕ Registrar Amonestación"):
            tipo = st.radio("Tipo:", ["Normal", "Directa"])
            if st.button("Guardar Falta"):
                db.table("participantes").update({
                    "amarillas_normales": amarillas_n + 1 if tipo == "Normal" else amarillas_n,
                    "amarillas_directas": amarillas_d + 1 if tipo == "Directa" else amarillas_d
                }).eq("id", perfil["id"]).execute()
                st.rerun()

        st.markdown("---")
        with st.form("edit"):
            st.subheader("Ficha Técnica")
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre", value=perfil["nombre"])
            handle = col2.text_input("Instagram", value=perfil["handle"])
            if st.form_submit_button("Actualizar"):
                db.table("participantes").update({"nombre": nombre, "handle": handle}).eq("id", perfil["id"]).execute()
                st.rerun()

# 5. ESTRUCTURA PRINCIPAL (Solución al NameError)
if check_login():
    # El menú se define SOLO si hay login
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", ["📱 Panel de Validación", "👥 CRM Perfiles Santas"])
    
    if menu == "📱 Panel de Validación":
        st.title("📊 Stories Tracker - Resultados")
        try:
            res_logs = db.table("registros").select("*, participantes(nombre)").order("created_at", desc=True).limit(50).execute()
            if res_logs.data:
                for log in res_logs.data:
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"👤 **{log['participantes']['nombre']}**")
                    c2.write(f"📅 {log['fecha']}")
                    if log['status'] == "cumplido": c3.success("✅ OK")
                    else: c3.error("❌ NO")
                    st.divider()
            else:
                st.info("No hay datos de escaneo aún.")
        except:
            st.warning("Error cargando registros.")

    elif menu == "👥 CRM Perfiles Santas":
        mostrar_crm()
else:
    # Si no hay login, NO se intenta leer la variable 'menu'
    st.title("Bienvenida - Admin Santas")
    st.info("Ingresa tus credenciales a la izquierda.")
