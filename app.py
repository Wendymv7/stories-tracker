import streamlit as st
from supabase import create_client
from datetime import datetime

# Configuración básica de la página
st.set_page_config(page_title="Santas Tracker & CRM", page_icon="🛡️", layout="wide")

# 1. INICIALIZAR LA BASE DE DATOS
if "db" not in st.session_state:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(url, key)
    except Exception as e:
        st.error(f"Fallo crítico al conectar con Supabase: {e}")
        st.stop()

db = st.session_state.db

# 2. SISTEMA DE LOGIN PARA ADMINISTRADORAS
def check_login():
    st.sidebar.title("🔐 Acceso Admin Santas")
    
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Conectada como: {st.session_state.admin_name}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        return True

    with st.sidebar.form("login_form"):
        usuario = st.text_input("Usuario (ej: eli.lopez)")
        clave = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        try:
            res = db.table("administradores").select("*").eq("email", usuario).eq("password", clave).execute()
            if len(res.data) > 0:
                st.session_state.logged_in = True
                st.session_state.admin_name = res.data[0]["nombre"]
                st.rerun()
            else:
                st.sidebar.error("Usuario o contraseña incorrectos")
        except Exception as e:
            st.sidebar.error(f"Error al verificar en la base de datos: {e}")
            
    return False

# 3. LÓGICA DEL CRM Y PERFILES
def check_cumpleanos(participantes):
    hoy = datetime.now()
    cumpleaneras = []
    
    for p in participantes:
        if p.get("fecha_nacimiento"):
            try:
                # Convertir el string de la BD a un objeto fecha de Python
                fecha_nac = datetime.strptime(p["fecha_nacimiento"], "%Y-%m-%d")
                if fecha_nac.month == hoy.month and fecha_nac.day == hoy.day:
                    cumpleaneras.append(p["nombre"])
            except:
                pass
                
    if cumpleaneras:
        nombres = ", ".join(cumpleaneras)
        st.balloons()
        st.warning(f"🎉 **¡ALERTA DE CUMPLEAÑOS!** Hoy celebramos a: **{nombres}**. ¡No olviden felicitarla!")

def mostrar_crm():
    st.header("👥 CRM - Perfiles Santas")
    
    # Consultar todas las niñas ordenadas alfabéticamente
    res = db.table("participantes").select("*").order("nombre").execute()
    participantes = res.data
    
    if not participantes:
        st.info("No hay perfiles registrados en la base de datos.")
        return

    # Verificar si hay cumpleaños hoy
    check_cumpleanos(participantes)
    
    st.markdown("---")
    
    # Selector para buscar a la niña
    nombres = [p["nombre"] for p in participantes]
    seleccion = st.selectbox("🔍 Buscar perfil para visualizar o editar:", ["-- Seleccionar una cuenta --"] + nombres)
    
    if seleccion != "-- Seleccionar una cuenta --":
        # Extraer los datos de la niña seleccionada
        perfil = next(p for p in participantes if p["nombre"] == seleccion)
        
        with st.form(f"form_editar_{perfil['id']}"):
            st.subheader(f"Ficha Técnica: {perfil['nombre']}")
            
            # Formulario a dos columnas para mejor diseño
            col1, col2 = st.columns(2)
            
            with col1:
                nombre = st.text_input("Nombre Completo", value=perfil.get("nombre", ""))
                handle = st.text_input("Instagram Handle", value=perfil.get("handle", ""))
                tiktok = st.text_input("Usuario de TikTok", value=perfil.get("tiktok", "") or "")
                cedula = st.text_input("Documento de Identidad (Cédula)", value=perfil.get("cedula", "") or "")
                correo = st.text_input("Correo Electrónico", value=perfil.get("correo", "") or "")
                
            with col2:
                # Lógica para preseleccionar el rol correcto
                rol_actual = perfil.get("rol")
                opciones_rol = ["futbolista", "modelo"]
                index_rol = opciones_rol.index(rol_actual) if rol_actual in opciones_rol else 0
                    
                rol = st.selectbox("Rol en Santas", opciones_rol, index=index_rol)
                profesion = st.text
