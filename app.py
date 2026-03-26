import streamlit as st
from supabase import create_client

# 1. Inicializar la conexión solo una vez
if "db" not in st.session_state:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        # Creamos el cliente y lo guardamos en el estado de la sesión
        st.session_state.db = create_client(url, key)
    except Exception as e:
        st.error(f"Fallo crítico al conectar con Supabase: {e}")
        st.stop()

# 2. Ahora ya puedes usar st.session_state.db en el resto del código
db = st.session_state.db
