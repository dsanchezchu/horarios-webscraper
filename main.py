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

# Configuración inicial
load_dotenv()
CURSO_IDS = input("Ingrese IDs de los cursos (ej: ISIA-109,ISIA-110): ").strip().upper().split(',')
PDF_FOLDER = "horarios_generados"
os.makedirs(PDF_FOLDER, exist_ok=True)

def setup_brave():
    try:
        print("[+] Configurando navegador Brave...")
        options = webdriver.ChromeOptions()
        options.binary_location = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")  # Desactivar GPU
        options.add_argument("--no-sandbox")  # Modo sin sandbox
        options.add_argument("--disable-dev-shm-usage")  # Evitar problemas de memoria
        return webdriver.Chrome(options=options)
    except Exception as e:
        print(f"[-] Error al configurar Brave: {str(e)}")
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

    # Agrupar secciones por curso
    cursos = {}
    for sec in secciones:
        cursos.setdefault(sec['curso'], []).append(sec)
    
    # Generar todas las combinaciones posibles
    combinaciones = list(product(*cursos.values()))
    return combinaciones

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
            info = f"{entry['curso']}\n{entry['id_liga']}\n{entry['docente']}\nNRC: {entry['nrc']}"  # Incluir NRC
            data[hora_idx][dia_idx + 1] = info  # +1 porque la primera columna es la hora
        
        # Añadir encabezados de días
        data.insert(0, ["Hora"] + dias)
        
        # Crear la tabla
        table = Table(data, colWidths=[2 * cm] + [5 * cm] * len(dias))  # Ancho de columnas
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (0, 0), (0, 0)),
        ]))
        
        # Dibujar la tabla en el PDF
        table.wrapOn(c, width, height)
        table.drawOn(c, 2 * cm, height - (len(data) + 1) * 2 * cm)  # Ajustar posición
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
    
def login_and_navigate(driver):
    try:
        driver.get(os.getenv("BASE_URL"))
        form = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table[.//input[@placeholder='usuario']]"))
        )
        form.find_element(By.XPATH, ".//input[@placeholder='usuario']").send_keys(os.getenv("UPAO_USER"))
        form.find_element(By.XPATH, ".//input[@placeholder='contraseña']").send_keys(os.getenv("UPAO_PASS"))
        
        try:
            captcha = form.find_element(By.ID, "imgCaptcha")
            captcha.screenshot("captcha.png")
            code = input("Ingrese CAPTCHA: ")
            form.find_element(By.ID, "txt_img").send_keys(code)
        except:
            pass
        
        form.find_element(By.ID, "btn_valida").click()
        time.sleep(random_delay('navegacion'))
        
        driver.get(os.getenv("BASE_HORARIOS"))
        pregrado = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Horarios de clase pregrado')]"))
        )
        pregrado.click()
        time.sleep(random_delay('carga'))
        
        isia = driver.find_element(By.XPATH, "//td[contains(text(), 'ISIA')]/following-sibling::td[1]")
        driver.execute_script("arguments[0].click();", isia)
        time.sleep(random_delay('carga'))
        
        return driver
    except Exception as e:
        print(f"[-] Error en login: {str(e)}")
        driver.quit()
        raise

def main():
    driver = setup_brave()
    all_secciones = []
    
    try:
        # Login y navegación inicial
        driver = login_and_navigate(driver)
        
        # Procesar cada curso
        for curso_id in CURSO_IDS:
            if not re.match(r'^[A-Z]{4}-\d{3}$', curso_id):
                print(f"[-] ID inválido: {curso_id}")
                continue
                
            print(f"\n[+] Procesando curso: {curso_id}")
            curso_data = extract_course_by_id(driver, curso_id)
            
            if curso_data:
                all_secciones.extend(curso_data)
        
        # Generar combinaciones de todos los cursos
        combinaciones = generar_combinaciones_todos_cursos(all_secciones)
        print(f"[+] {len(combinaciones)} combinaciones encontradas")
        
        # Generar horarios válidos
        validos = []
        for comb in combinaciones:
            horario = []
            for sec in comb:
                for h in sec['horarios']:
                    horario.append({
                        'curso': sec['curso'],
                        'id_liga': sec['id_liga'],
                        'nrc': sec['nrc'],  # Incluir NRC
                        'dia': h['dia'],
                        'hora_inicio': h['hora_inicio'],
                        'hora_fin': h['hora_fin'],
                        'docente': sec['docente']
                    })
            if is_horario_valido(horario):
                validos.append(horario)
                if len(validos) >= 20:  # Limitar a 20 combinaciones
                    break
        
        print(f"[+] {len(validos)} horarios válidos generados")
        
        # Crear PDFs para los horarios válidos
        for i, horario in enumerate(validos):
            filename = os.path.join(PDF_FOLDER, f"horario_valido_{i+1}.pdf")
            crear_pdf(horario, filename)
    
    except Exception as e:
        print(f"[-] Error crítico: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()