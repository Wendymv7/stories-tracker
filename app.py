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
        
        # --- NUEVO: SISTEMA DE MULTAS Y AMONESTACIONES ---
        st.markdown(f"### ⚠️ Panel Disciplinario: {perfil['nombre']}")
        
        # Lógica matemática de las multas
        amarillas_norm = perfil.get('amarillas_normales', 0)
        amarillas_dir = perfil.get('amarillas_directas', 0)
        
        # Cada 3 normales = 100k, Cada 1 directa = 100k
        multa_por_normales = (amarillas_norm // 3) * 100000
        multa_por_directas = amarillas_dir * 100000
        multa_total = multa_por_normales + multa_por_directas
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("🟨 Amarillas Normales", amarillas_norm)
        col_m2.metric("🟥 Amarillas Directas", amarillas_dir)
        col_m3.metric("💸 Multa Acumulada", f"${multa_total:,.0f} COP")
        
        if multa_total > 0:
            st.error(f"🚨 ALERTA: Esta jugadora tiene una multa pendiente de ${multa_total:,.0f} COP.")
            
        with st.expander("➕ Agregar Amonestación"):
            tipo_falta = st.radio("Tipo de Falta:", ["Amarilla Normal (Llegada tarde, uniforme, etc)", "Amarilla Directa (Inasistencia a evento, retiro sin permiso)"])
            if st.button("Registrar Falta"):
                if "Normal" in tipo_falta:
                    db.table("participantes").update({"amarillas_normales": amarillas_norm + 1}).eq("id", perfil["id"]).execute()
                else:
                    db.table("participantes").update({"amarillas_directas": amarillas_dir + 1}).eq("id", perfil["id"]).execute()
                st.success("Falta registrada. Actualizando...")
                st.rerun()
                
        st.markdown("---")
        # --- FIN DEL NUEVO SISTEMA DE MULTAS ---
        
        with st.form(f"form_editar_{perfil['id']}"):
            st.subheader(f"Ficha Técnica")
            
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre Completo", value=perfil.get("nombre", ""))
                handle = st.text_input("Instagram Handle", value=perfil.get("handle", ""))
                tiktok = st.text_input("Usuario de TikTok", value=perfil.get("tiktok", "") or "")
                cedula = st.text_input("Documento de Identidad", value=perfil.get("cedula", "") or "")
                correo = st.text_input("Correo Electrónico", value=perfil.get("correo", "") or "")
                
            with col2:
                rol_actual = perfil.get("rol")
                opciones_rol = ["futbolista", "modelo"]
                index_rol = opciones_rol.index(rol_actual) if rol_actual in opciones_rol else 0
                    
                rol = st.selectbox("Rol en Santas", opciones_rol, index=index_rol)
                profesion = st.text_input("Profesión / Ocupación", value=perfil.get("profesion", "") or "")
                tipo_sangre = st.text_input("Tipo de Sangre", value=perfil.get("tipo_sangre", "") or "")
                direccion = st.text_input("Dirección", value=perfil.get("direccion", "") or "")
                
            col3, col4 = st.columns(2)
            with col3:
                fnac_val = perfil.get("fecha_nacimiento")
                fecha_nac = st.date_input("Fecha de Nacimiento", value=datetime.strptime(fnac_val, "%Y-%m-%d") if fnac_val else None)
            with col4:
                fing_val = perfil.get("fecha_ingreso_santas")
                fecha_ingreso = st.date_input("Fecha de Ingreso", value=datetime.strptime(fing_val, "%Y-%m-%d") if fing_val else None)

            guardar = st.form_submit_button("💾 Guardar Perfil", type="primary")
            
            if guardar:
                fnac_str = fecha_nac.strftime("%Y-%m-%d") if fecha_nac else None
                fing_str = fecha_ingreso.strftime("%Y-%m-%d") if fecha_ingreso else None
                
                datos = {
                    "nombre": nombre, "handle": handle, "tiktok": tiktok, "cedula": cedula,
                    "correo": correo, "rol": rol, "profesion": profesion, "tipo_sangre": tipo_sangre,
                    "direccion": direccion, "fecha_nacimiento": fnac_str, "fecha_ingreso_santas": fing_str
                }
                try:
                    db.table("participantes").update(datos).eq("id", perfil["id"]).execute()
                    st.success("Perfil actualizado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# 5. ESTRUCTURA PRINCIPAL DE LA APLICACIÓN
if check_login():
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", ["📱 Panel de Validación", "👥 CRM Perfiles Santas"])
    
    if menu == "📱 Panel de Validación":
        st.title("📊 Stories Tracker - Panel Principal")
        st.write("Verificación de cumplimiento de etiquetas en Instagram.")
        
        # Aquí prepararemos el botón para iniciar el robot
        if st.button("🚀 Iniciar Escaneo de Historias", type="primary"):
            st.info("El motor de validación se conectará en el siguiente paso. ¡Prepárate!")
        
    elif menu == "👥 CRM Perfiles Santas":
        mostrar_crm()
else:
    st.info("👈 Ingresa credenciales.")
