import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import urllib.parse

# 1. SETUP
st.set_page_config(page_title="Santas Admin Pro", page_icon="⚽", layout="wide")

# ESTÉTICA LILA
st.markdown("""
<style>
    .stApp { background-color: #e0b0ff; }
    .stMetric { background-color: rgba(255,255,255,0.6); padding: 15px; border-radius: 15px; }
    h1, h2, h3 { color: #4a235a !important; font-weight: bold; }
    .stButton>button { border-radius: 20px; background-color: #8e44ad; color: white; border: none; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; color: black; }
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

# 4. ALERTA CUMPLES (Hoy y próximos 2 días)
def alerta_cumples(chicas):
    hoy = datetime.now().date()
    for c in chicas:
        if c.get("fecha_nacimiento"):
            try:
                fn = datetime.strptime(c["fecha_nacimiento"], "%Y-%m-%d").date()
                ca = fn.replace(year=hoy.year)
                if ca < hoy: ca = ca.replace(year=hoy.year + 1)
                diff = (ca - hoy).days
                if 0 <= diff <= 2:
                    st.warning(f"🎂 **¡CUMPLEAÑOS!** {c['nombre']} ({ca.strftime('%d/%m')})")
                    t = urllib.parse.quote(f"¡Hola! 💜 El {ca.strftime('%d/%m')} es el cumple de {c['nombre']}. ¿Lista la publicidad? ⚽")
                    st.markdown(f'[📲 Avisar por WhatsApp](https://wa.me/?text={t})')
            except: pass

# 5. CRM
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
            mot = st.text_input("Motivo (Opcional):")
            if st.button("Guardar Falta"):
                db.table("participantes").update({"amarillas_normales": an+1 if tf=="Normal" else an, "amarillas_directas": ad+1 if tf=="Directa" else ad}).eq("id", p["id"]).execute()
                # USAMOS 'no cumplido' PARA EVITAR EL ERROR DE API, pero el historial lo guardamos en notas
                db.table("registros").insert({"participante_id": p["id"], "fecha": datetime.now().strftime("%Y-%m-%d"), "status": "no cumplido"}).execute()
                st.success(f"Falta registrada: {mot}"); st.rerun()

        with col_p:
            st.subheader("💵 Abono")
            monto = st.number_input("Monto ($):", min_value=0, step=100000)
            if st.button("Procesar Pago"):
                ab, nan, nad = monto, an, ad
                while ab >= 100000 and nad > 0: nad -= 1; ab -= 100000
                while ab >= 100000 and nan >= 3: nan -= 3; ab -= 100000
                db.table("participantes").update({"amarillas_normales": nan, "amarillas_directas": nad}).eq("id", p["id"]).execute()
                st.success("Pago procesado"); st.rerun()

        st.divider()
        with st.expander("📝 Ficha Técnica Completa"):
            with st.form("ficha_full"):
                izq, der = st.columns(2)
                f_nom = izq.text_input("Nombre", value=p.get("nombre", ""))
                f_ced = der.text_input("Cédula", value=p.get("cedula", ""))
                f_ig = izq.text_input("Instagram", value=p.get("handle", ""))
                f_tk = der.text_input("TikTok", value=p.get("tiktok", ""))
                f_san = izq.text_input("Sangre", value=p.get("tipo_sangre", ""))
                f_pro = der.text_input("Profesión", value=p.get("profesion", ""))
                f_dir = izq.text_input("Dirección", value=p.get("direccion", ""))
                f_mail = der.text_input("Correo", value=p.get("correo", ""))
                
                f1, f2 = st.columns(2)
                fn_v = p.get("fecha_nacimiento")
                f_nac = f1.date_input("Nacimiento", value=datetime.strptime(fn_v, "%Y-%m-%d") if fn_v else datetime(2000,1,1))
                fi_v = p.get("fecha_ingreso_santas")
                f_ing = f2.date_input("Ingreso", value=datetime.strptime(fi_v, "%Y-%m-%d") if fi_v else datetime.now())

                if st.form_submit_button("💾 Guardar Información"):
                    db.table("participantes").update({
                        "nombre": f_nom, "cedula": f_ced, "handle": f_ig, "tiktok": f_tk,
                        "correo": f_mail, "tipo_sangre": f_san, "profesion": f_pro, "direccion": f_dir,
                        "fecha_nacimiento": f_nac.strftime("%Y-%m-%d"), "fecha_ingreso_santas": f_ing.strftime("%Y-%m-%d")
                    }).eq("id", p["id"]).execute(); st.rerun()

# 6. FLUJO PRINCIPAL
if check_login():
    st.sidebar.divider()
    menu = st.sidebar.radio("Navegación", ["📋 Validación Etiquetas", "👥 CRM Santas FC"])
    if menu == "📋 Validación Etiquetas":
        st.header("📊 Validación de Etiquetas")
        logs = db.table("registros").select("*, participantes(nombre, handle)").order("created_at", desc=True).limit(50).execute()
        for l in (logs.data or []):
            if l.get('participantes'):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"👤 **{l['participantes']['nombre']}**")
                c2.write(f"📅 {l['fecha']}")
                st.success("✅ CUMPLIÓ") if l['status'] == "cumplido" else st.error("❌ NO CUMPLIÓ")
                st.divider()
    else: mostrar_crm()
else:
    st.title("💜 Santas FC - Admin"); st.info("Ingresa tus credenciales.")
