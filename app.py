import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import io

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Stories Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

DIAS_FULL  = ["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"]
DIAS_SHORT = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"]
MESES      = ["enero","febrero","marzo","abril","mayo","junio",
               "julio","agosto","septiembre","octubre","noviembre","diciembre"]

# ─────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────
@st.cache_resource
def get_db():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

db = get_db()

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("## 📋 Stories Tracker")
        st.markdown("Acceso para administradoras")
        pw = st.text_input("Contraseña", type="password", key="login_pw")
        if st.button("Entrar", type="primary"):
            if pw == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.stop()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt_date(d: date) -> str:
    return f"{DIAS_FULL[d.weekday()+1 if d.weekday()<6 else 0]} {d.day} de {MESES[d.month-1]} {d.year}"

# weekday() → 0=Lun…6=Dom, pero nuestra tabla usa 0=Dom,1=Lun…6=Sáb
def py_dow_to_app(d: date) -> int:
    return (d.weekday() + 1) % 7

def initials(nombre: str) -> str:
    parts = nombre.strip().split()
    return "".join(p[0].upper() for p in parts[:2])

def badge(status: str) -> str:
    icons = {"cumplido":"✅","incumplido":"❌","pendiente":"⏳","enviado":"📤"}
    labels = {"cumplido":"Cumplió","incumplido":"No cumplió","pendiente":"Pendiente","enviado":"En revisión"}
    return f"{icons.get(status,'⏳')} {labels.get(status,'Pendiente')}"

@st.cache_data(ttl=30)
def load_participantes():
    r = db.table("participantes").select("*").eq("activa", True).order("nombre").execute()
    return r.data or []

@st.cache_data(ttl=30)
def load_config():
    r = db.table("config").select("*").eq("id", 1).single().execute()
    return r.data or {"hashtags": [], "cuenta_tag": ""}

@st.cache_data(ttl=20)
def load_registros_hoy(today_str: str):
    r = db.table("registros").select("*").eq("fecha", today_str).execute()
    return {row["participante_id"]: row for row in (r.data or [])}

@st.cache_data(ttl=30)
def load_historial():
    desde = (date.today() - relativedelta(months=3)).isoformat()
    r = db.table("registros").select("*").gte("fecha", desde).order("fecha", desc=True).execute()
    return r.data or []

def invalidate_caches():
    load_participantes.clear()
    load_registros_hoy.clear()
    load_historial.clear()
    load_config.clear()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
check_auth()

today      = date.today()
today_str  = today.isoformat()
today_dow  = py_dow_to_app(today)

# Sidebar
with st.sidebar:
    st.markdown("### 📋 Stories Tracker")
    st.caption(fmt_date(today))
    st.divider()

    page = st.radio(
        "Navegación",
        ["📅 Hoy", "⏳ Revisar capturas", "👥 Participantes", "# Hashtags", "🗓 Historial", "📊 Informe"],
        label_visibility="collapsed",
    )
    st.divider()

    # Badge pendientes
    pend_count = len([r for r in load_historial() if r.get("status") == "enviado"])
    if pend_count:
        st.warning(f"⏳ {pend_count} captura{'s' if pend_count>1 else ''} por revisar")

    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ══════════════════════════════════════════════
