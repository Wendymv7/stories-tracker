import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Santas Admin Pro", page_icon="⚽", layout="wide")

# Estilo CSS para poner títulos en morado
st.markdown("""
    <style>
    .stMetric { color: #8e44ad; }
    h1, h2, h3 { color: #6c3483; }
    </style>
    """, unsafe_allow_code=True)

# 2. CONEXIÓN
if "db" not in st.session_state:
    u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    st.session_state.db = create_client(u, k)
db = st.session_state.db

# 3. LOGIN (Simplificado)
def check_login():
    st.sidebar.title("🔐 Acceso Admin")
    if st.session_state.get("logged_in"):
        st.sidebar.success(f"Hola: {st.session_state.admin_name}")
        if st.sidebar.button("Salir"):
            st.session_state.logged_in = False; st.rerun()
        return True
    with st.sidebar.form("login"):
        user = st.text_input("Usuario"); passw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", user).eq("password", passw).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.admin_name = True, res.data[0]["nombre"]
                st.rerun()
    return False

# 4. CRM Y CONTABILIDAD
def mostrar_crm():
    st.header("👥 Gestión de Santas FC")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas: st.info("Sin registros"); return

    sel = st.selectbox("Seleccionar niña:", ["-- Seleccionar --"] + [c["nombre"] for c in chicas])
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        an, ad = p.get('amarillas_normales', 0) or 0, p.get('amarillas_directas', 0) or 0
        multa = ((an // 3) * 100000) + (ad * 100000)
        
        st.subheader(f"💜 Perfil: {p['nombre']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", an); c2.metric("🟥 Directas", ad); c3.metric("💸 DEUDA", f"${multa:,.0f}")

        col_f, col_p = st.columns(2)
        with col_f:
            st.markdown("### ➕ Registrar Sanción")
            tipo_f = st.radio("Causa:", ["Normal", "Directa"], horizontal=True)
            motivo = st.text_input("¿Por qué la falta?", placeholder="Ej: No trajo el uniforme lila")
            if st.button("Guardar Falta"):
                # Actualizar contadores
                db.table("participantes").update({"amarillas_normales": an + 1 if tipo_f == "Normal" else an, "amarillas_directas": ad + 1 if tipo_f == "Directa" else ad}).eq("id", p["id"]).execute()
                # Guardar en registros (reutilizamos la tabla registros para el historial)
                db.table("registros").insert({"participante_id": p["id"], "fecha": datetime.now().strftime("%Y-%m-%d"), "status": f"Falta {tipo_f}: {motivo}"}).execute()
                st.rerun()
        
        with col_p:
            st.markdown("### 💵 Abono")
            monto = st.number_input("Monto ($):", min_value=0, step=100000)
            if st.button("Procesar Pago"):
                ab, nan, nad = monto, an, ad
                while ab >= 100000 and nad > 0: nad -= 1; ab -= 100000
                while ab >= 100000 and nan >= 3: nan -= 3; ab -= 100000
                db.table("participantes").update({"amarillas_normales": nan, "amarillas_directas": nad}).eq("id", p["id"]).execute()
                db.table("registros").insert({"participante_id": p["id"], "fecha": datetime.now().strftime("%Y-%m-%d"), "status": f"Abono: ${monto:,.0f}"}).execute()
                st.rerun()

        # --- SECCIÓN VER DETALLE (HISTORIAL) ---
        st.divider()
        with st.expander("🔍 Ver Detalle e Historial"):
            logs = db.table("registros").select("*").eq("participante_id", p["id"]).order("created_at", desc=True).execute()
            if logs.data:
                for l in logs.data:
                    st.write(f"📅 {l['fecha']} | {l['status']}")
            else:
                st.write("No hay eventos registrados.")

        st.divider()
        with st.form("ficha"):
            st.subheader("📝 Ficha Técnica")
            izq, der = st.columns(2)
            n = izq.text_input("Nombre", value=p["nombre"]); h = der.text_input("Instagram", value=p["handle"])
            ced = izq.text_input("Cédula", value=p.get("cedula", "")); sang = der.text_input("Sangre", value=p.get("tipo_sangre", ""))
            if st.form_submit_button("Actualizar Ficha"):
                db.table("participantes").update({"nombre":n,"handle":h,"cedula":ced,"tipo_sangre":sang}).eq("id", p["id"]).execute(); st.rerun()

# 5. FLUJO PRINCIPAL
if check_login():
    st.sidebar.image("https://i.ibb.co/Vp6q9F5/image-f23baf.png") # Aquí puedes poner el link real de tu logo
    st.sidebar.divider()
    opcion = st.sidebar.radio("Navegación", ["📱 Validación Robot", "👥 CRM Santas"])
    if opcion == "📱 Validación Robot":
        st.title("📊 Stories Tracker")
        logs = db.table("registros").select("*, participantes(nombre)").order("created_at", desc=True).limit(50).execute()
        for l in (logs.data or []):
            if "Falta" not in l['status'] and "Abono" not in l['status']: # Filtramos solo robots
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"👤 {l['participantes']['nombre']}")
                c2.write(f"📅 {l['fecha']}")
                if l['status'] == "cumplido": c3.success("✅ OK")
                else: c3.error("❌ NO")
    else: mostrar_crm()
else:
    st.title("💜 Santas FC - Admin"); st.info("Ingresa tus credenciales.")
