import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import urllib.parse

# 1. SETUP INICIAL
st.set_page_config(page_title="Santas Admin Pro", page_icon="⚽", layout="wide")

# ESTÉTICA LILA VIBRANTE
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

# 4. ALERTA CUMPLES (Corregida para hoy y próximos 2 días)
def alerta_cumples(chicas):
    hoy = datetime.now().date()
    for c in chicas:
        if c.get("fecha_nacimiento"):
            try:
                fn = datetime.strptime(c["fecha_nacimiento"], "%Y-%m-%d").date()
                ca = fn.replace(year=hoy.year)
                # Si el cumple ya pasó este año, mirar el del próximo (para finales de año)
                if ca < hoy: ca = ca.replace(year=hoy.year + 1)
                
                diff = (ca - hoy).days
                if 0 <= diff <= 2:
                    st.warning(f"🎂 **¡CUMPLEAÑOS!** {c['nombre']} ({ca.strftime('%d/%m')})")
                    t = urllib.parse.quote(f"¡Hola equipo! 💜 El {ca.strftime('%d/%m')} es el cumple de {c['nombre']}. ¿Lista la publicidad? ⚽")
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
            mot = st.text_input("Motivo de la falta:", key="mot_falta")
            if st.button("Guardar Falta"):
                db.table("participantes").update({"amarillas_normales": an+1 if tf=="Normal" else an, "amarillas_directas": ad+1 if tf=="Directa" else ad}).eq("id", p["id"]).execute()
                status_txt = f"Falta {tf}: {mot}" if mot else f"Falta {tf}"
                db.table("registros").insert({"participante_id": p["id"], "fecha": datetime.now().strftime("%Y-%m-%d"), "status": status_txt}).execute()
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

        st.divider()