# HOY
# ══════════════════════════════════════════════
if page == "📅 Hoy":
    st.title("Cumplimiento de hoy")
    st.caption(fmt_date(today))

    participantes = load_participantes()
    p_hoy = [p for p in participantes if today_dow in p["dias"]]

    if not p_hoy:
        st.info("No hay participantes asignadas para hoy.")
        st.stop()

    reg_map = load_registros_hoy(today_str)

    cum  = sum(1 for p in p_hoy if reg_map.get(p["id"],{}).get("status") == "cumplido")
    inc  = sum(1 for p in p_hoy if reg_map.get(p["id"],{}).get("status") == "incumplido")
    env  = sum(1 for p in p_hoy if reg_map.get(p["id"],{}).get("status") == "enviado")
    pend = len(p_hoy) - cum - inc - env
    pct  = round(cum / len(p_hoy) * 100) if p_hoy else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Asignadas hoy", len(p_hoy))
    c2.metric("✅ Cumplieron", cum)
    c3.metric("❌ No cumplieron", inc)
    c4.metric("⏳ Pendientes", pend)
    c5.metric("% cumplimiento", f"{pct}%")

    st.divider()

    filtro = st.segmented_control(
        "Filtrar",
        ["Todas","Pendientes","Cumplieron","No cumplieron"],
        default="Todas",
        key="hoy_filtro"
    )

    filtered = p_hoy
    if filtro == "Pendientes":
        filtered = [p for p in p_hoy if reg_map.get(p["id"],{}).get("status","pendiente") in ("pendiente",None)]
    elif filtro == "Cumplieron":
        filtered = [p for p in p_hoy if reg_map.get(p["id"],{}).get("status") == "cumplido"]
    elif filtro == "No cumplieron":
        filtered = [p for p in p_hoy if reg_map.get(p["id"],{}).get("status") == "incumplido"]

    if not filtered:
        st.info("Sin resultados para este filtro.")
    else:
        for p in filtered:
            reg = reg_map.get(p["id"])
            st_val = reg.get("status","pendiente") if reg else "pendiente"

            with st.container(border=True):
                col_info, col_btn = st.columns([3,2])
                with col_info:
                    st.markdown(f"**{p['nombre']}** &nbsp; `{p['handle']}`")
                    st.caption(f"Días: {', '.join(DIAS_SHORT[d] for d in p['dias'])}")
                    st.markdown(badge(st_val))
                    if reg and reg.get("evidencia_url"):
                        st.markdown(f"[📎 Ver captura de pantalla]({reg['evidencia_url']})")
                    if reg and reg.get("notas"):
                        st.caption(f"💬 {reg['notas']}")

                with col_btn:
                    with st.expander("✏️ Registrar"):
                        nuevo_st = st.selectbox(
                            "Estado",
                            ["pendiente","cumplido","incumplido","enviado"],
                            format_func=lambda x: {"pendiente":"⏳ Pendiente","cumplido":"✅ Cumplió","incumplido":"❌ No cumplió","enviado":"📤 En revisión"}[x],
                            index=["pendiente","cumplido","incumplido","enviado"].index(st_val),
                            key=f"st_{p['id']}"
                        )
                        notas = st.text_area("Notas", value=reg.get("notas","") if reg else "", key=f"notas_{p['id']}", height=68)
                        archivo = st.file_uploader("📎 Captura de pantalla", type=["png","jpg","jpeg","webp"], key=f"file_{p['id']}")

                        if st.button("Guardar", key=f"save_{p['id']}", type="primary"):
                            ev_url = reg.get("evidencia_url") if reg else None
                            ev_nom = reg.get("evidencia_nombre") if reg else None

                            if archivo:
                                ext  = archivo.name.rsplit(".",1)[-1]
                                path = f"{p['id']}/{today_str}_{int(datetime.now().timestamp())}.{ext}"
                                db.storage.from_("evidencias").upload(path, archivo.read(), {"content-type": archivo.type})
                                pub = db.storage.from_("evidencias").get_public_url(path)
                                ev_url = pub
                                ev_nom = archivo.name

                            payload = {
                                "participante_id": p["id"],
                                "fecha": today_str,
                                "status": nuevo_st,
                                "notas": notas,
                                "evidencia_url": ev_url,
                                "evidencia_nombre": ev_nom,
                                "updated_at": datetime.now().isoformat(),
                            }
                            db.table("registros").upsert(payload, on_conflict="participante_id,fecha").execute()
                            invalidate_caches()
                            st.success("Guardado ✓")
                            st.rerun()

    if st.button("↻ Actualizar"):
        invalidate_caches()
        st.rerun()

