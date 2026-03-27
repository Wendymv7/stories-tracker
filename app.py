import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Santas Admin - Pagos", page_icon="💰", layout="wide")

# 2. CONEXIÓN DB
if "db" not in st.session_state:
    u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    st.session_state.db = create_client(u, k)

db = st.session_state.db

# 3. LOGIN
def check_login():
    st.sidebar.title("🔐 Acceso Admin")
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Hola: {st.session_state.admin_name}")
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.logged_in = False; st.rerun()
        return True
    with st.sidebar.form("login"):
        user = st.text_input("Usuario")
        passw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", user).eq("password", passw).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.admin_name = True, res.data[0]["nombre"]
                st.rerun()
            else: st.sidebar.error("Error de acceso")
    return False

# 4. CRM CON GESTIÓN DE PAGOS
def mostrar_crm():
    st.header("👥 CRM Santas - Disciplina y Pagos")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas: st.info("Sin registros"); return

    sel = st.selectbox("Buscar niña:", ["-- Seleccionar --"] + [c["nombre"] for c in chicas])
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        
        an, ad = p.get('amarillas_normales', 0) or 0, p.get('amarillas_directas', 0) or 0
        multa_total = ((an // 3) * 100000) + (ad * 100000)
        
        # --- RESUMEN FINANCIERO ---
        st.markdown(f"### 📊 Estado de Cuenta: {p['nombre']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Amarillas Normales", an)
        c2.metric("🟥 Amarillas Directas", ad)
        c3.metric("💸 DEUDA TOTAL", f"${multa_total:,.0f}", delta_color="inverse")

        st.divider()

        # --- COLUMNAS DE ACCIÓN ---
        col_faltas, col_pagos = st.columns(2)

        with col_faltas:
            st.subheader("⚠️ Registrar Falta")
            tipo_f = st.radio("Tipo de falta:", ["Normal", "Directa"], horizontal=True)
            motivo_f = st.text_input("Motivo de la falta:", placeholder="Ej: Inasistencia")
            if st.button("➕ Aplicar Sanción"):
                db.table("participantes").update({
                    "amarillas_normales": an + 1 if tipo_f == "Normal" else an,
                    "amarillas_directas": ad + 1 if tipo_f == "Directa" else ad
                }).eq("id", p["id"]).execute()
                st.success(f"Sanción registrada para {p['nombre']}")
                st.rerun()

        with col_pagos:
            st.subheader("💳 Registrar Pago")
            monto_pago = st.number_input("Monto recibido ($):", min_value=0, step=50000)
            metodo = st.selectbox("Método de pago:", ["Nequi", "Efectivo", "Transferencia"])
            if st.button("✅ Confirmar Pago y Limpiar Deuda"):
                # Aquí podrías restar de una en una, pero lo más común es resetear si ya pagó
                db.table("participantes").update({
                    "amarillas_normales": 0, 
                    "amarillas_directas": 0
                }).eq("id", p["id"]).execute()
                st.balloons()
                st.success(f"Pago de ${monto_pago:,.0f} registrado. Cuenta de {p['nombre']} queda en $0.")
                st.rerun()

        st.divider()
        # --- HERRAMIENTAS DE EDICIÓN ---
        with st.expander("📝 Editar Información Básica"):
            with st.form("edit_info"):
                nom = st.text_input("Nombre", value=p["nombre"])
                ig = st.text_input("Instagram", value=p["handle"])
                if st.form_submit_button("Guardar Cambios"):
                    db.table("participantes").update({"nombre": nom, "handle": ig}).eq("id", p["id"]).execute()
                    st.rerun()

# 5. FLUJO PRINCIPAL
if check_login():
    st.sidebar.divider()
    opcion = st.sidebar.radio("Menú", ["📱 Validación", "👥 CRM"])
    if opcion == "📱 Validación":
        st.title("📊 Stories Tracker")
        logs = db.table("registros").select("*, participantes(nombre)").order("created_at", desc=True).limit(50).execute()
        for l in (logs.data or []):
            col1, col2, col3 = st.columns([2, 2, 1])
            n_nena = l['participantes']['nombre'] if l['participantes'] else "N/A"
            col1.write(f"👤 {n_nena}"); col2.write(f"📅 {l['fecha']}")
            if l['status'] == "cumplido": col3.success("✅ OK")
            else: col3.error("❌ NO")
            st.divider()
    else: mostrar_crm()
else:
    st.title("Admin Santas"); st.info("Inicia sesión a la izquierda.")
