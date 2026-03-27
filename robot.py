import os
import time
from datetime import datetime
from supabase import create_client
from playwright.sync_api import sync_playwright

# Conexión a Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
db = create_client(supabase_url, supabase_key)

IG_USER = os.environ.get("IG_USER")
IG_PASS = os.environ.get("IG_PASS")

def ejecutar_validacion():
    hoy = datetime.now()
    dia_semana = hoy.weekday() 
    etiqueta_esperada = "lajauladelangeloficial" if dia_semana == 2 else "mayorgol_"
    
    res = db.table("participantes").select("*").eq("activa", True).execute()
    participantes = res.data

    with sync_playwright() as p:
        # Usamos un User-Agent de una persona real para evitar bloqueos
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"Intentando entrar a Instagram para {IG_USER}...")
        try:
            page.goto("https://www.instagram.com/accounts/login/", wait_until="networkidle")
            
            # Esperamos hasta 30 segundos (antes eran 10) para que aparezca el cuadro de login
            page.wait_for_selector("input[name='username']", timeout=30000)
            
            page.fill("input[name='username']", IG_USER)
            time.sleep(2)
            page.fill("input[name='password']", IG_PASS)
            time.sleep(1)
            page.click("button[type='submit']")
            
            # Esperamos a que cargue el inicio
            page.wait_for_url("https://www.instagram.com/", timeout=20000)
            print("¡Login exitoso!")
            
        except Exception as e:
            print(f"Error en Login: {e}")
            browser.close()
            return

        for chica in participantes:
            handle = chica["handle"]
            print(f"Escaneando a: @{handle}")
            try:
                page.goto(f"https://www.instagram.com/{handle}/", wait_until="networkidle")
                time.sleep(4)
                
                # Lógica simplificada de detección de historias
                # Si el círculo de historia existe, lo intentamos clickear
                circulo = page.locator("header canvas").first
                estado = "incumplido"
                
                if circulo.is_visible():
                    circulo.click()
                    time.sleep(3)
                    # Buscamos la etiqueta en el texto de la página
                    if etiqueta_esperada.lower() in page.content().lower():
                        estado = "cumplido"
                
                # Guardar en Supabase
                db.table("registros").upsert({
                    "participante_id": chica["id"],
                    "fecha": hoy.strftime("%Y-%m-%d"),
                    "status": estado
                }).execute()
                print(f"Resultado para {handle}: {estado}")
                
            except Exception as e:
                print(f"Error con {handle}: {e}")

        browser.close()

if __name__ == "__main__":
    ejecutar_validacion()