# ══════════════════════════════════════════════
# REVISAR CAPTURAS
# ══════════════════════════════════════════════
elif page == "⏳ Revisar capturas":
    st.title("Revisar capturas")
    st.caption("Registros en estado 'En revisión' — aprueba o rechaza cada uno.")

    participantes = load_participantes()
    p_map = {p["id"]: p for p in participantes}

    desde = (date.today() - relativedelta(months=3)).isoformat()
    r = db.table("registros").select("*").eq("status","enviado").gte("fecha",desde).order("fecha",desc=True).execute()
    pendientes = r.data or []

    if not pendientes:
        st.success("Sin capturas pendientes de revisión. Todo al día ✓")
    else:
        for reg in pendientes:
            p = p_map.get(reg["participante_id"])
            if not p: continue
            d = date.fromisoformat(reg["fecha"])
            with st.container(border=True):
                c1, c2 = st.columns([3,1])
                with c1:
                    st.markdown(f"**{p['nombre']}** &nbsp; `{p['handle']}`")
                    st.caption(fmt_date(d))
                    if reg.get("evidencia_url"):
                        st.markdown(f"[📎 Ver captura de pantalla]({reg['evidencia_url']})")
                        try:
                            st.image(reg["evidencia_url"], width=320)
                        except:
                            pass
                    else:
                        st.caption("Sin imagen adjunta")
                    if reg.get("notas"):
                        st.caption(f"💬 {reg['notas']}")
                with c2:
                    if st.button("✅ Cumplió", key=f"ap_{reg['id']}", type="primary", use_container_width=True):
                        db.table("registros").update({"status":"cumplido","updated_at":datetime.now().isoformat()}).eq("id",reg["id"]).execute()
                        invalidate_caches(); st.rerun()
                    if st.button("❌ No cumplió", key=f"re_{reg['id']}", use_container_width=True):
                        db.table("registros").update({"status":"incumplido","updated_at":datetime.now().isoformat()}).eq("id",reg["id"]).execute()
                        invalidate_caches(); st.rerun()

# ══════════════════════════════════════════════
# PARTICIPANTES
# ══════════════════════════════════════════════
elif page == "👥 Participantes":
    st.title("Participantes")

    with st.expander("➕ Agregar participante", expanded=False):
        c1,c2 = st.columns(2)
        nombre = c1.text_input("Nombre completo")
        handle = c2.text_input("Usuario de Instagram", placeholder="@usuario")
        dias_opciones = {1:"Lunes",2:"Martes",3:"Miércoles",4:"Jueves",5:"Viernes",6:"Sábado",0:"Domingo"}
        dias_sel = st.multiselect("Días asignados", options=list(dias_opciones.keys()), format_func=lambda x: dias_opciones[x])
        if st.button("Agregar", type="primary"):
            if not nombre or not handle or not dias_sel:
                st.error("Completa todos los campos.")
            else:
                h = handle if handle.startswith("@") else "@"+handle
                db.table("participantes").insert({"nombre":nombre,"handle":h,"dias":dias_sel}).execute()
                invalidate_caches(); st.success("Agregada ✓"); st.rerun()

    st.divider()
    participantes = load_participantes()
    if not participantes:
        st.info("Sin participantes aún.")
    else:
        for p in participantes:
            c1,c2,c3 = st.columns([2,2,1])
            c1.markdown(f"**{p['nombre']}**")
            c2.caption(f"{p['handle']} · {', '.join(DIAS_SHORT[d] for d in p['dias'])}")
            if c3.button("Eliminar", key=f"del_{p['id']}", type="secondary"):
                db.table("participantes").update({"activa":False}).eq("id",p["id"]).execute()
                invalidate_caches(); st.rerun()

# ══════════════════════════════════════════════
# HASHTAGS
# ══════════════════════════════════════════════
elif page == "# Hashtags":
    st.title("Hashtags y cuenta")
    cfg = load_config()

    st.subheader("Hashtags obligatorios")
    st.caption("Estos deben estar en la story para contar como cumplida.")

    hashtags = list(cfg.get("hashtags") or [])
    c1,c2 = st.columns([3,1])
    nuevo_ht = c1.text_input("Nuevo hashtag", placeholder="#hashtag", label_visibility="collapsed")
    if c2.button("Agregar", type="primary"):
        val = nuevo_ht.strip()
        if val:
            if not val.startswith("#"): val = "#"+val
            if val not in hashtags:
                hashtags.append(val)
                db.table("config").update({"hashtags":hashtags,"updated_at":datetime.now().isoformat()}).eq("id",1).execute()
                load_config.clear(); st.rerun()

    if hashtags:
        cols = st.columns(min(len(hashtags), 5))
        for i, ht in enumerate(hashtags):
            with cols[i % 5]:
                if st.button(f"{ht} ×", key=f"rmht_{i}"):
                    hashtags.remove(ht)
                    db.table("config").update({"hashtags":hashtags,"updated_at":datetime.now().isoformat()}).eq("id",1).execute()
                    load_config.clear(); st.rerun()
    else:
        st.caption("Sin hashtags aún.")

    st.divider()
    st.subheader("Cuenta a etiquetar")
    cuenta_val = cfg.get("cuenta_tag","")
    c1,c2 = st.columns([3,1])
    nueva_cuenta = c1.text_input("Cuenta", value=cuenta_val, placeholder="@cuenta_principal", label_visibility="collapsed")
    if c2.button("Guardar", type="primary"):
        val = nueva_cuenta.strip()
        if not val.startswith("@"): val = "@"+val
        db.table("config").update({"cuenta_tag":val,"updated_at":datetime.now().isoformat()}).eq("id",1).execute()
        load_config.clear(); st.success("Guardado ✓"); st.rerun()

