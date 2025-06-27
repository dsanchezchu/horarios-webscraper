import streamlit as st
from main import abrir_login_y_guardar_captcha, login_and_navigate, run_horario_scraper

st.title("Generador de Horarios UPAO")

if "driver" not in st.session_state:
    st.session_state.driver = None

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
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    if st.session_state.driver:
                        st.session_state.driver.quit()
                    st.session_state.driver = None