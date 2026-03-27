import instaloader
from supabase import create_client
from datetime import datetime
import time

# ==========================================
# 1. CONFIGURACIÓN Y CREDENCIALES
# ==========================================
SUPABASE_URL = "TU_URL_DE_SUPABASE"
SUPABASE_KEY = "TU_KEY_DE_SUPABASE"

# Cuenta "robot" de Instagram (¡No uses tu cuenta personal para evitar bloqueos!)
IG_USER = "usuario_del_robot"
IG_PASS = "clave_del_robot"

# La etiqueta que buscamos hoy (sin el @)
ETIQUETA_HOY = "mayorgol_"

# Conexión a la base de datos
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. MOTOR DEL ROBOT (INSTALOADER)
# ==========================================
def iniciar_robot():
    print("🤖 Iniciando Robot Santas FC...")
    L = instaloader.Instaloader()
    
    try:
        L.login(IG_USER, IG_PASS)
        print("✅ Login en Instagram exitoso.")
    except Exception as e:
        print(f"❌ Error al iniciar sesión en IG: {e}")
        return

    # Traemos la lista de niñas desde tu base de datos
    res = db.table("participantes").select("id, nombre, handle").execute()
    chicas = res.data

    if not chicas:
        print("⚠️ No hay niñas registradas en la base de datos.")
        return

    print(f"🔍 Escaneando historias buscando: @{ETIQUETA_HOY}")
    print("-" * 30)

    for chica in chicas:
        ig_handle = chica.get('handle')
        if not ig_handle:
            continue # Si no tiene Instagram, la saltamos

        print(f"Revisando a: {chica['nombre']} (@{ig_handle})...")
        
        try:
            # Descargamos el perfil de la niña
            profile = instaloader.Profile.from_username(L.context, ig_handle)
            cumplio = False
            
            # Revisamos sus historias activas (últimas 24h)
            for story in L.get_stories([profile.userid]):
                for item in story.get_items():
                    # Extraemos los usuarios etiquetados en la historia
                    menciones = [mention.username.lower() for mention in item.tagged_users]
                    
                    if ETIQUETA_HOY.lower() in menciones:
                        cumplio = True
                        break # Si ya la encontró, dejamos de buscar en esta historia
                if cumplio:
                    break # Pasamos a la siguiente niña

            # Si cumplió, guardamos en la base de datos
            if cumplio:
                print(f"   🟢 ¡CUMPLIÓ! Etiqueta encontrada.")
                # Verificamos si ya le habíamos puesto "cumplido" hoy para no duplicar
                hoy = datetime.now().strftime("%Y-%m-%d")
                check = db.table("registros").select("*").eq("participante_id", chica["id"]).eq("fecha", hoy).eq("status", "cumplido").execute()
                
                if not check.data:
                    db.table("registros").insert({
                        "participante_id": chica["id"],
                        "fecha": hoy,
                        "status": "cumplido"
                    }).execute()
            else:
                print(f"   🔴 No se encontró la etiqueta aún.")

        except Exception as e:
            print(f"   ⚠️ Error leyendo a @{ig_handle}: Perfil privado o no existe.")
        
        # ⏱️ PAUSA TÉCNICA: Vital para que Instagram no nos bloquee la IP
        time.sleep(15) 

    print("-" * 30)
    print("🏁 Escaneo finalizado.")

# ==========================================
# 3. EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    iniciar_robot()
