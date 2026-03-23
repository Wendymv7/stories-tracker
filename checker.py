"""
checker.py — Verifica stories de Instagram y guarda resultados en Supabase.

Lógica de ventanas:
  Miércoles → válidas si se publicaron desde martes 00:00 hasta miércoles 15:00 COL
  Viernes   → válidas si se publicaron desde jueves 00:00 hasta viernes 20:00 COL

Las stories de Instagram duran 24h, así que si alguien publicó ayer a las 9pm
todavía estarán activas y el checker las detecta.
"""

import os
import sys
import time
import random
import pytz
from datetime import datetime, date, timedelta
from supabase import create_client

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
IG_USERNAME  = os.environ["IG_USERNAME"]
IG_PASSWORD  = os.environ["IG_PASSWORD"]
SESSION_FILE = "ig_session.json"

TZ_COL = pytz.timezone("America/Bogota")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────────────────
# VENTANAS DE VALIDEZ POR DÍA
# ─────────────────────────────────────────────────────────
# dow: 0=Lun,1=Mar,2=Mié,3=Jue,4=Vie,5=Sáb,6=Dom (Python)
VENTANAS = {
    2: {  # Miércoles
        "label":         "Miércoles",
        "fecha_asignada": "miercoles",
        # Stories válidas: desde martes 00:00 hasta miércoles 15:00 COL
        "dia_inicio_offset": -1,   # martes = miércoles - 1
        "hora_inicio":   (0, 0),
        "hora_limite":   (15, 0),  # 3pm COL (2pm + 1h umbral)
    },
    4: {  # Viernes
        "label":         "Viernes",
        "fecha_asignada": "viernes",
        # Stories válidas: desde jueves 00:00 hasta viernes 20:00 COL
        "dia_inicio_offset": -1,   # jueves = viernes - 1
        "hora_inicio":   (0, 0),
        "hora_limite":   (20, 0),  # 8pm COL (7pm + 1h umbral)
    },
}

def get_ventana_hoy():
    """
    Retorna la ventana de validez para el día actual.
    Considera que algunas corridas de "día antes" corren en madrugada
    del día de asignación (ej: martes 8pm = miércoles 1am UTC).
    """
    now_col = datetime.now(TZ_COL)
    dow     = now_col.weekday()  # 0=Lun ... 6=Dom

    # Revisar si aplica ventana para hoy o para ayer
    for target_dow, ventana in VENTANAS.items():
        fecha_asignada = now_col.date()
        if dow == target_dow:
            fecha_asignada = now_col.date()
        elif dow == (target_dow - 1) % 7:
            # Corrida del día anterior (martes para miércoles, jueves para viernes)
            fecha_asignada = now_col.date() + timedelta(days=1)
        else:
            continue

        # Calcular ventana de timestamps
        inicio = TZ_COL.localize(datetime(
            fecha_asignada.year, fecha_asignada.month, fecha_asignada.day,
            ventana["hora_inicio"][0], ventana["hora_inicio"][1]
        ) - timedelta(days=-ventana["dia_inicio_offset"]))

        limite = TZ_COL.localize(datetime(
            fecha_asignada.year, fecha_asignada.month, fecha_asignada.day,
            ventana["hora_limite"][0], ventana["hora_limite"][1]
        ))

        # Si ya pasó el límite, no vale la pena verificar
        if now_col > limite:
            print(f"⚠ Ya pasó el límite para {ventana['label']} ({limite.strftime('%H:%M')} COL). Sin verificación.")
            return None, None, None

        return fecha_asignada, inicio, limite

    print(f"ℹ Hoy ({now_col.strftime('%A %H:%M')} COL) no hay verificación programada.")
    return None, None, None

# ─────────────────────────────────────────────────────────
# LOGIN INSTAGRAM
# ─────────────────────────────────────────────────────────
def get_client():
    from instagrapi import Client

    cl = Client()
    cl.delay_range = [3, 7]

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            cl.get_timeline_feed()
            print("✓ Sesión reutilizada")
            return cl
        except Exception:
            print("⚠ Sesión expirada, rehaciendo login...")

    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("✓ Login exitoso")
        return cl
    except Exception as e:
        print(f"✗ Error en login: {e}")
        sys.exit(1)