# ══════════════════════════════════════════════
# HISTORIAL
# ══════════════════════════════════════════════
elif page == "🗓 Historial":
    st.title("Historial · 3 meses")

    participantes = load_participantes()
    p_map = {p["id"]: p for p in participantes}
    registros = load_historial()

    if not registros:
        st.info("Sin registros en los últimos 3 meses.")
        st.stop()

    # Filtro por participante
    nombres = ["Todas"] + [p["nombre"] for p in participantes]
    filtro_p = st.selectbox("Filtrar por participante", nombres)

    if filtro_p != "Todas":
        pid_filtro = next((p["id"] for p in participantes if p["nombre"]==filtro_p), None)
        registros  = [r for r in registros if r["participante_id"]==pid_filtro]

    # Agrupar por fecha
    by_date: dict = {}
    for r in registros:
        by_date.setdefault(r["fecha"], []).append(r)

    for fecha in sorted(by_date.keys(), reverse=True):
        d    = date.fromisoformat(fecha)
        rows = by_date[fecha]
        cum  = sum(1 for r in rows if r["status"]=="cumplido")
        pct  = round(cum/len(rows)*100) if rows else 0

        with st.expander(f"{fmt_date(d)} — {pct}% cumplimiento", expanded=(fecha==today_str)):
            for r in rows:
                p = p_map.get(r["participante_id"])
                if not p: continue
                c1,c2,c3 = st.columns([2,2,1])
                c1.markdown(f"**{p['nombre']}**")
                c2.caption(p["handle"])
                c3.markdown(badge(r["status"]))
                if r.get("evidencia_url"):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;[📎 Ver captura]({r['evidencia_url']})")
                if r.get("notas"):
                    st.caption(f"&nbsp;&nbsp;&nbsp;💬 {r['notas']}")

# ══════════════════════════════════════════════
# INFORME
# ══════════════════════════════════════════════
elif page == "📊 Informe":
    st.title("Informe general")
    st.caption("Últimos 3 meses")

    participantes = load_participantes()
    registros     = load_historial()
    p_map         = {p["id"]: p for p in participantes}

    total_a = 0; total_c = 0
    tabla_rows = []
    for p in participantes:
        asig=0; cump=0; evid=0
        for r in registros:
            if r["participante_id"] != p["id"]: continue
            d = date.fromisoformat(r["fecha"])
            if py_dow_to_app(d) not in p["dias"]: continue
            asig += 1
            if r["status"] == "cumplido":
                cump += 1
                if r.get("evidencia_url"): evid += 1
        total_a += asig; total_c += cump
        pct = round(cump/asig*100) if asig else 0
        tabla_rows.append({"Participante":p["nombre"],"Handle":p["handle"],"Días asignados":asig,"Cumplió":cump,"No cumplió":asig-cump,"Evidencias":evid,"Cumplimiento %":pct})

    g_pct = round(total_c/total_a*100) if total_a else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Participantes", len(participantes))
    c2.metric("Días registrados", len({r["fecha"] for r in registros}))
    c3.metric("✅ Cumplimientos", total_c)
    c4.metric("% global", f"{g_pct}%")

    st.divider()

    if tabla_rows:
        df = pd.DataFrame(tabla_rows)
        st.dataframe(
            df.style.bar(subset=["Cumplimiento %"], color=["#fcebeb","#eaf3de"], vmin=0, vmax=100),
            use_container_width=True,
            hide_index=True,
        )

        # Exportar CSV
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Exportar CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"informe-stories-{today_str}.csv",
            mime="text/csv",
        )
    else:
        st.info("Sin datos aún.")
