from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
import pandas as pd
import re
import random
import os
import time
from dotenv import load_dotenv
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from itertools import product
import json
from pathlib import Path
dotenv_path = Path('.env')
os.environ.pop("UPAO_USER", None)
os.environ.pop("UPAO_PASS", None)
os.environ.pop("BASE_URL", None)
os.environ.pop("BASE_HORARIOS", None)

# Recargar el archivo .env
load_dotenv(dotenv_path=dotenv_path, override=True)
CURSO_IDS = input("Ingrese IDs de los cursos (ej: ISIA-109,ISIA-110): ").strip().upper().split(',')
PDF_FOLDER = "horarios_generados"
DATA_FOLDER = "data-horatios"
os.makedirs(PDF_FOLDER, exist_ok=True)

CSV_FOLDER = "csv_horarios"
os.makedirs(CSV_FOLDER, exist_ok=True)

# Configura el navegador Brave para usar con Selenium
def setup_brave():
    try:
        print("[+] Configurando navegador Brave...")
        options = webdriver.ChromeOptions()
        options.binary_location = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=options)
    except Exception as e:
        print(f"[-] Error al configurar Brave: {str(e)}")
        raise

# Genera un retraso aleatorio según el contexto (para parecer navegación humana)
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

# Parsea un rango horario tipo "08:00 AM - 10:00 AM" a objetos time de Python
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

# Agrupa las secciones por su ID de liga (ej. T1, P1)
def group_by_liga(secciones):
    grupos = {}
    for sec in secciones:
        liga_base = sec['id_liga'][0]
        liga_num = sec['id_liga'][1:]
        grupos.setdefault(liga_base, {}).setdefault(liga_num, []).append(sec)
    return grupos

# Genera todas las combinaciones posibles por curso, respetando las ligas T1, P1, etc.
def generar_combinaciones_todos_cursos(secciones):

    cursos = {}

    for sec in secciones:
        cursos.setdefault(sec['curso'], []).append(sec)

    combinaciones_por_curso = {}

    for curso, secciones_curso in cursos.items():
        ligas_por_num = {}
        for sec in secciones_curso:
            tipo = sec['id_liga'][0]
            num = sec['id_liga'][1:]
            ligas_por_num.setdefault(num, {}).setdefault(tipo, []).append(sec)

        combinaciones_validas = []
        for num, tipos in ligas_por_num.items():
            partes = list(tipos.values())
            for comb in product(*partes):
                combinaciones_validas.append(comb)
        
        combinaciones_por_curso[curso] = combinaciones_validas

    return list(product(*combinaciones_por_curso.values()))


# Verifica que no haya traslapes de horarios en un horario completo
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

        #obtener bloques únicos
        bloques = sorted({(entry['hora_inicio'], entry['hora_fin']) for entry in horario},
                         key=lambda x: x[0].hour * 60 + x[0].minute)

        #construir tabla vacía
        data = []
        for inicio, fin in bloques:
            fila = [f"{inicio.strftime('%H:%M')} - {fin.strftime('%H:%M')}"] + [""] * len(dias)
            data.append(fila)

        #Rellenar la tabla con los cursos
        for entry in horario:
            bloque_idx = next(i for i, (ini, fin) in enumerate(bloques)
                              if ini == entry['hora_inicio'] and fin == entry['hora_fin'])
            dia_idx = dias.index(entry['dia'])

            styles = getSampleStyleSheet()
            style = styles['Normal']
            style.fontSize = 7
            style.alignment = TA_CENTER

            contenido = f"{entry['curso']}<br/>{entry['id_liga']}<br/>NRC: {entry['nrc']}"
            data[bloque_idx][dia_idx + 1] = Paragraph(contenido, style)

        #Añadir encabezados de días
        data.insert(0, ["Hora"] + dias)

        #Calcular dimensiones disponibles para la tabla
        total_width = width * 0.95
        total_height = height * 0.90

        #Ancho de columnas
        hora_col_width = total_width * 0.15
        dias_col_width = (total_width - hora_col_width) / len(dias)
        col_widths = [hora_col_width] + [dias_col_width] * len(dias)

        #Alto de filas (todas iguales)
        row_height = total_height / len(data)
        row_heights = [row_height] * len(data)

        table = Table(data, colWidths=col_widths, rowHeights=row_heights)

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

        #Calcular tamaño de la tabla
        table_width, table_height = table.wrap(0, 0)

        #Calcular posición centrada
        x = (width - table_width) / 2
        y = (height - table_height) / 2

        #Dibujar la tabla centrada
        table.wrapOn(c, width, height)
        table.drawOn(c, x, y)

        c.save()
    except Exception as e:
        print(f"[-] Error PDF: {str(e)}")
        raise

# Extrae los datos (NRC, ID LIGA, docente, horarios) del detalle del curso
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
                    'curso': curso_id,
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

