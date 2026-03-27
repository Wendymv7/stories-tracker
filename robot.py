import instaloader
from supabase import create_client
from datetime import datetime
import time
import random
import os

# ==========================================
# 1. CREDENCIALES Y CONFIGURACIÓN
# ==========================================
SUPABASE_URL = "TU_URL_DE_SUPABASE"
SUPABASE_KEY = "TU_KEY_DE_SUPABASE"

# Cuenta carnada de Instagram (Solo para el robot)
IG_USER = "TU_CUENTA_CARNADA"
IG_PASS = "TU_CLAVE_CARNADA"

# Conexión a Base de Datos
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. CEREBRO DE CALENDARIO (¿Qué día es hoy?)
# ==========================================
# weekday() devuelve: 0=Lun, 1=Mar, 2=Mié, 3=Jue, 4=Vie, 5=Sáb, 6=Dom
dia_actual = datetime.now().weekday()

# Definimos qué buscar según el día
if dia_actual == 2: # MIÉRCOLES
    ETIQUETA_HOY = "etiqueta_del_miercoles" # <--- Cambia esto
elif dia_actual == 4: # VIERNES
    ETIQUETA_HOY = "mayorgol_"
else:
    # Si lo corres otro día por error, el robot se apaga para no gastar recursos
    print("💤 Hoy no es día de escaneo (Solo Miércoles y Viernes). Apagando robot.")
    exit()

# ==========================================
# 3. MOTOR DEL ROBOT (ANTI-BANEO)
# ==========================================
def iniciar_robot():
    print(f"🤖 Iniciando Robot Santas FC | Buscando: @{ETIQUETA_HOY}")
    L = instaloader.Instaloader()
    
    # ESTRATEGIA DE SESIÓN (Para no alertar a Instagram)
    try:
        # Intenta cargar la sesión guardada previamente
        L.load_session_from_file(IG_USER)
        print("✅ Sesión recuperada desde archivo local.")
    except FileNotFoundError:
        print("⚠️ No hay sesión guardada. Iniciando login manual por única vez...")
        try:
            L.login(IG_USER, IG_PASS)
            L.save_session_to_file() # Guarda la huella digital para la próxima vez
            print("✅ Login exitoso y sesión guardada.")
        except Exception as e:
            print(f"❌ Error crítico en login: {e}")
            return

    # Extraemos a las niñas de la BD
    res = db.table("participantes").select("id, nombre, handle").execute()
    chicas = res.data

    if not chicas:
        print("⚠️ No hay base de datos disponible.")
        return

    print("-" * 40)
    hoy_str = datetime.now().strftime("%Y-%m-%d")

    for chica in chicas:
        ig_handle = chica.get('handle')
        if not ig_handle:
            continue

        print(f"👀 Revisando a: {chica['nombre']} (@{ig_handle})...")
        
        # Antes de entrar a Instagram, vemos si YA le pusimos 'cumplido' hoy
        check = db.table("registros").select("*").eq("participante_id", chica["id"]).eq("fecha", hoy_str).eq("status", "cumplido").execute()
        if check.data:
            print(f"   ⏩ Ya tiene su validación de hoy. Saltando...")
            continue

        try:
            profile = instaloader.Profile.from_username(L.context, ig_handle)
            cumplio = False
            
            # Revisar historias de las últimas 24h
            for story in L.get_stories([profile.userid]):
                for item in story.get_items():
                    # Extraer menciones (etiquetas)
                    menciones = [m.username.lower() for m in item.tagged_users]
                    
                    if ETIQUETA_HOY.lower() in menciones:
                        cumplio = True
                        break
                if cumplio: break

            if cumplio:
                print(f"   🟢 ¡CUMPLIÓ! Etiqueta @{ETIQUETA_HOY} encontrada.")
                db.table("registros").insert({
                    "participante_id": chica["id"], "fecha": hoy_str, "status": "cumplido"
                }).execute()
            else:
                print(f"   🔴 Sin rastro de la etiqueta aún.")

        except Exception as e:
            print(f"   ⚠️ Perfil inaccesible o privado (@{ig_handle}).")
        
        # ⏱️ PAUSA HUMANA ALEATORIA (El secreto Anti-Baneo)
        espera = random.randint(25, 55)
        print(f"   ⏳ Esperando {espera} segundos para simular ser humano...")
        time.sleep(espera)

    print("-" * 40)
    print("🏁 Escaneo finalizado con éxito.")

if __name__ == "__main__":
    iniciar_robot()
