from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
from itertools import product
import pandas as pd
import re
import random
import os
import time
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración inicial
CURSO_ID = input("Ingrese ID del curso (ej: ISIA-109): ").strip().upper()
PDF_FOLDER = "horarios_generados"
os.makedirs(PDF_FOLDER, exist_ok=True)

def setup_brave():
    try:
        print("[+] Configurando navegador Brave...")
        options = webdriver.ChromeOptions()
        options.binary_location = "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")  # Desactivar aceleración de hardware
        options.add_argument("--disable-software-rasterizer")  # Desactivar rasterizador de software
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        return webdriver.Chrome(options=options)
    except Exception as e:
        print(f"[-] Error al configurar Brave: {str(e)}")
        raise

def random_delay(context):
    delays = {
        'navegacion': random.uniform(5, 10),
        'carga': random.uniform(3, 6),
        'combinaciones': random.uniform(2, 5),
        'extraccion': random.uniform(1, 3)
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

def generate_combinations(secciones):
    """
    Genera combinaciones solo con secciones del mismo grupo (T1+P1+L1, T2+P2+L2, etc)
    """
    grupos_compatibles = {}

    # Agrupar por curso y número de grupo
    for sec in secciones:
        curso = sec['curso']
        id_liga = sec['id_liga']
        grupo_num = id_liga[1:]  # Extrae el número del grupo (ej. T1 → '1')
        
        # Clasificar por tipo
        tipo = None
        if 'T' in id_liga:
            tipo = 'teoria'
        elif 'P' in id_liga:
            tipo = 'practica'
        elif 'L' in id_liga:
            tipo = 'laboratorio'

        if tipo:
            # Estructura: {curso: {grupo_num: {tipo: [secciones]}}}
            grupos_compatibles.setdefault(curso, {}).setdefault(grupo_num, {}).setdefault(tipo, []).append(sec)

    combinaciones = []
    
    for curso, grupos in grupos_compatibles.items():
        for grupo_num, componentes in grupos.items():
            teoria = componentes.get('teoria', [])
            practica = componentes.get('practica', [])
            laboratorio = componentes.get('laboratorio', [])
            
            # Validar que exista al menos teoría
            if not teoria:
                continue
                
            # Generar combinaciones dentro del mismo grupo
            if practica and laboratorio:
                # Combinar T + P + L del mismo grupo
                for t, p, l in product(teoria, practica, laboratorio):
                    combinaciones.append([t, p, l])
            elif practica:
                # Combinar T + P del mismo grupo
                for t, p in product(teoria, practica):
                    combinaciones.append([t, p])
            elif laboratorio:
                # Combinar T + L del mismo grupo (si aplica)
                for t, l in product(teoria, laboratorio):
                    combinaciones.append([t, l])
            else:
                # Solo teoría (si no hay otros componentes)
                combinaciones.extend(teoria)

    return combinaciones

def extract_course_data(driver):
    data = []
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        try:
            print("[+] Esperando carga de los cursos...")
            WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.ID, "id_detalle_cursos"))
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

            return data
        
        except Exception as e:
            attempt += 1
            print(f"[-] Intento {attempt}/{max_attempts} fallido: {str(e)}")
            time.sleep(random.uniform(2, 4))

    print("[-] Error crítico: No se pudo extraer la información")
    return []

