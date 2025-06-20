import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, quote_plus
import unicodedata
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import os


def buscar_url_perfil(nombre_completo, _):
    """
    Busca el perfil usando Selenium, ya que el contenido se carga vía JavaScript (Google CSE).
    """
    query = quote_plus(nombre_completo)
    url_busqueda = f"https://peru.misprofesores.com/Buscar?q={query}"

    print(f"[*] Buscando con Selenium: {url_busqueda}")

    # Configuración de Chrome en modo headless y silencioso
    options = Options()
    options.add_argument("--headless=new")  # Usa "--headless" si tienes problemas
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")  # Silencia advertencias/info de Chromium

    # Redirigir los logs del servicio a NUL (en Windows); en Linux usar "/dev/null"
    service = Service(log_path=os.devnull)

    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url_busqueda)
        time.sleep(3)  # Esperar a que cargue el contenido dinámico

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        resultados = soup.find_all('a', class_='gs-title')
        tokens = nombre_completo.lower().split()

        for link in resultados:
            texto = link.get_text(separator=' ', strip=True).lower()
            href = link.get('href')
            if not href:
                continue

            # Extraer URL real si viene con q=
            if 'q=' in href:
                qs = parse_qs(urlparse(href).query)
                real_url = qs.get('q', [None])[0]
            else:
                real_url = href

            if not real_url:
                continue

            coincidencias = sum(1 for token in tokens if token in texto.replace('-', ' '))
            if coincidencias >= 2:
                print(f"[+] Coincidencia con {coincidencias} tokens: {texto}")
                print(f"[+] URL de perfil: {real_url}")
                return real_url

        print("[!] No se encontraron coincidencias.")
        return None

    finally:
        driver.quit()

def extraer_comentarios_con_paginacion(start_url, cabeceras):
    """
    Recorre la paginación de un sitio para extraer todos los comentarios.
    (Esta función no cambia respecto a la versión anterior)
    """
    todos_los_comentarios = []
    url_actual = start_url

    while url_actual:
        print(f"[*] Haciendo scraping en la página: {url_actual}")
        try:
            response = requests.get(url_actual, headers=cabeceras)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            comentarios_tags = soup.find_all('p', class_='commentsParagraph')
            comentarios_pagina = [tag.get_text(strip=True) for tag in comentarios_tags]
            
            if comentarios_pagina:
                print(f"[+] Se encontraron {len(comentarios_pagina)} comentarios en esta página.")
                todos_los_comentarios.extend(comentarios_pagina)
            else:
                print("[!] No se encontraron comentarios en esta página.")

            siguiente_url = None
            pagination_ul = soup.find('ul', class_='pagination')
            if pagination_ul:
                active_li = pagination_ul.find('li', class_='active')
                if active_li:
                    next_li = active_li.find_next_sibling('li')
                    if next_li and next_li.find('a') and next_li.find('a').has_attr('href'):
                        href = next_li.find('a')['href']
                        siguiente_url = urljoin(url_actual, href)
                        print(f"[*] Página siguiente encontrada: {siguiente_url}")
            
            url_actual = siguiente_url
            if url_actual:
                time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ocurrió un error en la petición a {url_actual}: {e}")
            break
    return todos_los_comentarios

def guardar_en_json(datos, nombre_archivo):
    """
    Guarda una lista de datos en un archivo JSON dentro de la carpeta 'comentarios',
    omitiendo los comentarios en revisión y eliminando saltos de línea.
    """
    if not datos:
        print("[!] No hay datos para guardar.")
        return

    comentarios_validos = []
    omitidos = 0

    for comentario in datos:
        texto = comentario.strip().lower()
        if not texto or "comentario esperando revisión" in texto:
            omitidos += 1
        else:
            comentario_limpio = comentario.replace("\r", " ").replace("\n", " ").strip()
            comentarios_validos.append(comentario_limpio)

    output_data = {
        'total_comentarios': len(comentarios_validos),
        'comentarios': comentarios_validos
    }

    # Crear la carpeta 'comentarios' si no existe
    carpeta = "comentarios"
    os.makedirs(carpeta, exist_ok=True)

    # Ruta completa del archivo
    ruta_archivo = os.path.join(carpeta, nombre_archivo)

    try:
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"\n[SUCCESS] Proceso completado. Datos guardados en '{ruta_archivo}'")
        print(f"[INFO] Se omitieron {omitidos} comentario(s) en revisión.")
    except IOError as e:
        print(f"[ERROR] No se pudo escribir en el archivo '{ruta_archivo}': {e}")

# --- EJECUCIÓN PRINCIPAL DEL SCRIPT ---
if __name__ == '__main__':
    # 1. Define el nombre completo que quieres buscar
    nombre_a_buscar = "Armando Caballero" # <--- CAMBIA ESTE VALOR

    # Define las cabeceras para las peticiones HTTP
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 2. Llama a la función de búsqueda para obtener la URL del perfil
    url_del_perfil = buscar_url_perfil(nombre_a_buscar, headers)
    
    # 3. Si se encontró una URL, procede a extraer los comentarios
    if url_del_perfil:
        print("\n--- Iniciando la extracción de comentarios desde la URL encontrada ---")
        comentarios_totales = extraer_comentarios_con_paginacion(url_del_perfil, headers)
        
        # 4. Guarda los resultados en un archivo JSON
        if comentarios_totales:
            # Crea un nombre de archivo dinámico basado en el nombre buscado
            nombre_archivo_json = f"comentarios_{nombre_a_buscar.replace(' ', '_').lower()}.json"
            guardar_en_json(comentarios_totales, nombre_archivo_json)
    else:
        print("\n[!] Proceso detenido. No se pudo encontrar una URL de perfil para continuar.")
