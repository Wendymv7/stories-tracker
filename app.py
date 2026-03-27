import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP INICIAL
st.set_page_config(page_title="Santas Admin", page_icon="🛡️", layout="wide")

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

# 4. MÓDULO CRM
def mostrar_crm():
    st.header("👥 CRM Santas")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas:
        st.info("No hay registros")
        return

    sel = st.selectbox("Buscar niña:", ["-- Seleccionar --"] + [c["nombre"] for c in chicas])
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        st.subheader(f"⚠️ Disciplina: {p['nombre']}")
        
        an = p.get('amarillas_normales', 0) or 0
        ad = p.get('amarillas_directas', 0) or 0
        m = ((an // 3) * 100000) + (ad * 100000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", an)
        c2.metric("🟥 Directas", ad)
        c3.metric("💸 Multa", f"${m:,.0f}")

        col_b1, col_b2 = st.columns(2)
        if col_b1.button("➕ Amarilla Normal"):
            db.table("participantes").update({"amarillas_normales": an + 1}).eq("id", p["id"]).execute()
            st.rerun()
        if col_b2.button("➕ Amarilla Directa"):
            db.table("participantes").update({"amarillas_directas": ad + 1}).eq("id", p["id"]).execute()
            st.rerun()

        st.divider()
        with st.form("edit"):
            st.write("📝 Editar Ficha")
            nom = st.text_input("Nombre", value=p["nombre"])
            ig = st.text_input("Instagram", value=p["handle"])
            if st.form_submit_button("Guardar Cambios"):
                db.table("participantes").update({"nombre": nom, "handle": ig}).eq("id", p["id"]).execute()
                st.success("¡Listo!")
                st.rerun()

# 5. ESTRUCTURA PRINCIPAL (FLUJO CORREGIDO)
if check_login():
    st.sidebar.divider()
    opcion = st.sidebar.radio("Menú", ["📱 Validación", "👥 CRM"])
    
    if opcion == "📱 Validación":
        st.title("📊 Stories Tracker")
        try:
            logs = db.table("registros").select("*, participantes(nombre)").order("created_at", desc=True).limit(50).execute()
            if logs.data:
                for l in logs.data:
                    col1, col2, col3 = st.columns([2, 2, 1])
                    n_nena = l['participantes']['nombre'] if l['participantes'] else "N/A"
                    col1.write(f"👤 {n_nena}")
                    col2.write(f"📅 {l['fecha']}")
                    if l['status'] == "cumplido":
                        col3.success("✅ OK")
                    else:
                        col3.error("❌ NO")
                    st.divider()
            else:
                st.info("Sin datos de escaneo aún.")
        except Exception as e:
            st.warning("Aún no hay registros en la tabla.")
    else:
        mostrar_crm()
else:
    st.title("Admin Santas")
    st.info("Ingresa tus datos en el panel de la izquierda para comenzar.")
