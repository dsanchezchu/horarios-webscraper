import streamlit as st
from main import abrir_login_y_guardar_captcha, login_and_navigate, run_horario_scraper
from styles import load_custom_css, render_metric_card, render_comentario_card, render_profesor_title
import os
from pdf2image import convert_from_path
import pandas as pd
import json
import subprocess
import sys

# Cargar estilos CSS al inicio
load_custom_css()

st.title("Generador de Horarios UPAO")

# Inicializar estados de sesión al principio
if "driver" not in st.session_state:
    st.session_state.driver = None
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "login"
if "mostrar_opiniones" not in st.session_state:
    st.session_state.mostrar_opiniones = False
if "profesor_seleccionado" not in st.session_state:
    st.session_state.profesor_seleccionado = None
if "comentarios_procesados" not in st.session_state:
    st.session_state.comentarios_procesados = False
if "clasificaciones_procesadas" not in st.session_state:
    st.session_state.clasificaciones_procesadas = False
if "mostrar_clasificaciones" not in st.session_state:
    st.session_state.mostrar_clasificaciones = False

# Funciones para las opiniones de profesores
def ejecutar_scraping_comentarios():
    """Ejecuta el script main_comentarios.py para obtener comentarios de profesores"""
    try:
        print("Ejecutando main_comentarios.py...")  # Debug
        # Ejecutar el script main_comentarios.py
        result = subprocess.run([sys.executable, "main_comentarios.py"], 
                              capture_output=True, text=True, cwd=".")
        
        print(f"Return code: {result.returncode}")  # Debug
        print(f"Stdout: {result.stdout}")  # Debug
        print(f"Stderr: {result.stderr}")  # Debug
        
        if result.returncode == 0:
            return True, "Scraping de comentarios completado exitosamente"
        else:
            return False, f"Error en el scraping: {result.stderr}"
    except Exception as e:
        print(f"Exception: {str(e)}")  # Debug
        return False, f"Error al ejecutar el scraping: {str(e)}"

def ejecutar_clasificacion_profesores():
    """Ejecuta los scripts para clasificar profesores usando análisis de sentimientos"""
    try:
        # Paso 1: Ejecutar comentarios_a_csv_.py
        print("Ejecutando comentarios_a_csv_.py...")
        result1 = subprocess.run([sys.executable, "comentarios/comentarios_a_csv_.py"], 
                               capture_output=True, text=True, cwd=".")
        
        if result1.returncode != 0:
            return False, f"Error en comentarios_a_csv_.py: {result1.stderr}"
        
        # Paso 2: Ejecutar aplicacion-analisis-sent.py
        print("Ejecutando aplicacion-analisis-sent.py...")
        result2 = subprocess.run([sys.executable, "aplicacion-analisis-sent.py"], 
                               capture_output=True, text=True, cwd=".")
        
        if result2.returncode != 0:
            return False, f"Error en aplicacion-analisis-sent.py: {result2.stderr}"
        
        return True, "Clasificación de profesores completada exitosamente"
    except Exception as e:
        return False, f"Error al ejecutar la clasificación: {str(e)}"

