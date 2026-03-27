import instaloader
from supabase import create_client
from datetime import datetime
import time
import random
import os

# ==========================================
# 1. CREDENCIALES DESDE GITHUB SECRETS
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
IG_USER = os.environ.get("IG_USER")
IG_PASS = os.environ.get("IG_PASS")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. CEREBRO DE CALENDARIO (Hora Colombia)
# ==========================================
# Se ejecuta en servidores UTC, pero validamos el día
dia_actual = datetime.now().weekday()

if dia_actual in [1, 2]: # Martes o Miércoles
    ETIQUETA_HOY = "etiqueta_miercoles" # <--- ¡CÁMBIA ESTO POR LA DEL MIÉRCOLES!
elif dia_actual in [3, 4]: # Jueves o Viernes
    ETIQUETA_HOY = "mayorgol_"
else:
    print("💤 Hoy no es día de escaneo. Apagando robot.")
    exit()

# ==========================================
# 3. MOTOR DEL ROBOT
# ==========================================
def iniciar_robot():
    print(f"🤖 Iniciando Robot Santas FC | Buscando: @{ETIQUETA_HOY}")
    L = instaloader.Instaloader()
    
    try:
        print("Intentando login en Instagram...")
        L.login(IG_USER, IG_PASS)
        print("✅ Login exitoso.")
    except Exception as e:
        print(f"❌ Error crítico en login: {e}")
        return

    res = db.table("participantes").select("id, nombre, handle").execute()
    chicas = res.data

    if not chicas:
        print("⚠️ No hay base de datos disponible.")
        return

    hoy_str = datetime.now().strftime("%Y-%m-%d")
    print("-" * 40)

    for chica in chicas:
        ig_handle = chica.get('handle')
        if not ig_handle: continue

        print(f"👀 Revisando a: {chica['nombre']} (@{ig_handle})...")
        
        # Validar si ya tiene el 'cumplido'
        check = db.table("registros").select("*").eq("participante_id", chica["id"]).eq("fecha", hoy_str).eq("status", "cumplido").execute()
        if check.data:
            print(f"   ⏩ Ya cumplió hoy. Saltando...")
            continue

        try:
            profile = instaloader.Profile.from_username(L.context, ig_handle)
            cumplio = False
            
            for story in L.get_stories([profile.userid]):
                for item in story.get_items():
                    menciones = [m.username.lower() for m in item.tagged_users]
                    if ETIQUETA_HOY.lower() in menciones:
                        cumplio = True; break
                if cumplio: break

            if cumplio:
                print(f"   🟢 ¡CUMPLIÓ! Etiqueta @{ETIQUETA_HOY} encontrada.")
                db.table("registros").insert({"participante_id": chica["id"], "fecha": hoy_str, "status": "cumplido"}).execute()
            else:
                print(f"   🔴 Sin rastro de la etiqueta aún.")

        except Exception as e:
            print(f"   ⚠️ Perfil privado o error: @{ig_handle}")
        
        # Pausa aleatoria anti-baneo
        espera = random.randint(15, 35)
        print(f"   ⏳ Pausa anti-robot: {espera}s...")
        time.sleep(espera)

    print("-" * 40)
    print("🏁 Escaneo finalizado.")

if __name__ == "__main__":
    iniciar_robot()
