from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm  # Importar cm
from datetime import datetime
from itertools import product
import pandas as pd
import re
import random
import os
import time
from dotenv import load_dotenv
import json

# Configuración inicial
load_dotenv()
PDF_FOLDER = "horarios_generados"
os.makedirs(PDF_FOLDER, exist_ok=True)
DATA_FOLDER = "data-horarios"
os.makedirs(DATA_FOLDER, exist_ok=True)

CSV_FOLDER = "csv_horarios"
os.makedirs(CSV_FOLDER, exist_ok=True)

def setup_chrome():
    try:
        print("[+] Configurando navegador Chrome (Linux)...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Opcional: sin interfaz gráfica
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        return webdriver.Chrome(options=options)
    except Exception as e:
        print(f"[-] Error al configurar Chrome: {str(e)}")
        raise

def random_delay(context):
    delays = {
        'navegacion': random.uniform(2, 4),
        'carga': random.uniform(1, 3),
        'combinaciones': random.uniform(1, 2),
        'extraccion': random.uniform(0.5, 1.5)
    }
    delay = delays.get(context, random.uniform(1, 3))
    print(f"[+] Retraso de {delay:.2f} segundos para {context}")
    return delay

def parse_horario(hora_str):
    try:
        formato = "%I:%M %p"
        inicio, fin = hora_str.split(' - ')
        return {
            'inicio': datetime.strptime(inicio, formato).time(),
            'fin': datetime.strptime(fin, formato).time()
        }
    except Exception as e:
        print(f"[-] Error al parsear horario: {str(e)}")
        raise

def group_by_liga(secciones):
    grupos = {}
    for sec in secciones:
        liga_base = sec['id_liga'][0]  # Extraer la parte base (T, P, L)
        liga_num = sec['id_liga'][1:]  # Extraer el número (1, 2, 3)
        grupos.setdefault(liga_base, {}).setdefault(liga_num, []).append(sec)
    return grupos

def generar_combinaciones_todos_cursos(secciones):
    from itertools import product

    cursos = {}

    # Agrupar secciones por curso
    for sec in secciones:
        cursos.setdefault(sec['curso'], []).append(sec)

    combinaciones_por_curso = {}

    for curso, secciones_curso in cursos.items():
        # Agrupar por número de liga: L1, T1, P1 => grupo 1, etc.
        ligas_por_num = {}
        for sec in secciones_curso:
            tipo = sec['id_liga'][0]  # L, T, P
            num = sec['id_liga'][1:]  # 1, 2, 3...
            ligas_por_num.setdefault(num, {}).setdefault(tipo, []).append(sec)

        # Generar combinaciones dentro del curso, respetando cada grupo de liga
        combinaciones_validas = []
        for num, tipos in ligas_por_num.items():
            partes = list(tipos.values())  # listas de secciones por tipo
            for comb in product(*partes):
                combinaciones_validas.append(comb)
        
        combinaciones_por_curso[curso] = combinaciones_validas

    # Ahora combinar entre cursos
    return list(product(*combinaciones_por_curso.values()))


def is_horario_valido(horario):
    df = pd.DataFrame(horario).sort_values(['dia', 'hora_inicio'])
    for dia, grupo in df.groupby('dia'):
        times = grupo[['hora_inicio', 'hora_fin']].sort_values('hora_inicio')
        for i in range(1, len(times)):
            if times.iloc[i]['hora_inicio'] < times.iloc[i-1]['hora_fin']:
                return False
    return True

def crear_pdf(horario, filename):
    try:
        # Definir tamaño A4 horizontal
        A4_HORIZONTAL = (A4[1], A4[0])  # Intercambiar ancho y alto
        c = canvas.Canvas(filename, pagesize=A4_HORIZONTAL)
        width, height = A4_HORIZONTAL

        # Crear tabla semanal
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
        dias_abreviados = {'LUN': 'Lunes', 'MAR': 'Martes', 'MIE': 'Miércoles',
                           'JUE': 'Jueves', 'VIE': 'Viernes', 'SAB': 'Sábado'}

        # Convertir días abreviados a completos
        for entry in horario:
            entry['dia'] = dias_abreviados.get(entry['dia'], entry['dia'])

        # Obtener horas únicas y ordenadas
        horas = sorted({h['hora_inicio'] for h in horario}, key=lambda t: t.hour * 60 + t.minute)

        # Crear datos para la tabla
        data = [[f"{h.strftime('%H:%M')}"] + [""] * len(dias) for h in horas]

        # Llenar la tabla con los horarios
        for entry in horario:
            hora_idx = horas.index(entry['hora_inicio'])
            dia_idx = dias.index(entry['dia'])
            info = f"{entry['curso']}\n{entry['id_liga']}\n{entry['docente']}\nNRC: {entry['nrc']}"
            data[hora_idx][dia_idx + 1] = info  # +1 porque la primera columna es la hora

        # Añadir encabezados de días
        data.insert(0, ["Hora"] + dias)

        # Calcular dimensiones disponibles para la tabla
        total_width = width * 0.95  # 95% del ancho
        total_height = height * 0.90  # 90% de la altura

        # Ancho de columnas
        hora_col_width = total_width * 0.15  # 15% para "Hora"
        dias_col_width = (total_width - hora_col_width) / len(dias)
        col_widths = [hora_col_width] + [dias_col_width] * len(dias)

        # Alto de filas (todas iguales)
        row_height = total_height / len(data)
        row_heights = [row_height] * len(data)

        # Crear tabla
        table = Table(data, colWidths=col_widths, rowHeights=row_heights)

        # Estilos
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        # Calcular tamaño de la tabla
        table_width, table_height = table.wrap(0, 0)

        # Calcular posición centrada
        x = (width - table_width) / 2
        y = (height - table_height) / 2

        # Dibujar la tabla centrada
        table.wrapOn(c, width, height)
        table.drawOn(c, x, y)

        # Guardar PDF
        c.save()
    except Exception as e:
        print(f"[-] Error PDF: {str(e)}")
        raise

def extract_course_data(driver, curso_id):
    data = []
    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "id_detalle_cursos"))
        )
        course_blocks = driver.find_elements(By.XPATH, "//div[contains(@style, 'border-bottom:0px solid #C0C0C0')]")
        
        for block in course_blocks:
            try:
                nrc = block.find_element(By.XPATH, ".//td[contains(text(), 'NRC:')]/b").text.strip()
                id_liga = block.find_element(By.XPATH, ".//td[contains(text(), 'ID LIGA:')]/b").text.strip()
                docente = block.find_element(By.XPATH, ".//td[@class='e_fila_table4']").text.strip()
                
                horarios = []
                schedule_rows = block.find_elements(By.XPATH, ".//tr[contains(@style, 'background:#FFFFFF')]")
                for row in schedule_rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    dia = cols[2].text.strip()
                    hora = cols[3].text.strip()
                    parsed = parse_horario(hora)
                    horarios.append({
                        'dia': dia,
                        'hora_inicio': parsed['inicio'],
                        'hora_fin': parsed['fin']
                    })
                
                data.append({
                    'curso': curso_id,  # Actualizar para múltiples cursos
                    'nrc': nrc,
                    'id_liga': id_liga,
                    'docente': docente,
                    'horarios': horarios
                })
            except Exception as e:
                print(f"[-] Error en bloque: {str(e)}")
        return data
    except Exception as e:
        print(f"[-] Error extrayendo {curso_id}: {str(e)}")
        return []