def load_profesor_classifications():
    """Carga las clasificaciones de profesores desde el archivo JSON"""
    try:
        with open('clasificacion_profesores.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def show_profesor_classifications():
    """Muestra las clasificaciones de los profesores"""
    st.subheader("🎯 Clasificación de Profesores")
    
    clasificaciones = load_profesor_classifications()
    
    if not clasificaciones:
        st.warning("No hay clasificaciones disponibles. Ejecuta la clasificación primero.")
        return
    
    # Convertir a DataFrame para mejor manejo
    df_clasificaciones = pd.DataFrame(clasificaciones)
    
    # Contar clasificaciones
    buenos = len(df_clasificaciones[df_clasificaciones['clasificacion'] == 'bueno'])
    malos = len(df_clasificaciones[df_clasificaciones['clasificacion'] == 'malo'])
    neutros = len(df_clasificaciones[df_clasificaciones['clasificacion'] == 'neutro'])
    
    # Mostrar estadísticas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(render_metric_card(buenos, "Profesores Buenos", "buenos"), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(malos, "Profesores Malos", "malos"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_metric_card(neutros, "Profesores Neutros", "neutros"), unsafe_allow_html=True)
    
    # Mostrar lista de profesores organizados por clasificación
    st.markdown("### 📊 Clasificación detallada:")
    
    # Profesores buenos
    profesores_buenos = df_clasificaciones[df_clasificaciones['clasificacion'] == 'bueno']
    if not profesores_buenos.empty:
        st.markdown("#### ✅ **Profesores Buenos:**")
        for _, profesor in profesores_buenos.iterrows():
            st.success(f"👨‍🏫 {profesor['Docente']}")
    
    # Profesores neutros
    profesores_neutros = df_clasificaciones[df_clasificaciones['clasificacion'] == 'neutro']
    if not profesores_neutros.empty:
        st.markdown("#### ⚖️ **Profesores Neutros:**")
        for _, profesor in profesores_neutros.iterrows():
            st.info(f"👨‍🏫 {profesor['Docente']}")
    
    # Profesores malos
    profesores_malos = df_clasificaciones[df_clasificaciones['clasificacion'] == 'malo']
    if not profesores_malos.empty:
        st.markdown("#### ❌ **Profesores Malos:**")
        for _, profesor in profesores_malos.iterrows():
            st.error(f"👨‍🏫 {profesor['Docente']}")

def load_profesor_comments():
    """Carga los comentarios de profesores desde el archivo JSON"""
    try:
        with open('comentarios/comentarios.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_profesores_from_horarios():
    """Obtiene la lista de profesores únicos de los horarios válidos"""
    try:
        df_horarios = pd.read_csv('csv_horarios/horarios_validos.csv')
        # Obtener profesores únicos de la columna 'Docente'
        profesores_unicos = df_horarios['Docente'].unique()
        return profesores_unicos
    except FileNotFoundError:
        st.error("No se encontró el archivo de horarios válidos")
        return []

def show_profesor_comments(profesor_nombre):
    """Muestra los comentarios de un profesor específico"""
    comentarios_data = load_profesor_comments()
    
    # Función para normalizar nombres para búsqueda
    def normalizar_nombre_comentarios(nombre):
        return set(palabra.upper().strip() for palabra in nombre.split() if palabra.strip())
    
    # Buscar comentarios del profesor
    profesor_normalizado = normalizar_nombre_comentarios(profesor_nombre)
    comentarios_encontrados = None
    nombre_encontrado = None
    
    for prof_comentarios, data in comentarios_data.items():
        prof_normalizado = normalizar_nombre_comentarios(prof_comentarios)
        if profesor_normalizado == prof_normalizado:
            comentarios_encontrados = data
            nombre_encontrado = prof_comentarios
            break
    
    if comentarios_encontrados:
        st.markdown(render_profesor_title(nombre_encontrado), unsafe_allow_html=True)
        st.write(f"**Total de comentarios:** {comentarios_encontrados['total_comentarios']}")
        
        if 'comentarios' in comentarios_encontrados and comentarios_encontrados['comentarios']:
            for i, comentario in enumerate(comentarios_encontrados['comentarios'], 1):
                st.markdown(render_comentario_card(i, comentario), unsafe_allow_html=True)
        else:
            st.info("Este profesor tiene comentarios registrados pero no están disponibles para mostrar.")
    else:
        st.warning(f"No se encontraron comentarios para {profesor_nombre}")

def show_profesor_opinions():
    """Muestra las opiniones de los profesores basado en comentarios.json"""
    st.subheader("📝 Opiniones acerca de tus profesores")
    
    # Cargar comentarios y profesores de horarios
    comentarios_data = load_profesor_comments()
    profesores_horarios = get_profesores_from_horarios()
    
    if len(comentarios_data) == 0 or len(profesores_horarios) == 0:
        st.warning("No hay datos de comentarios disponibles para mostrar")
        return
    
    # Función para normalizar nombres (convertir a conjunto de palabras en mayúsculas)
    def normalizar_nombre(nombre):
        return set(palabra.upper().strip() for palabra in nombre.split() if palabra.strip())
    
    # Filtrar solo los profesores que están en los horarios válidos y tienen comentarios
    profesores_con_comentarios = []
    
    for profesor in profesores_horarios:
        profesor_normalizado = normalizar_nombre(profesor)
        
        # Buscar coincidencia en comentarios
        for prof_comentarios, data in comentarios_data.items():
            prof_normalizado = normalizar_nombre(prof_comentarios)
            
            # Si hay coincidencia exacta de todas las palabras
            if profesor_normalizado == prof_normalizado:
                profesores_con_comentarios.append({
                    'Docente': profesor,  # Usar el nombre del CSV
                    'Total_Comentarios': data['total_comentarios'],
                    'Nombre_Comentarios': prof_comentarios
                })
                break
    
    if len(profesores_con_comentarios) == 0:
        st.warning("No se encontraron comentarios para los profesores de tus horarios")
        return
    
    # Crear DataFrame
    df_profesores = pd.DataFrame(profesores_con_comentarios)
    
    # Mostrar lista de profesores con botones para cada uno (sin estadísticas)
    st.markdown("**Haz clic en un profesor para ver sus comentarios:**")
    
    for index, row in df_profesores.iterrows():
        col1, col2 = st.columns([6, 2])
        
        with col1:
            if st.button(f"👨‍🏫 {row['Docente']}", key=f"prof_{index}", use_container_width=True):
                st.session_state.profesor_seleccionado = row['Docente']
                st.rerun()
        
        with col2:
            st.write(f"📝 {row['Total_Comentarios']} comentarios")
    
    # Mostrar comentarios del profesor seleccionado
    if st.session_state.profesor_seleccionado:
        st.markdown("---")
        show_profesor_comments(st.session_state.profesor_seleccionado)
        
        # Botón para limpiar selección
        if st.button("Volver a la lista", use_container_width=True):
            st.session_state.profesor_seleccionado = None
            st.rerun()

if st.session_state.pantalla == "login":
    with st.form("credenciales_form"):
        user = st.text_input("Usuario UPAO")
        password = st.text_input("Contraseña", type="password")
        curso_ids = st.text_input("IDs de cursos (ej: ISIA-109,ISIA-110)")
        base_url = st.text_input("URL de login", value="https://matricula.upao.edu.pe/login")
        base_horarios = st.text_input("URL de horarios", value="https://matricula.upao.edu.pe/horarios")
        step = st.radio("Paso", ["1. Ingresar credenciales y obtener captcha", "2. Ingresar captcha y continuar scraping"])
        captcha_code = st.text_input("Captcha (solo en paso 2)", value="") if step == "2. Ingresar captcha y continuar scraping" else ""
        submitted = st.form_submit_button("Siguiente")

    if submitted:
        if step == "1. Ingresar credenciales y obtener captcha":
            if not user or not password or not curso_ids:
                st.error("Por favor, completa todos los campos.")
            else:
                with st.spinner("Abriendo navegador y obteniendo captcha..."):
                    driver, captcha_path = abrir_login_y_guardar_captcha(user, password, base_url)
                    st.session_state.driver = driver
                    st.session_state.curso_ids = curso_ids
                    st.session_state.base_url = base_url
                    st.session_state.base_horarios = base_horarios
                st.image(captcha_path, caption="Captcha actual")
                st.success("Captcha obtenido. Ahora ingresa el código y pasa al paso 2.")
        elif step == "2. Ingresar captcha y continuar scraping":
            if not captcha_code or st.session_state.driver is None:
                st.error("Debes obtener el captcha primero (paso 1).")
            else:
                with st.spinner("Procesando scraping..."):
                    try:
                        driver = login_and_navigate(st.session_state.driver, captcha_code, st.session_state.base_horarios)
                        ok, msg = run_horario_scraper(
                            user,
                            password,
                            [c.strip().upper() for c in st.session_state.curso_ids.split(",")],
                            st.session_state.base_url,
                            st.session_state.base_horarios,
                            driver=driver
                        )
                        if ok:
                            st.success(msg)
                            st.session_state.pantalla = "final"
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        if st.session_state.driver:
                            st.session_state.driver.quit()
                        st.session_state.driver = None

elif st.session_state.pantalla == "final":
    pdf_folder = "horarios_generados"
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    st.subheader("Horarios generados:")
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        for img in images:
            st.image(img, caption=pdf_file, use_container_width=True)

    # Separador visual
    st.markdown("---")
    
    # Botón para mostrar opiniones de profesores
    if st.button("👨‍🏫 Opiniones acerca de tus profes", use_container_width=True):
        if not st.session_state.comentarios_procesados:
            with st.spinner("Obteniendo comentarios de profesores..."):
                success, message = ejecutar_scraping_comentarios()
                if success:
                    st.session_state.comentarios_procesados = True
                    st.session_state.mostrar_opiniones = True
                    st.session_state.profesor_seleccionado = None  # Resetear selección
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.session_state.mostrar_opiniones = True
            st.session_state.profesor_seleccionado = None  # Resetear selección
            st.rerun()
    
    # Mostrar opiniones si están activadas
    if st.session_state.mostrar_opiniones:
        show_profesor_opinions()
        
        # Separador visual
        st.markdown("---")
        
        # Botón para clasificar profesores (solo aparece después de mostrar opiniones)
        if st.button("🎯 Clasificar profesores", use_container_width=True):
            if not st.session_state.clasificaciones_procesadas:
                with st.spinner("Clasificando profesores con análisis de sentimientos..."):
                    success, message = ejecutar_clasificacion_profesores()
                    if success:
                        st.session_state.clasificaciones_procesadas = True
                        st.session_state.mostrar_clasificaciones = True
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.session_state.mostrar_clasificaciones = True
                st.rerun()
        
        # Mostrar clasificaciones si están activadas
        if st.session_state.mostrar_clasificaciones:
            show_profesor_classifications()
    
    # Separador visual
    st.markdown("---")
    
    # Botón de cerrar sesión centrado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("Cerrar sesión", use_container_width=True, type="primary"):
            # Limpiar PDFs de la carpeta horarios_generados
            try:
                pdf_folder = "horarios_generados"
                if os.path.exists(pdf_folder):
                    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
                    for pdf_file in pdf_files:
                        pdf_path = os.path.join(pdf_folder, pdf_file)
                        os.remove(pdf_path)
                    if pdf_files:
                        print(f"[INFO] Se eliminaron {len(pdf_files)} archivos PDF")
            except Exception as e:
                print(f"[ERROR] Error al eliminar PDFs: {e}")
            
            # Limpiar archivo de clasificaciones JSON
            try:
                if os.path.exists("clasificacion_profesores.json"):
                    os.remove("clasificacion_profesores.json")
                    print("[INFO] Se eliminó clasificacion_profesores.json")
            except Exception as e:
                print(f"[ERROR] Error al eliminar clasificacion_profesores.json: {e}")

            # Limpiar archivo de clasificaciones CSV
            try:
                if os.path.exists("./comentarios/datacoment.csv"):
                    os.remove("./comentarios/datacoment.csv")
                    print("[INFO] Se eliminó datacoment.csv")
            except Exception as e:
                print(f"[ERROR] Error al eliminar datacoment.csv: {e}")

            try:
                if os.path.exists("./comentarios/comentarios.json"):
                    os.remove("./comentarios/comentarios.json")
                    print("[INFO] Se eliminó comentarios.json")
            except Exception as e:
                print(f"[ERROR] Error al eliminar comentarios.json: {e}")

            # Limpiar archivos JSON de la carpeta data-horarios
            try:
                data_horarios_folder = "data-horarios"
                if os.path.exists(data_horarios_folder):
                    json_files = [f for f in os.listdir(data_horarios_folder) if f.endswith(".json")]
                    for json_file in json_files:
                        json_path = os.path.join(data_horarios_folder, json_file)
                        os.remove(json_path)
                    if json_files:
                        print(f"[INFO] Se eliminaron {len(json_files)} archivos JSON de data-horarios")
            except Exception as e:
                print(f"[ERROR] Error al eliminar JSONs de data-horarios: {e}")

            # Limpiar todas las variables de sesión
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Sesión cerrada exitosamente")
            st.rerun()