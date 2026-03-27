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
    st.header("👥 CRM - Gestión de Santas")
    
    res = db.table("participantes").select("*").order("nombre").execute()
    participantes = res.data
    
    if not participantes:
        st.info("No hay perfiles registrados.")
        return

    check_cumpleanos(participantes)
    
    # BUSCADOR MEJORADO: Streamlit permite escribir dentro del selectbox para filtrar
    st.markdown("### 🔍 Buscar Jugadora o Modelo")
    nombre_buscado = st.selectbox(
        "Escribe el nombre para filtrar rápidamente:",
        options=[p["nombre"] for p in participantes],
        index=None,
        placeholder="Ej: Manuela..."
    )
    
    if nombre_buscado:
        perfil = next(p for p in participantes if p["nombre"] == nombre_buscado)
        
        # --- PANEL DISCIPLINARIO (Multas) ---
        st.info(f"Ficha de {perfil['nombre']}")
        # ... (aquí va tu código de amarillas que ya funcionaba)

# 5. PANEL DE VALIDACIÓN (Aquí verás lo que hace el robot)
if menu == "📱 Panel de Validación":
    st.title("📊 Stories Tracker - Resultados del Robot")
    
    # Consultar los últimos registros guardados por el robot
    res_logs = db.table("registros").select("*, participantes(nombre, handle)").order("created_at", desc=True).limit(50).execute()
    
    if res_logs.data:
        st.write("Últimas validaciones realizadas por **juan_verificador**:")
        for log in res_logs.data:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"👤 {log['participantes']['nombre']}")
            col2.write(f"📅 {log['fecha']}")
            if log['status'] == "cumplido":
                col3.success("✅ Cumplió")
            else:
                col3.error("❌ Incumplió")
    else:
        st.warning("Aún no hay datos de escaneo. El robot no ha corrido o no encontró historias.")
