import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP INICIAL
st.set_page_config(page_title="Santas Admin Pro", page_icon="💰", layout="wide")

# 2. CONEXIÓN A BASE DE DATOS
if "db" not in st.session_state:
    try:
        u = st.secrets["SUPABASE_URL"]
        k = st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(u, k)
    except Exception as e:
        st.error(f"Error conexión: {e}")
        st.stop()

db = st.session_state.db

# 3. SISTEMA DE LOGIN
def check_login():
    st.sidebar.title("🔐 Acceso Admin")
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Hola: {st.session_state.admin_name}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()
        return True
    
    with st.sidebar.form("login"):
        user = st.text_input("Usuario")
        passw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", user).eq("password", passw).execute()
            if res.data:
                st.session_state.logged_in = True
                st.session_state.admin_name = res.data[0]["nombre"]
                st.rerun()
            else:
                st.sidebar.error("Datos incorrectos")
    return False

# 4. MÓDULO CRM Y CONTABILIDAD
def mostrar_crm():
    st.header("👥 CRM Santas - Gestión Integral")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas:
        st.info("No hay registros")
        return

    sel = st.selectbox("Seleccionar niña:", ["-- Seleccionar --"] + [c["nombre"] for c in chicas])
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        
        # --- RESUMEN DE MULTAS ---
        an = p.get('amarillas_normales', 0) or 0
        ad = p.get('amarillas_directas', 0) or 0
        deuda_actual = ((an // 3) * 100000) + (ad * 100000)
        
        st.markdown(f"## ⚠️ Estado de Cuenta: {p['nombre']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Amarillas Normales", an)
        c2.metric("🟥 Amarillas Directas", ad)
        c3.metric("💸 DEUDA TOTAL", f"${deuda_actual:,.0f}", delta_color="inverse")

        st.divider()

        # --- GESTIÓN DISCIPLINARIA Y ABONOS ---
        col_f, col_p = st.columns(2)
        
        with col_f:
            st.subheader("➕ Registrar Sanción")
            tipo_f = st.radio("Tipo de falta:", ["Normal", "Directa"], horizontal=True)
            if st.button("Confirmar Falta"):
                db.table("participantes").update({
                    "amarillas_normales": an + 1 if tipo_f == "Normal" else an,
                    "amarillas_directas": ad + 1 if tipo_f == "Directa" else ad
                }).eq("id", p["id"]).execute()
                st.rerun()

        with col_p:
            st.subheader("💵 Registrar Abono")
            monto = st.number_input("Monto del abono ($):", min_value=0, step=100000)
            if st.button("Procesar Pago Parcial"):
                if monto >= 100000:
                    abono, nan, nad = monto, an, ad
                    while abono >= 100000 and nad > 0:
                        nad -= 1; abono -= 100000
                    while abono >= 100000 and nan >= 3:
                        nan -= 3; abono -= 100000
                    db.table("participantes").update({"amarillas_normales": nan, "amarillas_directas": nad}).eq("id", p["id"]).execute()
                    st.success("Abono aplicado.")
                    st.rerun()
                else:
                    st.warning("Abono mínimo: $100.000")

        st.divider()

        # --- FICHA TÉCNICA (COMPLETA - AQUÍ ESTÁ TODO) ---
        with st.form("ficha_completa"):
            st.subheader(f"📝 Ficha Técnica: {p['nombre']}")
            izq, der = st.columns(
