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
    Busca el perfil usando Selenium y devuelve tanto la URL como el nombre real del perfil.
    """
    query = quote_plus(nombre_completo)
    url_busqueda = f"https://peru.misprofesores.com/Buscar?q={query}"

    print(f"[*] Buscando con Selenium: {url_busqueda}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")

    service = Service(log_path=os.devnull)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url_busqueda)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        resultados = soup.find_all('a', class_='gs-title')
        tokens = nombre_completo.lower().split()

        for link in resultados:
            texto = link.get_text(separator=' ', strip=True)
            href = link.get('href')
            if not href:
                continue

            if 'q=' in href:
                qs = parse_qs(urlparse(href).query)
                real_url = qs.get('q', [None])[0]
            else:
                real_url = href

            if not real_url:
                continue

            coincidencias = sum(1 for token in tokens if token in texto.lower().replace('-', ' '))
            if coincidencias >= 2:
                print(f"[+] Coincidencia con {coincidencias} tokens: {texto}")
                print(f"[+] URL de perfil: {real_url}")
                nombre_limpio = texto.split(" - ")[0].strip()
                return real_url, nombre_limpio

        print("[!] No se encontraron coincidencias.")
        return None, None

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

def guardar_en_json_unico(datos, nombre_docente, nombre_archivo='comentarios.json'):
    """
    Guarda comentarios de varios docentes en un solo archivo JSON de forma acumulativa.
    Cada docente tiene su propia sección y se evita duplicar comentarios.
    """
    if not datos:
        print("[!] No hay datos para guardar.")
        return

    # Crear carpeta si no existe
    carpeta = "horarios-webscraper/comentarios"
    os.makedirs(carpeta, exist_ok=True)
    ruta_archivo = os.path.join(carpeta, nombre_archivo)

    # Filtrar comentarios válidos
    comentarios_validos = []
    omitidos = 0
    for comentario in datos:
        texto = comentario.strip().lower()
        if not texto or "comentario esperando revisión" in texto:
            omitidos += 1
        else:
            comentario_limpio = comentario.replace("\r", " ").replace("\n", " ").strip()
            comentarios_validos.append(comentario_limpio)

    # Cargar datos existentes
    if os.path.exists(ruta_archivo):
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}

    # Si el docente ya existe, extender sin duplicar
    if nombre_docente in data:
        comentarios_anteriores = set(data[nombre_docente]["comentarios"])
    else:
        data[nombre_docente] = {"comentarios": []}
        comentarios_anteriores = set()

    nuevos_comentarios = [c for c in comentarios_validos if c not in comentarios_anteriores]
    data[nombre_docente]["comentarios"].extend(nuevos_comentarios)
    data[nombre_docente]["total_comentarios"] = len(data[nombre_docente]["comentarios"])

    try:
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"\n[SUCCESS] Comentarios guardados en '{ruta_archivo}'")
        print(f"[INFO] Docente: {nombre_docente}")
        print(f"[INFO] Comentarios añadidos: {len(nuevos_comentarios)}")
        print(f"[INFO] Comentarios omitidos (revisión o duplicados): {omitidos}")
    except IOError as e:
        print(f"[ERROR] No se pudo guardar el archivo '{ruta_archivo}': {e}")

# --- EJECUCIÓN PRINCIPAL DEL SCRIPT ---
if __name__ == '__main__':
    # 1. Define el nombre completo que quieres buscar
    nombre_a_buscar = "MORALES SKRABONJA CESAR GUILLERMO" # <--- CAMBIA ESTE VALOR

    # Define las cabeceras para las peticiones HTTP
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 2. Llama a la función de búsqueda para obtener la URL del perfil
    url_del_perfil, nombre_docente_real = buscar_url_perfil(nombre_a_buscar, headers)

    if url_del_perfil:
        print("\n--- Iniciando la extracción de comentarios desde la URL encontrada ---")
        comentarios_totales = extraer_comentarios_con_paginacion(url_del_perfil, headers)

        if comentarios_totales:
            guardar_en_json_unico(comentarios_totales, nombre_docente_real)
    else:
        print("\n[!] Proceso detenido. No se pudo encontrar una URL de perfil para continuar.")
