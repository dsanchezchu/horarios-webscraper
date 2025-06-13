import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, quote_plus
import unicodedata

base_busqueda_url = 'https://peru.misprofesores.com' 


def buscar_url_perfil(nombre_completo, cabeceras):
    """
    Busca un nombre en el sitio y devuelve la URL del primer resultado.
    """
    # Formatear el nombre para la query de la URL (ej: "Juan Pérez" -> "Juan+Pérez")
    query_formateada = quote_plus(nombre_completo)
    url_de_busqueda = f"{base_busqueda_url}/Buscar?q={query_formateada}"
    
    print(f"[*] Buscando perfil para: '{nombre_completo}'")
    print(f"[*] URL de búsqueda: {url_de_busqueda}")

    try:
        response = requests.get(url_de_busqueda, headers=cabeceras)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- LÓGICA PARA ENCONTRAR EL LINK ---
        # 1. Encontrar el primer div con la clase 'gs-title'
        div_resultado = soup.find('div', class_='gs-title')
        
        if div_resultado:
            # 2. Dentro de ese div, encontrar el enlace 'a' con la clase 'gs-title'
            link_tag = div_resultado.find('a', class_='gs-title')
            
            if link_tag and link_tag.has_attr('href'):
                # Extraer el texto completo de la etiqueta <a>
                texto_a = link_tag.get_text(separator=' ', strip=True)
                # Extraer todos los textos de las etiquetas <b> dentro de <a>
                textos_b = [b_tag.get_text(strip=True) for b_tag in link_tag.find_all('b')]
                # Unir los textos de <b> para comparar con el nombre buscado
                texto_b_unido = ' '.join(textos_b)
                # Extraer el texto fuera de <b> (nombres intermedios y apellidos intermedios)
                partes = []
                for elem in link_tag.contents:
                    if hasattr(elem, 'name') and elem.name == 'b':
                        partes.append(elem.get_text(strip=True))
                    elif isinstance(elem, str):
                        # Puede haber espacios, nombres intermedios, apellidos intermedios, guiones, etc.
                        partes.extend([p for p in elem.strip().split() if p and p != '-'])
                # Reconstruir el nombre completo detectado (ignorando el texto después del guion)
                if '-' in partes:
                    idx = partes.index('-')
                    partes = partes[:idx]
                nombre_detectado = ' '.join(partes)
                # Comprobar si el nombre buscado está contenido (ignorando mayúsculas/minúsculas y tildes)
                def normalizar(s):
                    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()
                if normalizar(nombre_completo) != normalizar(nombre_detectado):
                    print(f"[!] El nombre detectado ('{nombre_detectado}') no coincide exactamente con el nombre buscado ('{nombre_completo}').")
                nombre_variantes = [
                    nombre_completo,
                    nombre_completo.upper(),
                    nombre_completo.lower(),
                    nombre_completo.title(),
                    nombre_completo.capitalize(),
                    nombre_detectado
                ]
                if not any(var in texto_a or var in texto_b_unido for var in nombre_variantes):
                    print(f"[!] El texto encontrado ('{texto_a}') no coincide exactamente con ninguna variante del nombre buscado.")
                print(f"[+] ¡Coincidencia encontrada!: '{texto_a}'")
                href = link_tag['href']
                # Construye la URL absoluta por si el href es relativo (ej. /perfil/123)
                url_absoluta = urljoin(url_de_busqueda, href)
                print(f"[+] URL de perfil obtenida: {url_absoluta}")
                return url_absoluta

        print(f"[!] No se encontró ninguna coincidencia para '{nombre_completo}' con la estructura esperada.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Falló la petición de búsqueda: {e}")
        return None

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
    Guarda una lista de datos en un archivo JSON.
    (Esta función no cambia)
    """
    if not datos:
        print("[!] No hay datos para guardar.")
        return
    output_data = {'total_comentarios': len(datos), 'comentarios': datos}
    try:
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"\n[SUCCESS] Proceso completado. Datos guardados en '{nombre_archivo}'")
    except IOError as e:
        print(f"[ERROR] No se pudo escribir en el archivo '{nombre_archivo}': {e}")


# --- EJECUCIÓN PRINCIPAL DEL SCRIPT ---
if __name__ == '__main__':
    # 1. Define el nombre completo que quieres buscar
    nombre_a_buscar = "Armando Javier Caballero Alvarado" # <--- CAMBIA ESTE VALOR

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
