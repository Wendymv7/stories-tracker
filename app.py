import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Santas Admin Pro", page_icon="💰", layout="wide")

# 2. CONEXIÓN
if "db" not in st.session_state:
    try:
        u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(u, k)
    except Exception as e:
        st.error(f"Error DB: {e}"); st.stop()

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
            else: st.sidebar.error("Datos incorrectos")
    return False

# 4. CRM Y CONTABILIDAD
def mostrar_crm():
    st.header("👥 CRM Santas")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas: st.info("Sin registros"); return

    sel = st.selectbox("Buscar niña:", ["-- Seleccionar --"] + [c["nombre"] for c in chicas])
    
    if sel != "-- Seleccionar --":
        p = next(c for c in chicas if c["nombre"] == sel)
        an, ad = p.get('amarillas_normales', 0) or 0, p.get('amarillas_directas', 0) or 0
        multa = ((an // 3) * 100000) + (ad * 100000)
        
        st.markdown(f"## ⚠️ Disciplina: {p['nombre']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", an); c2.metric("🟥 Directas", ad); c3.metric("💸 Multa", f"${multa:,.0f}")

        col_f, col_p = st.columns(2)
        with col_f:
            st.subheader("➕ Sanción")
            tipo_f = st.radio("Causa:", ["Normal", "Directa"], horizontal=True)
            if st.button("Guardar Falta"):
                db.table("participantes").update({"amarillas_normales": an + 1 if tipo_f == "Normal" else an, "amarillas_directas": ad + 1 if tipo_f == "Directa" else ad}).eq("id", p["id"]).execute(); st.rerun()
        with col_p:
            st.subheader("💵 Abono")
            monto = st.number_input("Monto ($):", min_value=0, step=100000)
            if st.button("Procesar Pago"):
                ab, nan, nad = monto, an, ad
                while ab >= 100000 and nad > 0: nad -= 1; ab -= 100000
                while ab >= 100000 and nan >= 3: nan -= 3; ab -= 100000
                db.table("participantes").update({"amarillas_normales": nan, "amarillas_directas": nad}).eq("id", p["id"]).execute(); st.rerun()

        st.divider()
        with st.form("ficha_completa"):
            st.subheader("📝 Ficha Técnica")
            izq, der = st.columns(2)
            n = izq.text_input("Nombre", value=p.get("nombre", "")); h = der.text_input("Instagram", value=p.get("handle", ""))
            tk = izq.text_input("TikTok", value=p.get("tiktok", "") or ""); ced = der.text_input("Cédula", value=p.get("cedula", "") or "")
            ma = izq.text_input("Correo", value=p.get("correo", "") or ""); sa = der.text_input("Sangre", value=p.get("tipo_sangre", "") or "")
            dr = izq.text_input("Dirección", value=p.get("direccion", "") or ""); pr = der.text_input("Profesión", value=p.get("profesion", "") or "")
            f1, f2 = st.columns(2)
            fn = p.get("fecha_nacimiento")
            f_nac = f1.date_input("Nacimiento", value=datetime.strptime(fn, "%Y-%m-%d") if fn else datetime(2000,1,1))
            fi = p.get("fecha_ingreso_santas")
            f_ing = f2.date_input("Ingreso", value=datetime.strptime(fi, "%Y-%m-%d") if fi else datetime.now())
            if st.form_submit_button("💾 Actualizar Ficha"):
                db.table("participantes").update({"nombre":n,"handle":h,"tiktok":tk,"cedula":ced,"correo":ma,"tipo_sangre":sa,"direccion":dr,"profesion":pr,"fecha_nacimiento":f_nac.strftime("%Y-%m-%d"),"fecha_ingreso_santas":f_ing.strftime("%Y-%m-%d")}).eq("id", p["id"]).execute()
                st.success("¡Listo!"); st.rerun()

# 5. FLUJO PRINCIPAL
if check_login():
    st.sidebar.divider()
    opcion = st.sidebar.radio("Menú", ["📱 Validación", "👥 CRM"])
    if opcion == "📱 Validación":
        st.title("📊 Stories Tracker")
        try:
            logs = db.table("registros").select("*, participantes(nombre, handle)").order("created_at", desc=True).limit(50).execute()
            for l in (logs.data or []):
                col1, col2, col3 = st.columns([2, 2, 1])
                n_nena = l['participantes']['nombre'] if l['participantes'] else "N/A"
                col1.write(f"👤 **{n_nena}** (@{l['participantes']['handle']})")
                col2.write(f"📅 {l['fecha']}"); col3.success("✅ OK") if l['status'] == "cumplido" else col3.error("❌ NO")
                st.divider()
        except: st.warning("Sin datos.")
    else: mostrar_crm()
else:
    st.title("Admin Santas"); st.info("Ingresa tus credenciales a la izquierda.")
