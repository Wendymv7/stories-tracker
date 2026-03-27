import os
import time
from datetime import datetime
from supabase import create_client
from playwright.sync_api import sync_playwright

# 1. Conexión a Supabase usando variables de entorno (GitHub Secrets)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
db = create_client(supabase_url, supabase_key)

# 2. Credenciales de Instagram
IG_USER = os.environ.get("IG_USER")
IG_PASS = os.environ.get("IG_PASS")

def ejecutar_validacion():
    hoy = datetime.now()
    dia_semana = hoy.weekday() # 2 es Miércoles, 4 es Viernes
    
    # Determinar la etiqueta según el día
    etiqueta_esperada = ""
    if dia_semana == 2: # Miércoles
        etiqueta_esperada = "lajauladelangeloficial"
        print("Ejecutando escaneo de Miércoles. Etiqueta:", etiqueta_esperada)
    elif dia_semana == 4: # Viernes
        etiqueta_esperada = "mayorgol_"
        print("Ejecutando escaneo de Viernes. Etiqueta:", etiqueta_esperada)
    else:
        print("Hoy no es día de validación programada.")
        return

    # Obtener participantes activas del CRM
    res = db.table("participantes").select("*").eq("activa", True).execute()
    participantes = res.data

    if not participantes:
        print("No hay participantes activas.")
        return

    print("Iniciando navegador Playwright...")
    with sync_playwright() as p:
        # Lanzamos el navegador
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        # Login en Instagram
        print(f"Iniciando sesión con {IG_USER}...")
        page.goto("https://www.instagram.com/accounts/login/")
        page.wait_for_selector("input[name='username']", timeout=10000)
        page.fill("input[name='username']", IG_USER)
        page.fill("input[name='password']", IG_PASS)
        page.click("button[type='submit']")
        page.wait_for_url("https://www.instagram.com/", timeout=15000)
        print("¡Login exitoso!")
        time.sleep(3) # Pausa por seguridad anti-bot

        # Escanear a cada jugadora/modelo
        for chica in participantes:
            handle = chica["handle"]
            print(f"Revisando historias de: @{handle}")
            
            try:
                page.goto(f"https://www.instagram.com/{handle}/")
                time.sleep(3)
                
                estado = "incumplido"
                
                # Buscar si hay un elemento de historia (el aro de color)
                # Nota: La estructura del DOM de Instagram cambia, usamos selectores genéricos de historia
                historia_disponible = page.locator("div[role='button']:has(canvas)").count() > 0
                
                if historia_disponible:
                    page.locator("div[role='button']:has(canvas)").first.click()
                    time.sleep(2)
                    
                    # Recorrer historias de las últimas 24h
                    while True:
                        texto_pantalla = page.locator("body").inner_text()
                        if etiqueta_esperada.lower() in texto_pantalla.lower():
                            estado = "cumplido"
                            print(f"✅ Etiqueta encontrada en @{handle}")
                            break
                        
                        # Intentar pasar a la siguiente historia
                        next_btn = page.locator("button[aria-label='Siguiente']")
                        if next_btn.is_visible():
                            next_btn.click()
                            time.sleep(1)
                        else:
                            print(f"❌ Historias revisadas, etiqueta no encontrada para @{handle}")
                            break
                else:
                    print(f"⚠️ @{handle} no tiene historias publicadas.")
            except Exception as e:
                print(f"Error revisando a @{handle}: {e}")
                estado = "incumplido"

            # Guardar el registro en Supabase
            fecha_str = hoy.strftime("%Y-%m-%d")
            registro = {
                "participante_id": chica["id"],
                "fecha": fecha_str,
                "status": estado
            }
            # Usamos upsert por si el robot corre dos veces el mismo día
            db.table("registros").upsert(registro, on_conflict="participante_id, fecha").execute()

        browser.close()
        print("✅ Proceso de validación finalizado con éxito.")

if __name__ == "__main__":
    ejecutar_validacion()
