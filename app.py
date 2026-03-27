import streamlit as st
from supabase import create_client
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Santas Admin", page_icon="🛡️", layout="wide")

# 2. CONEXIÓN DB
if "db" not in st.session_state:
    try:
        u = st.secrets["SUPABASE_URL"]
        k = st.secrets["SUPABASE_KEY"]
        st.session_state.db = create_client(u, k)
    except Exception as e:
        st.error(f"Error DB: {e}")
        st.stop()

db = st.session_state.db

# 3. LOGIN
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

# 4. CRM Y FICHA TÉCNICA
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
        st.markdown(f"## ⚠️ Disciplina: {p['nombre']}")
        
        an = p.get('amarillas_normales', 0) or 0
        ad = p.get('amarillas_directas', 0) or 0
        multa = ((an // 3) * 100000) + (ad * 100000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🟨 Normales", an)
        c2.metric("🟥 Directas", ad)
        c3.metric("💸 Multa", f"${multa:,.0f}")

        col_b1, col_b2 = st.columns(2)
        if col_b1.button("➕ Amarilla Normal"):
            db.table("participantes").update({"amarillas_normales": an + 1}).eq("id", p["id"]).execute()
            st.rerun()
        if col_b2.button("➕ Amarilla Directa"):
            db.table("participantes").update({"amarillas_directas": ad + 1}).eq("id", p["id"]).execute()
            st.rerun()

        st.divider()
        with st.form("ficha_full"):
            st.subheader(f"📝 Ficha Técnica: {p['nombre']}")
            
            c_izq, c_der = st.columns(2)
            with c_izq:
                nom = st.text_input("Nombre Completo", value=p.get("nombre", ""))
                ig = st.text_input("Instagram", value=p.get("handle", ""))
                tk = st.text_input("TikTok", value=p.get("tiktok", "") or "")
                ced = st.text_input("Cédula", value=p.get("cedula", "") or "")
                mail = st.text_input("Correo", value=p.get("correo", "") or "")
            with c_der:
                rol = st.selectbox("Rol", ["futbolista", "modelo"], index=0 if p.get("rol") == "futbolista" else 1)
                prof = st.text_input("Profesión", value=p.get("profesion", "") or "")
                sang = st.text_input("Tipo Sangre", value=p.get("tipo_sangre", "") or "")
                dir_casa = st.text_input("Dirección", value=p.get("direccion", "") or "")

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                fn_str = p.get("fecha_nacimiento")
                f_nac = st.date_input("Fecha Nacimiento", value=datetime.strptime(fn_str, "%Y-%m-%d") if fn_str else datetime(2000,1,1))
            with c_f2:
                fi_str = p.get("fecha_ingreso_santas")
                f_ing = st.date_input("Fecha Ingreso", value=datetime.strptime(fi_str, "%Y-%m-%d") if fi_str else datetime.now())

            if st.form_submit_button("💾 Guardar Todo"):
                db.table("participantes").update({
                    "nombre": nom, "handle": ig, "tiktok": tk, "cedula": ced,
                    "correo": mail, "rol": rol, "profesion": prof, "tipo_sangre": sang,
                    "direccion": dir_casa, "fecha_nacimiento": f_nac.strftime("%Y-%m-%d"),
                    "fecha_ingreso_santas": f_ing.strftime("%Y-%m-%d")
                }).eq("id", p["id"]).execute()
                st.success("¡Datos guardados!")
                st.rerun()

# 5. FLUJO PRINCIPAL
if check_login():
    st.sidebar.divider()
    opcion = st.sidebar.radio("Menú", ["📱 Validación", "👥 CRM"])
    
    if opcion == "📱 Validación":
        st.title("📊 Stories Tracker")
        try:
            logs = db.table("registros").select("*, participantes(nombre)").order("created_at", desc=True).limit(50).execute()
            if logs.data:
                for l in logs.data:
                    c1,