def extract_course_by_id(driver, curso_id):
    try:
        print(f"[+] Buscando curso: {curso_id}...")
        
        # XPath optimizado con validación de contenido y atributos
        xpath = f"//td[" \
                f"contains(@onclick, 'f_detalle_cursos') and " \
                f"span[@class='letra' and normalize-space()='{curso_id}']" \
                f"]"
        
        # Esperar hasta 20 segundos por el elemento
        curso_row = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        
        # Verificar validez del elemento
        onclick = curso_row.get_attribute('onclick')
        if not onclick.startswith('javascript:f_detalle_cursos'):
            raise ValueError(f"[-] Elemento inválido para {curso_id}")
        
        # Scroll y clic con JavaScript
        driver.execute_script("""
            arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});
            arguments[0].click();
        """, curso_row)
        
        # Esperar carga del detalle del curso
        try:
            WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[@id='id_detalle_cursos']//table[contains(@class, 'tabla_3')]")
                )
            )
        except:
            print(f"[-] Timeout cargando detalle de {curso_id}")
            driver.save_screenshot(f"error_{curso_id}.png")
            return []
        
        # Extraer datos
        data = extract_course_data(driver, curso_id)
        
        # Volver a la lista de cursos
        driver.execute_script("window.location.href = 'javascript:f_show_three();'")
        time.sleep(random_delay('navegacion'))
        
        return data

    except Exception as e:
        print(f"[-] Error procesando {curso_id}: {str(e)}")
        return []
    