#Localiza un curso por ID en la tabla principal y extrae su información
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

            # Extraer bloques de cursos
            print("[+] Extrayendo información de los cursos...")
            course_blocks = driver.find_elements(By.XPATH, "//div[@style='border-bottom:0px solid #C0C0C0;margin-bottom:30px;margin-left:5px;']")

            for block in course_blocks:
                try:
                    nrc = block.find_element(By.XPATH, ".//td[contains(text(), 'NRC:')]/b").text.strip()
                    id_liga = block.find_element(By.XPATH, ".//td[contains(text(), 'ID LIGA:')]/b").text.strip()
                    id_docente = block.find_elements(By.XPATH, ".//td[@class='e_fila_table3']")[1].text.strip()
                    docente = block.find_element(By.XPATH, ".//td[@class='e_fila_table4']").text.strip()
                    
                    horarios = []
                    schedule_rows = block.find_elements(By.XPATH, ".//tr[@style='background:#FFFFFF;font-size:12px;']")
                    
                    for row in schedule_rows:
                        columns = row.find_elements(By.TAG_NAME, "td")
                        dia = columns[2].text.strip()
                        hora = columns[3].text.strip()
                        hora_inicio, hora_fin = parse_horario(hora).values()
                        horarios.append({"nrc": nrc, "dia": dia, "hora_inicio": hora_inicio, "hora_fin": hora_fin, "docente": docente})

                    data.append({
                        "curso": CURSO_ID,
                        "nrc": nrc,
                        "id_liga": id_liga,
                        "id_docente": id_docente,
                        "docente": docente,
                        "horarios": horarios
                    })
                except Exception as e:
                    print(f"[-] Error al extraer datos del bloque: {str(e)}")

            os.makedirs(DATA_FOLDER, exist_ok=True)
            json_path = os.path.join(DATA_FOLDER, f"{CURSO_ID}_raw.json")
            with open(json_path, "w", encoding="utf-8") as jf:

                json.dump(data, jf, indent=4, default=str)
            print(f"[+] Datos crudos guardados en JSON: {json_path}")

            return data
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
    
def login_and_navigate(driver):
    try:

        print("[+] Iniciando sesión y navegando...")
        base_url = os.getenv("BASE_URL")
        upao_user = os.getenv("UPAO_USER")
        upao_pass = os.getenv("UPAO_PASS")
        base_horarios = os.getenv("BASE_HORARIOS")

        if not all([base_url, upao_user, upao_pass, base_horarios]):
            raise ValueError("Faltan variables de entorno en el archivo .env")

        driver.get(base_url)

        form_container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table[.//input[@placeholder='usuario']]"))
        )

        username = form_container.find_element(By.XPATH, ".//input[@placeholder='usuario']")
        password = form_container.find_element(By.XPATH, ".//input[@placeholder='contraseña']")
        username.clear()
        username.send_keys(upao_user)
        time.sleep(random.uniform(0.5, 1.5))
        password.clear()
        password.send_keys(upao_pass)
        time.sleep(random.uniform(0.5, 1.5))

        try:
            captcha = form.find_element(By.ID, "imgCaptcha")
            captcha.screenshot("captcha.png")
            code = input("Ingrese CAPTCHA: ")
            form.find_element(By.ID, "txt_img").send_keys(code)
        except:
            pass

        form_container.find_element(By.ID, "btn_valida").click()
        time.sleep(random.uniform(4, 6))

        driver.get(base_horarios)
        time.sleep(random.uniform(5, 7))

        pregrado_link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Horarios de clase pregrado (Trujillo-Piura)')]"))
        )
        pregrado_link.click()
        time.sleep(random.uniform(3, 5))

        print(f"[+] Esperando {random_delay('navegacion')} segundos...")
        time.sleep(random_delay('navegacion'))

        print("[+] Accediendo a ISIA...")
        isia_row = driver.find_element(By.XPATH, "//td[contains(text(), 'ISIA')]/following-sibling::td[1]")

        time.sleep(random.uniform(1.0, 2.5))
        driver.execute_script("arguments[0].click();", isia_row)

        print(f"[+] Esperando {random_delay('carga')} segundos...")
        time.sleep(random_delay('carga'))

        try:
            curso_id = CURSO_ID.strip().upper()
            if not re.match(r'^[A-Z]{4}-\d{3}$', curso_id):
                raise ValueError("Formato inválido. Ejemplo: 'ISIA-112', colocaste: " + CURSO_ID)

            xpath = f"//td[" \
                    f"contains(@onclick, 'f_detalle_cursos') and " \
                    f"span[@class='letra' and normalize-space()='{curso_id}']" \
                    f"]"

            curso_row = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )

            onclick = curso_row.get_attribute('onclick')
            if not onclick.startswith('javascript:f_detalle_cursos'):
                raise ValueError("Elemento no es un curso válido")

            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});
            """, curso_row)

            time.sleep(random.uniform(0.8, 1.2))
            driver.execute_script("arguments[0].click();", curso_row)
            print(f"[+] Clickeando en {curso_id}...")

            WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[@id='id_detalle_cursos']//table[@width='90%;' and @border='0' and @cellpadding='5' and @cellspacing='2' and contains(@class, 'tabla_3')]")
                )
            )
            print("[+] Detalle cargado exitosamente")

            return extract_course_data(driver)

        except Exception as e:
            print(f"[-] Error: {str(e)}")
            driver.save_screenshot("error_screenshot.png")
            return False
    except Exception as e:
        print(f"[-] Error en login: {str(e)}")
        driver.quit()
        raise

def guardar_horarios_csv(horarios, filename):
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

# Orquesta el flujo completo: login, extracción, combinaciones, validación y exportación
def main():
    driver = setup_brave()
    all_secciones = []
    validos = []

    try:
        driver = login_and_navigate(driver)
        
        for curso_id in CURSO_IDS:
            if not re.match(r'^[A-Z]{4}-\d{3}$', curso_id):
                print(f"[-] ID inválido: {curso_id}")
                continue
                
            print(f"\n[+] Procesando curso: {curso_id}")
            curso_data = extract_course_by_id(driver, curso_id)
            
            if curso_data:
                all_secciones.extend(curso_data)
        
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
    
    except Exception as e:
        print(f"[-] Error crítico: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()