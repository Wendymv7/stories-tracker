import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import urllib.parse

# 1. SETUP
st.set_page_config(page_title="Santas Admin Pro", page_icon="⚽", layout="wide")

# LILA SANTAS VIBRANTE
st.markdown("""
<style>
    .stApp { background-color: #e0b0ff; }
    .stMetric { background-color: rgba(255,255,255,0.6); padding: 15px; border-radius: 15px; }
    h1, h2, h3 { color: #4a235a !important; font-weight: bold; }
    .stButton>button { border-radius: 20px; background-color: #8e44ad; color: white; border: none; }
</style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN
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
        user = st.text_input("Usuario"); passw = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            res = db.table("administradores").select("*").eq("email", user).eq("password", passw).execute()
            if res.data:
                st.session_state.logged_in, st.session_state.admin_name = True, res.data[0]["nombre"]
                st.rerun()
    return False

# 4. ALERTA CUMPLES
def alerta_cumples(chicas):
    hoy = datetime.now()
    for c in chicas:
        if c.get("fecha_nacimiento"):
            try:
                fn = datetime.strptime(c["fecha_nacimiento"], "%Y-%m-%d")
                ca = fn.replace(year=hoy.year)
                if 0 <= (ca - hoy).days <= 2:
                    st.warning(f"🎂 **CUMPLE CERCA:** {c['nombre']} ({ca.strftime('%d/%m')})")
                    msg = urllib.parse.quote(f"¡Hola! 💜 El {ca.strftime('%d/%m')} cumple {c['nombre']}. ¿Lista la publicidad? ⚽")
                    st.markdown(f'[📲 Avisar por WhatsApp](https://wa.me/?text={msg})')
            except: pass

# 5. CRM Y CONTABILIDAD
def mostrar_crm():
    st.header("👥 Gestión de Santas FC")
    res = db.table("participantes").select("*").order("nombre").execute()
    chicas = res.data
    if not chicas: st.info("Sin registros"); return

    alerta_cumples(chicas)
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
            st.markdown("### ➕ Sanción")
            tf = st.radio("Tipo:", ["Normal", "Directa"], horizontal=True)
            mot = st.text_input("Motivo:")
            if st.button("Guardar Falta"):
                db.table("participantes").update({
                    "amarillas_normales": an+1 if tf=="Normal" else an, 
                    "amarillas_directas": ad+1 if tf=="Directa" else ad
                }).eq("id", p["id"]).execute()
                # Registro simplificado para evitar errores de API
                db.table("registros").insert({"participante_id": p["id"], "fecha": datetime.now().strftime("%Y-%m-%d"), "status": f"Falta {tf}"}).execute()
                st.rerun()

        with col_p:
            st.subheader("💵 Abono")
            monto = st.number_input("Monto ($):", min_value=0, step=100000)
            if st.button("Procesar Pago"):
                ab, nan, nad = monto, an, ad
                # Lógica de descuento real
                while ab >= 100000 and nad > 0:
                    nad -= 1; ab -= 100000
                while ab >= 100000 and nan >= 3:
                    nan -= 3; ab -= 100000
                db.table("participantes").update({"amarillas_normales": nan, "amarillas_directas": nad}).eq("id", p["id"]).execute()
                db.table("registros").insert({"participante_id": p["id"], "fecha": datetime.now().strftime("%Y-%m-%d"), "status": "Pago Realizado"}).execute()
                st.rerun()

        st.divider()
        with st.expander("🔍 Ver Detalle e Historial"):
            logs = db.table("registros").select("*").eq("participante_id", p["id"]).order("created_at", desc=True).execute()
            for l in (logs.data or []):
                st.write(f"📅 {l['fecha']} | {l['status']}")

        st.divider()
        # --- FICHA TÉCNICA TOTAL ---
        with st.form("ficha_full"):
            st.subheader("📝 Ficha Técnica Completa")
            izq, der = st.columns(2)
            with izq:
                f_nom = st.text_input("Nombre", value=p.get("nombre", ""))
                f_ced = st.text_input("Cédula", value=p.get("cedula", ""))
                f_ig = st.text_input("Instagram", value=p.get("handle", ""))
                f_tk = st.text_input("TikTok", value=p.get("tiktok", ""))
                f_mail = st.text_input("Correo", value=p.get("correo", ""))
            with der:
                f_san = st.text_input("Sangre", value=p.get("tipo_sangre", ""))
                f_pro = st.text_input("Profesión", value=p.get("profesion", ""))
                f_dir = st.text_input("Dirección", value=p.get("direccion", ""))
                
                fn_v = p.get("fecha_nacimiento")
                f_nac = st.date_input("Nacimiento", value=datetime.strptime(fn_v, "%Y-%m-%d") if fn_v else datetime(2000,1,1))
                
                fi_v = p.get("fecha_ingreso_santas")
                f_ing = st.date_input("Ingreso", value=datetime.strptime(fi_v, "%Y-%m-%d") if fi_v else datetime.now())

            if st.form_submit_button("💾 Guardar Datos"):
                db.table("participantes").update({
                    "nombre": f_nom, "cedula": f_ced, "handle": f_ig, "tiktok": f_tk,
                    "correo": f_mail, "tipo_sangre": f_san, "profesion": f_pro, "direccion": f_dir,
                    "fecha_nacimiento": f_nac.strftime("%Y-%m-%d"),
                    "fecha_ingreso_santas": f_ing.strftime("%Y-%m-%d")
                }).eq("id", p["id"]).execute()
                st.success("¡Información actualizada!"); st.rerun()

# 6. FLUJO PRINCIPAL
if check_login():
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegación", ["📋 Validación Etiquetas", "👥 CRM Perfiles Santas"])
    if menu == "📋 Validación Etiquetas":
        st.header("📊 Validación de Etiquetas")
        logs = db.table("registros").select("*, participantes(nombre)").order("created_at", desc=True).limit(50).execute()
        for l in (logs.data or []):
            if l.get('participantes') and "Falta" not in str(l['status']) and "Pago" not in str(l['status']):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"👤 **{l['participantes']['nombre']}**"); c2.write(f"📅 {l['fecha']}")
                st.success("✅ CUMPLIÓ") if l['status'] == "cumplido" else st.error("❌ NO CUMPLIÓ")
                st.divider()
    else: mostrar_crm()
else:
    st.title("💜 Santas FC - Admin"); st.info("Ingresa tus credenciales.")
