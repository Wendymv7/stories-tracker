import streamlit as st
from supabase import create_client

# 1. INICIALIZAR LA BASE DE DATOS (Evita el error rojo)
if "db" not in st.session_state:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(url, key)
    except Exception as e:
        st.error(f"Fallo crítico al conectar con Supabase: {e}")
        st.stop()

# 2. SISTEMA DE LOGIN PARA LAS 4 ADMINISTRADORAS
def check_login():
    st.sidebar.title("🔐 Acceso Admin")
    
    # Si la sesión está activa, mostrar nombre y botón de salir
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Conectada como: {st.session_state.admin_name}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        return True

    # Si no hay sesión, mostrar el formulario
    with st.sidebar.form("login_form"):
        usuario = st.text_input("Usuario (ej: eli.lopez)")
        clave = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        try:
            # Consultamos exactamente tu tabla 'administradores'
            res = st.session_state.db.table("administradores")\
                .select("*").eq("email", usuario).eq("password", clave).execute()
            
            if len(res.data) > 0:
                st.session_state.logged_in = True
                st.session_state.admin_name = res.data[0]["nombre"]
                st.rerun()
            else:
                st.sidebar.error("Usuario o contraseña incorrectos")
        except Exception as e:
            st.sidebar.error(f"Error al verificar en la base de datos: {e}")
            
    return False

# 3. EJECUCIÓN DEL PANEL PRINCIPAL (Solo visible si hay login)
if check_login():
    st.title("📊 Stories Tracker - Panel de Control")
    st.write(f"¡Bienvenida al sistema, {st.session_state.admin_name}!")
    
    st.markdown("---")
    
    # Aquí puedes hacer una prueba rápida para ver si lee a las 6 niñas
    st.subheader("Niñas en la base de datos:")
    try:
        ninas = st.session_state.db.table("participantes").select("*").execute()
        if len(ninas.data) > 0:
            st.dataframe(ninas.data) # Muestra la tabla en pantalla
        else:
            st.info("La tabla de participantes está vacía. Necesitas sincronizar el Excel.")
    except Exception as e:
        st.error(f"Error al cargar participantes: {e}")
        
else:
    st.info("👈 Por favor, ingresa tus credenciales en el menú lateral para ver el panel de control.")