# ─────────────────────────────────────────────────────────
# CARGAR PARTICIPANTES DEL DÍA ASIGNADO
# ─────────────────────────────────────────────────────────
def cargar_participantes(fecha_asignada: date):
    """
    Trae participantes cuyo día asignado corresponde al día de la fecha_asignada.
    La app usa: 0=Dom,1=Lun,2=Mar,3=Mié,4=Jue,5=Vie,6=Sáb
    Python weekday: 0=Lun,1=Mar,2=Mié,3=Jue,4=Vie,5=Sáb,6=Dom
    """
    app_dow = (fecha_asignada.weekday() + 1) % 7
    r = db.table("participantes").select("*").eq("activa", True).execute()
    todos = r.data or []
    return [p for p in todos if app_dow in (p.get("dias") or [])]

def cargar_config():
    r = db.table("config").select("*").eq("id", 1).single().execute()
    return r.data or {"hashtags": [], "cuenta_tag": ""}

# ─────────────────────────────────────────────────────────
# VERIFICAR STORIES
# ─────────────────────────────────────────────────────────
def story_en_ventana(story, ventana_inicio, ventana_limite) -> bool:
    """Verifica si la story fue publicada dentro de la ventana válida."""
    if not hasattr(story, "taken_at") or not story.taken_at:
        return True  # si no tiene timestamp, la incluimos

    taken = story.taken_at
    if taken.tzinfo is None:
        taken = pytz.utc.localize(taken)
    taken_col = taken.astimezone(TZ_COL)

    en_ventana = ventana_inicio <= taken_col <= ventana_limite
    if not en_ventana:
        print(f"    Story fuera de ventana: {taken_col.strftime('%a %d/%m %H:%M COL')}")
    return en_ventana

def verificar_usuario(cl, handle: str, hashtags: list, cuenta_tag: str,
                      ventana_inicio, ventana_limite) -> dict:
    resultado = {
        "tiene_stories":        False,
        "stories_en_ventana":   0,
        "hashtags_encontrados": [],
        "hashtags_faltantes":   list(hashtags),
        "cuenta_etiquetada":    False,
        "cumple":               False,
        "detalle":              "",
    }

    try:
        username = handle.lstrip("@")
        user_id  = cl.user_id_from_username(username)
        time.sleep(random.uniform(2, 4))

        stories = cl.user_stories(user_id)
        time.sleep(random.uniform(1, 3))

        if not stories:
            resultado["detalle"] = "Sin stories activas"
            return resultado

        resultado["tiene_stories"] = True

        # Filtrar solo stories dentro de la ventana válida
        stories_validas = [s for s in stories if story_en_ventana(s, ventana_inicio, ventana_limite)]
        resultado["stories_en_ventana"] = len(stories_validas)

        if not stories_validas:
            resultado["detalle"] = (
                f"Tiene {len(stories)} stories pero ninguna dentro de la ventana "
                f"({ventana_inicio.strftime('%a %H:%M')}–{ventana_limite.strftime('%a %H:%M')} COL)"
            )
            return resultado

        ht_encontrados = set()
        cuenta_ok      = False

        for story in stories_validas:
            # Texto de la story
            texto = ""
            if hasattr(story, "caption_text") and story.caption_text:
                texto = story.caption_text.lower()

            # Sticker de hashtag
            if hasattr(story, "story_hashtags") and story.story_hashtags:
                for ht in story.story_hashtags:
                    ht_encontrados.add(f"#{ht.hashtag.name.lower()}")

            # Sticker de mención
            if hasattr(story, "story_mentions") and story.story_mentions:
                for m in story.story_mentions:
                    if m.user.username.lower() == cuenta_tag.lstrip("@").lower():
                        cuenta_ok = True

            # Hashtags en texto
            for ht in hashtags:
                if ht.lower() in texto:
                    ht_encontrados.add(ht.lower())

        ht_requeridos = [h.lower() for h in hashtags]
        ht_faltantes  = [h for h in ht_requeridos if h not in ht_encontrados]

        resultado["hashtags_encontrados"] = list(ht_encontrados)
        resultado["hashtags_faltantes"]   = ht_faltantes
        resultado["cuenta_etiquetada"]    = cuenta_ok

        cumple_ht     = len(ht_faltantes) == 0
        cumple_cuenta = cuenta_ok if cuenta_tag else True
        resultado["cumple"] = cumple_ht and cumple_cuenta

        if resultado["cumple"]:
            resultado["detalle"] = (
                f"✓ Cumple — {len(stories_validas)} stories en ventana, "
                f"hashtags: {', '.join(ht_encontrados) or 'n/a'}"
            )
        else:
            partes = []
            if ht_faltantes:
                partes.append(f"Faltan: {', '.join(ht_faltantes)}")
            if cuenta_tag and not cuenta_ok:
                partes.append(f"No etiquetó {cuenta_tag}")
            resultado["detalle"] = " · ".join(partes)

    except Exception as e:
        err = str(e)
        if "not found" in err.lower() or "user_not_found" in err.lower():
            resultado["detalle"] = "Perfil no encontrado o privado"
        else:
            resultado["detalle"] = f"Error: {err[:120]}"
            if "login" in err.lower():
                raise
        print(f"  ⚠ Error: {err}")

    return resultado