def abrir_login_y_guardar_captcha(user, password, base_url):
    driver = setup_chrome()
    driver.get(base_url)
    form = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//table[.//input[@placeholder='usuario']]"))
    )
    form.find_element(By.XPATH, ".//input[@placeholder='usuario']").send_keys(user)
    form.find_element(By.XPATH, ".//input[@placeholder='contraseña']").send_keys(password)
    captcha = form.find_element(By.ID, "imgCaptcha")
    captcha_path = "captcha.png"
    captcha.screenshot(captcha_path)
    # NO hagas nada más aquí, no recargues ni cambies de página
    return driver, captcha_path

def login_and_navigate(driver, captcha_code, base_horarios):
    # Usa el mismo driver y DOM, solo llena el captcha y haz click
    form = driver.find_element(By.XPATH, "//table[.//input[@placeholder='usuario']]")
    form.find_element(By.ID, "txt_img").send_keys(captcha_code)
    form.find_element(By.ID, "btn_valida").click()
    time.sleep(random_delay('navegacion'))

    driver.get(base_horarios)
    pregrado = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Horarios de clase pregrado')]"))
    )
    pregrado.click()
    time.sleep(random_delay('carga'))

    isia = driver.find_element(By.XPATH, "//td[contains(text(), 'ISIA')]/following-sibling::td[1]")
    driver.execute_script("arguments[0].click();", isia)
    time.sleep(random_delay('carga'))
    return driver

def run_horario_scraper(user, password, curso_ids, base_url, base_horarios, driver):
    PDF_FOLDER = "horarios_generados"
    os.makedirs(PDF_FOLDER, exist_ok=True)
    DATA_FOLDER = "data-horarios"
    os.makedirs(DATA_FOLDER, exist_ok=True)
    CSV_FOLDER = "csv_horarios"
    os.makedirs(CSV_FOLDER, exist_ok=True)

    all_secciones = []
    validos = []

    try:
        for curso_id in curso_ids:
            if not re.match(r'^[A-Z]{4}-\d{3}$', curso_id):
                print(f"[-] ID inválido: {curso_id}")
                continue
            print(f"\n[+] Procesando curso: {curso_id}")
            curso_data = extract_course_by_id(driver, curso_id)
            if curso_data:
                all_secciones.extend(curso_data)
                json_path = os.path.join(DATA_FOLDER, f"{curso_id}.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(curso_data, f, ensure_ascii=False, indent=2, default=str)
                print(f"[+] Datos de {curso_id} guardados en {json_path}")
        combinaciones = generar_combinaciones_todos_cursos(all_secciones)
        print(f"[+] {len(combinaciones)} combinaciones encontradas")
        for comb in combinaciones:
            horario = []
            for grupo in comb:
                for sec in grupo:
                    for h in sec['horarios']:
                        horario.append({
                            'curso': sec['curso'],
                            'id_liga': sec['id_liga'],
                            'nrc': sec['nrc'],
                            'dia': h['dia'],
                            'hora_inicio': h['hora_inicio'],
                            'hora_fin': h['hora_fin'],
                            'docente': sec['docente']
                        })
            if is_horario_valido(horario):
                validos.append(horario)
                if len(validos) >= 100:
                    break
        print(f"[+] {len(validos)} horarios válidos generados")
        for i, horario in enumerate(validos[:20]):
            filename = os.path.join(PDF_FOLDER, f"horario_valido_{i+1}.pdf")
            crear_pdf(horario, filename)
        csv_filename = os.path.join(CSV_FOLDER, "horarios_validos.csv")
        guardar_horarios_csv(validos, csv_filename)
        return True, f"Proceso completado. PDFs y CSV generados en las carpetas correspondientes."
    except Exception as e:
        print(f"[-] Error crítico: {str(e)}")
        return False, str(e)
    finally:
        if driver and hasattr(driver, "quit"):
            driver.quit()

def guardar_horarios_csv(horarios, filename):
    try:
        # Crear una lista de diccionarios para cada entrada de horario
        rows = []
        for idx, horario in enumerate(horarios, start=1):
            for entry in horario:
                rows.append({
                    '#horario': idx,
                    'Curso': entry['curso'],
                    'ID Liga': entry['id_liga'],
                    'NRC': entry['nrc'],
                    'Día': entry['dia'],
                    'Hora Inicio': entry['hora_inicio'].strftime('%H:%M'),
                    'Hora Fin': entry['hora_fin'].strftime('%H:%M'),
                    'Docente': entry['docente']
                })
        
        # Crear un DataFrame y exportarlo a CSV
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"[+] Horarios guardados en {filename}")
    except Exception as e:
        print(f"[-] Error al guardar CSV: {str(e)}")
        raise