import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. CONFIGURACIÓN E IMPORTACIONES (Siempre va primero)
st.set_page_config(page_title="Santas Tracker & CRM", page_icon="🛡️", layout="wide")

# 2. INICIALIZAR LA BASE DE DATOS
if "db" not in st.session_state:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(url, key)
    except Exception as e:
        st.error(f"Fallo crítico al conectar con Supabase: {e}")
        st.stop()

db = st.session_state.db

# 3. SISTEMA DE LOGIN PARA ADMINISTRADORAS
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

# 4. LÓGICA DEL CRM Y PERFILES
def check_cumpleanos(participantes):
    hoy = datetime.now()
    cumpleaneras = []
    
    for p in participantes:
        if p.get("fecha_nacimiento"):
            try:
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
    
    res = db.table("participantes").select("*").order("nombre").execute()
    participantes = res.data
    
    if not participantes:
        st.info("No hay perfiles registrados en la base de datos.")
        return

    check_cumpleanos(participantes)
    st.markdown("---")
    
    nombres = [p["nombre"] for p in participantes]
    seleccion = st.selectbox("🔍 Buscar perfil para visualizar o editar:", ["-- Seleccionar una cuenta --"] + nombres)
    
    if seleccion != "-- Seleccionar una cuenta --":
        perfil = next(p for p in participantes if p["nombre"] == seleccion)
        
        with st.form(f"form_editar_{perfil['id']}"):
            st.subheader(f"Ficha Técnica: {perfil['nombre']}")
            
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre Completo", value=perfil.get("nombre", ""))
                handle = st.text_input("Instagram Handle", value=perfil.get("handle", ""))
                tiktok = st.text_input("Usuario de TikTok", value=perfil.get("tiktok", "") or "")
                cedula = st.text_input("Documento de Identidad (Cédula)", value=perfil.get("cedula", "") or "")
                correo = st.text_input("Correo Electrónico", value=perfil.get("correo", "") or "")
                
            with col2:
                rol_actual = perfil.get("rol")
                opciones_rol = ["futbolista", "modelo"]
                index_rol = opciones_rol.index(rol_actual) if rol_actual in opciones_rol else 0
                    
                rol = st.selectbox("Rol en Santas", opciones_rol, index=index_rol)
                profesion = st.text_input("Profesión / Ocupación", value=perfil.get("profesion", "") or "")
                tipo_sangre = st.text_input("Tipo de Sangre", value=perfil.get("tipo_sangre", "") or "")
                direccion = st.text_input("Dirección de Residencia", value=perfil.get("direccion", "") or "")
                
            col3, col4 = st.columns(2)
            with col3:
                fnac_val = perfil.get("fecha_nacimiento")
                fecha_nac = st.date_input("Fecha de Nacimiento", 
                                          value=datetime.strptime(fnac_val, "%Y-%m-%d") if fnac_val else None)
            with col4:
                fing_val = perfil.get("fecha_ingreso_santas")
                fecha_ingreso = st.date_input("Fecha de Ingreso a Santas", 
                                              value=datetime.strptime(fing_val, "%Y-%m-%d") if fing_val else None)

            st.markdown("<br>", unsafe_allow_html=True)
            guardar = st.form_submit_button("💾 Guardar / Actualizar Perfil", type="primary")
            
            if guardar:
                fnac_str = fecha_nac.strftime("%Y-%m-%d") if fecha_nac else None
                fing_str = fecha_ingreso.strftime("%Y-%m-%d") if fecha_ingreso else None
                
                datos_actualizados = {
                    "nombre": nombre,
                    "handle": handle,
                    "tiktok": tiktok,
                    "cedula": cedula,
                    "correo": correo,
                    "rol": rol,
                    "profesion": profesion,
                    "tipo_sangre": tipo_sangre,
                    "direccion": direccion,
                    "fecha_nacimiento": fnac_str,
                    "fecha_ingreso_santas": fing_str
                }
                
                try:
                    db.table("participantes").update(datos_actualizados).eq("id", perfil["id"]).execute()
                    st.success("¡Perfil actualizado correctamente en la base de datos!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar los datos: {e}")

# 5. ESTRUCTURA PRINCIPAL DE LA APLICACIÓN
if check_login():
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación del Sistema", ["📱 Panel de Validación", "👥 CRM Perfiles Santas"])
    
    if menu == "📱 Panel de Validación":
        st.title("📊 Stories Tracker - Panel Principal")
        st.write("Bienvenida al centro de control. Aquí podrás verificar el cumplimiento de las etiquetas en Instagram.")
        
    elif menu == "👥 CRM Perfiles Santas":
        mostrar_crm()
else:
    st.info("👈 Por favor, ingresa tus credenciales en el menú lateral para acceder al sistema.")