# ─────────────────────────────────────────────────────────
# GUARDAR RESULTADO
# ─────────────────────────────────────────────────────────
def guardar_resultado(participante_id: str, fecha_str: str, resultado: dict):
    # No sobreescribir si ya está cumplido
    ex = db.table("registros").select("status").eq("participante_id", participante_id).eq("fecha", fecha_str).execute()
    if ex.data and ex.data[0].get("status") == "cumplido":
        print(f"  → Ya cumplido, no se sobreescribe")
        return

    status = "cumplido" if resultado["cumple"] else "incumplido"
    now_col = datetime.now(TZ_COL)

    payload = {
        "participante_id": participante_id,
        "fecha":           fecha_str,
        "status":          status,
        "notas":           resultado["detalle"][:500],
        "revisado_por":    f"Bot {now_col.strftime('%a %H:%M COL')}",
        "updated_at":      datetime.now().isoformat(),
    }
    db.table("registros").upsert(payload, on_conflict="participante_id,fecha").execute()
    icono = "✅" if status == "cumplido" else "❌"
    print(f"  {icono} {status} — {resultado['detalle'][:80]}")

def log_run(fecha_str, total, cumplieron, errores, duracion):
    try:
        now_col = datetime.now(TZ_COL)
        db.table("checker_logs").insert({
            "fecha":        fecha_str,
            "hora":         now_col.strftime("%H:%M COL"),
            "total":        total,
            "cumplieron":   cumplieron,
            "errores":      errores,
            "duracion_seg": round(duracion),
        }).execute()
    except Exception:
        pass

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def main():
    import time as time_mod
    inicio = time_mod.time()

    now_col = datetime.now(TZ_COL)
    print(f"\n{'='*55}")
    print(f"Stories Checker — {now_col.strftime('%A %d/%m/%Y %H:%M')} COL")
    print(f"{'='*55}\n")

    # Determinar ventana válida para hoy
    fecha_asignada, ventana_inicio, ventana_limite = get_ventana_hoy()
    if not fecha_asignada:
        sys.exit(0)

    print(f"Día asignado: {fecha_asignada}")
    print(f"Ventana válida: {ventana_inicio.strftime('%a %d/%m %H:%M')} → {ventana_limite.strftime('%a %d/%m %H:%M')} COL\n")

    # Cargar datos
    participantes = cargar_participantes(fecha_asignada)
    config        = cargar_config()
    hashtags      = config.get("hashtags") or []
    cuenta_tag    = config.get("cuenta_tag") or ""
    fecha_str     = fecha_asignada.isoformat()

    print(f"Participantes a verificar: {len(participantes)}")
    print(f"Hashtags requeridos:       {hashtags}")
    print(f"Cuenta a etiquetar:        {cuenta_tag}\n")

    if not participantes:
        print("Sin participantes para este día. Fin.")
        sys.exit(0)

    cl = get_client()

    cumplieron = 0
    errores    = 0

    for i, p in enumerate(participantes, 1):
        handle = p["handle"]
        print(f"[{i}/{len(participantes)}] {handle}")

        if i > 1:
            pausa = random.uniform(10, 25)
            print(f"  ⏳ Pausa {pausa:.0f}s...")
            time.sleep(pausa)

        try:
            resultado = verificar_usuario(cl, handle, hashtags, cuenta_tag, ventana_inicio, ventana_limite)
            guardar_resultado(p["id"], fecha_str, resultado)
            if resultado["cumple"]:
                cumplieron += 1
        except Exception as e:
            errores += 1
            print(f"  ✗ Error grave: {e}")
            time.sleep(45)

    duracion = time_mod.time() - inicio
    print(f"\n{'='*55}")
    print(f"Resumen: {cumplieron}/{len(participantes)} cumplieron · {errores} errores · {duracion:.0f}s")
    print(f"{'='*55}\n")

    log_run(fecha_str, len(participantes), cumplieron, errores, duracion)

if __name__ == "__main__":
    main()
