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
CURSO_ID = input("Ingrese ID del curso (ej: ISIA-109): ").strip().replace('-', '').lower()
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

def extract_course_data(driver):
    print("[+] Extrayendo datos del curso...")
    secciones = []
    
    try:
        # Localizar contenedor principal
        contenedor = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='id_grids']"))
        )
        
        # Buscar todas las filas de cursos
        rows = contenedor.find_elements(By.XPATH, ".//tr[contains(@style, 'background:#EAF3FD') or contains(@style, 'background:#FFFFFF')]")
        
        for row in rows:
            try:
                # Extraer código de curso
                codigo_span = row.find_element(By.XPATH, ".//td[1]//span[@class='letra']")
                codigo = codigo_span.text.strip().replace('-', '').lower()
                
                if codigo != CURSO_ID:
                    continue
                    
                print(f"[+] Curso {codigo_span.text} encontrado. Extrayendo detalles...")
                
                # Hacer clic en la fila (con scroll y espera)
                driver.execute_script("arguments[0].scrollIntoView(true);", row)
                time.sleep(random.uniform(1.5, 3.5))
                row.click()
                
                # Esperar página de detalles
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@style, 'border-bottom:0px solid #C0C0C0')]"))
                )
                
                # Extraer cabecera
                cabecera = driver.find_element(By.XPATH, "//table[1]").text
                nrc = re.search(r'NRC:\s*(\S+)', cabecera).group(1)
                secc = re.search(r'SECC:\s*(\S+)', cabecera).group(1)
                id_liga = re.search(r'ID LIGA:\s*(\S+)', cabecera).group(1)
                liga = re.search(r'LIGA:\s*(\S+)', cabecera).group(1).split()[0]  # Extraer T/P/L
                
                # Extraer horarios
                horarios = []
                tabla = driver.find_element(By.XPATH, "//table[2]")
                for fila in tabla.find_elements(By.XPATH, ".//tr[contains(@style, 'background:#FFFFFF')]"):
                    celdas = fila.find_elements(By.TAG_NAME, 'td')
                    if len(celdas) >= 6:
                        horarios.append({
                            'dia': celdas[2].text.strip(),
                            'hora_inicio': parse_horario(celdas[3].text.strip())['inicio'],
                            'hora_fin': parse_horario(celdas[3].text.strip())['fin'],
                            'docente': celdas[5].text.strip(),
                            'aula': celdas[1].text.strip()
                        })
                
                secciones.append({
                    'nrc': nrc,
                    'seccion': secc,
                    'id_liga': id_liga,
                    'liga': liga,
                    'horarios': horarios,
                    'curso': codigo_span.text  # Versión original con formato
                })
                
                # Regresar a la lista principal
                driver.back()
                time.sleep(random.uniform(3, 5))
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='id_grids']"))
                )
                
            except Exception as e:
                print(f"[-] Error en fila: {str(e)}")
                continue
    
    except Exception as e:
        print(f"[-] Error crítico: {str(e)}")
    
    return secciones

def generate_combinations(secciones):
    print("[+] Generando combinaciones de horarios...")
    ligas = {}
    for sec in secciones:
        if sec['id_liga'] not in ligas:
            ligas[sec['id_liga']] = {
                'T': [], 
                'P': [], 
                'L': []
            }
        for tipo in sec['liga'].split():
            ligas[sec['id_liga']][tipo[0]].append(sec)

    combinaciones = []
    for liga_id, grupos in ligas.items():
        teoricas = grupos['T']
        practicas = grupos['P']
        labs = grupos['L']
        
        if teoricas and practicas and labs:
            combinaciones.extend(product(teoricas, practicas, labs))
        elif teoricas and practicas:
            combinaciones.extend(product(teoricas, practicas))
        else:
            combinaciones.extend(teoricas + practicas + labs)
        
        time.sleep(random_delay('combinaciones'))
    
    return combinaciones

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

        return extract_course_data(driver)
        
    except Exception as e:
        print(f"[-] Error: {str(e)}")
        driver.quit()
        raise

def crear_pdf(horario, filename):
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        c.drawString(100, height - 40, f"Horario del curso {CURSO_ID}")
        
        data = [["Curso", "Sección", "Día", "Hora Inicio", "Hora Fin", "Docente"]]
        for h in horario:
            data.append([h['curso'], h['seccion'], h['dia'], h['hora_inicio'].strftime("%H:%M"), h['hora_fin'].strftime("%H:%M"), h['docente']])
        
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
        secciones = login_and_navigate(driver)
        
        combinaciones = generate_combinations(secciones)
        print(f"[+] {len(combinaciones)} combinaciones encontradas")
        
        validas = 0
        for i, comb in enumerate(combinaciones, 1):
            horario = []
            for sec in comb:
                for h in sec['horarios']:
                    horario.append({
                        'curso': sec['curso'],
                        'seccion': sec['seccion'],
                        'dia': h['dia'],
                        'hora_inicio': h['hora_inicio'],
                        'hora_fin': h['hora_fin'],
                        'docente': h['docente']
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