import streamlit as st
from datetime import datetime

def load_historial():
    # Asegúrate de que 'desde' sea un string tipo 'YYYY-MM-DD'
    desde = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Consulta ajustada a tu nueva tabla 'registros'
        # Nota: Usamos .select("*, participantes(nombre, handle)") para traer los datos de la niña
        query = st.session_state.db.table("registros")\
            .select("*, participantes(nombre, handle)")\
            .gte("fecha", desde)\
            .order("fecha", desc=True)\
            .execute()
        
        return query.data
    except Exception as e:
        st.error(f"Error en la base de datos: {e}")
        return []

# Para el conteo de la línea 121 (el que fallaba en tu imagen):
historial = load_historial()
pend_count = len([r for r in historial if r.get("status") == "pendiente"]) 
# Cambié "enviado" por "pendiente" porque así lo definiste en tu SQL (check status)
