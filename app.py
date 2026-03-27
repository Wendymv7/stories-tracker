import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
import urllib.parse

# 1. SETUP INICIAL
st.set_page_config(page_title="Santas Admin Pro", page_icon="⚽", layout="wide")

# LILA MÁS VIVO (Orquídea Santas)
st.markdown("""
<style>
    .stApp { background-color: #e0b0ff; }
    .stMetric { background-color: rgba(255,255,255,0.5); padding: 10px; border-radius: 10px; color: #6c3483; }
    h1, h2, h3 { color: #4a235a !important; font-weight: bold; }
    .stButton>button { border-radius: 20px; background-color: #8e44ad; color: white; }
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

# 4. ALERTA CUMPLES Y WHATSAPP
def alerta_cumples(chicas):
    hoy = datetime.now()
    for c in chicas:
        if c.get("fecha_nacimiento"):
            try:
                f_nac = datetime.strptime(c["fecha_nacimiento"], "%Y-%m-%d")
                cumple_act = f_nac.replace(year=hoy.year)
                diff = (cumple_act - hoy).days
                if 0 <= diff <= 2:
                    st.warning(f"🎂 **PROXIMO CUMPLE:** {c['nombre']} ({cumple_act.strftime('%d/%m')})")
                    t = urllib.parse.quote(f"¡Hola equipo! 💜 El {cumple_act.strftime('%d/%m')} es el cumple de {c['nombre']}. ¿Lista la publicidad? ⚽")
                    st.markdown(f'<a href="https://wa.me/?text={t}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:8px 15px;border-radius:10px;">📲 Avisar por WhatsApp</button></a>', unsafe_allow_html=True)
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
            tipo_f = st.radio("Tipo:", ["Normal", "Directa"], horizontal=True)
            motivo = st.text_input("Motivo de la falta:")
            if st.button("Guardar Falta"):
                # Actualizar puntos
                db.table("participantes").update({
                    "amarillas_normales": an + 1 if tipo_f == "Normal" else an,
                    "amarillas_directas": ad + 1 if tipo_f == "Directa" else ad
                }).eq("id", p["id"]).execute()
                
                # Insertar en registros (Solución al error de API)
                info_status = f"Falta {tipo_f}: {motivo}" if motivo else f"Falta {tipo_f}"
                db.table("registros").insert({
                    "participante_id": p["id"],
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "status": info_status
                }).execute()
                st.rerun()

        with col_p:
            st.markdown("### 💵 Abono")
            monto = st.number_input("Monto ($):", min_value=0, step=100000)
            if st.button("Procesar Pago"):
                ab, nan, nad = monto, an, ad
                while ab >= 100000 and nad > 0