def login_and_navigate(driver):
    try:
        print("[+] Iniciando sesión y navegando...")
        driver.get(os.getenv("BASE_URL"))
        
        form_container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table[.//input[@placeholder='usuario']]"))
        )
        
        username = form_container.find_element(By.XPATH, ".//input[@placeholder='usuario']")
        password = form_container.find_element(By.XPATH, ".//input[@placeholder='contraseña']")
        username.send_keys(os.getenv("UPAO_USER"))
        time.sleep(random.uniform(0.5, 1.5))
        password.send_keys(os.getenv("UPAO_PASS"))
        time.sleep(random.uniform(0.5, 1.5))
        
        try:
            captcha = form_container.find_element(By.ID, "imgCaptcha")
            captcha.screenshot("captcha.png")
            code = input("Ingrese el código CAPTCHA: ")
            if code:
                form_container.find_element(By.ID, "txt_img").send_keys(code)
        except:
            pass
        
        form_container.find_element(By.ID, "btn_valida").click()
        time.sleep(random.uniform(4, 6))
        
        driver.get(os.getenv("BASE_HORARIOS"))
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
            # Validar formato del código (ej. "ISIA-112")
            curso_id = CURSO_ID.strip().upper()
            if not re.match(r'^[A-Z]{4}-\d{3}$', curso_id):
                raise ValueError("Formato inválido. Ejemplo: 'ISIA-112', colocaste: " + CURSO_ID)

            # XPath optimizado con doble validación
            xpath = f"//td[" \
                    f"contains(@onclick, 'f_detalle_cursos') and " \
                    f"span[@class='letra' and normalize-space()='{curso_id}']" \
                    f"]"
            
            try:
                # Espera inteligente hasta 20 segundos
                curso_row = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            except:
                print(f"[-] Curso {curso_id} no encontrado")
                return False

            # Verificar atributos críticos
            onclick = curso_row.get_attribute('onclick')
            if not onclick.startswith('javascript:f_detalle_cursos'):
                raise ValueError("Elemento no es un curso válido")

            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});
            """, curso_row)
            
            time.sleep(random.uniform(0.8, 1.2))  # Espera para animaciones
            
            # Ejecutar clic mediante JavaScript
            driver.execute_script("arguments[0].click();", curso_row)
            print(f"[+] Clickeando en {curso_id}...")

            # Esperar carga de detalle
            # WebDriverWait(driver, 15).until(
            #     EC.visibility_of_element_located(
            #         (By.XPATH, "//div[@id='id_detalle_cursos'][contains(@style, 'display: block')]")
            #     )
            # )

            try:
                # Esperar carga de detalle
                WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//div[@id='id_detalle_cursos']//table[@width='90%;' and @border='0' and @cellpadding='5' and @cellspacing='2' and contains(@class, 'tabla_3')]")
                    )
                )
                print("[+] Detalle cargado exitosamente")
                
                # Extraer datos
                return extract_course_data(driver)
                
            except Exception as e:
                print(f"[-] Error en carga de detalle: {str(e)}")
                driver.save_screenshot("error_screenshot.png")  # Captura de pantalla para depuración
                return False

        except Exception as e:
            print(f"[-] Error: {str(e)}")
            driver.quit()
            raise
        
    except Exception as e:
        print(f"[-] Error: {str(e)}")
        driver.quit()
        raise

def crear_pdf(horario, filename):
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        c.drawString(100, height - 40, f"Horario del curso {CURSO_ID}")
        
        data = [["Curso", "ID Liga", "Día", "Hora Inicio", "Hora Fin", "Docente", "NRC"]]
        for h in horario:
            data.append([h['curso'], h['id_liga'], h['dia'], h['hora_inicio'].strftime("%H:%M"), h['hora_fin'].strftime("%H:%M"), h['docente'], h['nrc']])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        table.wrapOn(c, width, height)
        table.drawOn(c, 30, height - 200)
        c.save()
        print(f"[+] PDF generado: {filename}")
    except Exception as e:
        print(f"[-] Error al crear PDF: {str(e)}")
        raise

def main():
    driver = setup_brave()
    
    try:
        login = login_and_navigate(driver)
        # secciones = extract_course_data(login)
        combinaciones = generate_combinations(login)
        print(f"[+] {len(combinaciones)} combinaciones encontradas")
        
        validas = 0
        for i, comb in enumerate(combinaciones, 1):
            horario = []
            for sec in comb:
                for h in sec['horarios']:
                    horario.append({
                        'curso': sec['curso'],
                        'id_liga': sec['id_liga'],
                        'dia': h['dia'],
                        'hora_inicio': h['hora_inicio'],
                        'hora_fin': h['hora_fin'],
                        'docente': h['docente'],
                        'nrc': h['nrc']
                    })
            
            df = pd.DataFrame(horario)
            df = df.sort_values(['dia', 'hora_inicio'])
            valido = True
            
            for dia, grupo in df.groupby('dia'):
                for j in range(1, len(grupo)):
                    if grupo.iloc[j]['hora_inicio'] < grupo.iloc[j-1]['hora_fin']:
                        valido = False
                        break
                if not valido:
                    break
            
            if valido:
                validas += 1
                filename = os.path.join(PDF_FOLDER, f"horario_{CURSO_ID}_{validas}.pdf")
                crear_pdf(horario, filename)
        
        print(f"[+] {validas} horarios válidos generados en '{PDF_FOLDER}'")
        
    except Exception as e:
        print(f"[-] Error crítico: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()