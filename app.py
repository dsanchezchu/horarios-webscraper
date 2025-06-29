import streamlit as st
from main import abrir_login_y_guardar_captcha, login_and_navigate, run_horario_scraper
from styles import load_custom_css, render_metric_card, render_comentario_card, render_profesor_title
import os
from pdf2image import convert_from_path
import pandas as pd
import json

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

# Funciones para las opiniones de profesores
def load_profesor_classifications():
    """Carga las clasificaciones de profesores desde el archivo JSON"""
    try:
        with open('clasificacion_profesores.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo de clasificaciones de profesores")
        return []

def load_profesor_comments():
    """Carga los comentarios de profesores desde el archivo JSON"""
    try:
        with open('comentarios/comentarios.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo de comentarios de profesores")
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
    """Muestra las opiniones de los profesores que aparecen en los horarios válidos"""
    st.subheader("📝 Opiniones acerca de tus profesores")
    
    # Cargar clasificaciones y profesores de horarios
    clasificaciones = load_profesor_classifications()
    profesores_horarios = get_profesores_from_horarios()
    
    if len(clasificaciones) == 0 or len(profesores_horarios) == 0:
        st.warning("No hay datos disponibles para mostrar")
        return
    
    # Función para normalizar nombres (convertir a conjunto de palabras en mayúsculas)
    def normalizar_nombre(nombre):
        return set(palabra.upper().strip() for palabra in nombre.split() if palabra.strip())
    
    # Crear diccionario de clasificaciones con nombres normalizados
    dict_clasificaciones = {}
    for prof in clasificaciones:
        nombre_normalizado = normalizar_nombre(prof['Docente'])
        dict_clasificaciones[frozenset(nombre_normalizado)] = {
            'nombre_original': prof['Docente'],
            'clasificacion': prof['clasificacion']
        }
    
    # Filtrar solo los profesores que están en los horarios válidos
    profesores_filtrados = []
    for profesor in profesores_horarios:
        profesor_normalizado = normalizar_nombre(profesor)
        
        # Buscar coincidencia en clasificaciones
        for key, value in dict_clasificaciones.items():
            # Si hay coincidencia exacta de todas las palabras
            if profesor_normalizado == key:
                profesores_filtrados.append({
                    'Docente': profesor,  # Usar el nombre del CSV
                    'Clasificación': value['clasificacion']
                })
                break
    
    if len(profesores_filtrados) == 0:
        st.warning("No se encontraron clasificaciones para los profesores de tus horarios")
        return
    
    # Crear DataFrame y mostrar tabla
    df_profesores = pd.DataFrame(profesores_filtrados)
    
    # Agregar emojis según la clasificación
    emoji_map = {
        'bueno': '✅',
        'malo': '❌',
        'neutro': '⚪'
    }
    
    df_profesores['Estado'] = df_profesores['Clasificación'].map(emoji_map)
    
    # Reordenar columnas
    df_profesores = df_profesores[['Estado', 'Docente', 'Clasificación']]
    
    # Mostrar estadísticas
    total_profesores = len(df_profesores)
    buenos = len(df_profesores[df_profesores['Clasificación'] == 'bueno'])
    malos = len(df_profesores[df_profesores['Clasificación'] == 'malo'])
    neutros = len(df_profesores[df_profesores['Clasificación'] == 'neutro'])
    
    # Mostrar estadísticas con estilos personalizados
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(render_metric_card(total_profesores, "Total Profesores", "total"), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(buenos, "Buenos ✅", "buenos"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_metric_card(malos, "Malos ❌", "malos"), unsafe_allow_html=True)
    
    with col4:
        st.markdown(render_metric_card(neutros, "Neutros ⚪", "neutros"), unsafe_allow_html=True)
    
    # Mostrar tabla con botones para cada profesor
    st.markdown("**Haz clic en un profesor para ver sus comentarios:**")
    
    for index, row in df_profesores.iterrows():
        col1, col2, col3 = st.columns([1, 6, 2])
        
        with col1:
            st.write(row['Estado'])
        
        with col2:
            if st.button(row['Docente'], key=f"prof_{index}", use_container_width=True):
                st.session_state.profesor_seleccionado = row['Docente']
                st.rerun()
        
        with col3:
            st.write(row['Clasificación'])
    
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
        st.session_state.mostrar_opiniones = True
        st.session_state.profesor_seleccionado = None  # Resetear selección
        st.rerun()
    
    # Mostrar opiniones si están activadas
    if st.session_state.mostrar_opiniones:
        show_profesor_opinions()
    
    # Separador visual
    st.markdown("---")
    
    # Botón de cerrar sesión centrado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("Cerrar sesión", use_container_width=True, type="primary"):
            # Limpiar todas las variables de sesión
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Sesión cerrada exitosamente")
            st.rerun()