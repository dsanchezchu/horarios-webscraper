# Horarios Web Scraper

Este proyecto tiene como objetivo desarrollar un web scraper para extraer información de horarios de clase de sitios web. La herramienta permitirá a los estudiantes acceder a sus horarios de forma rápida y sencilla, sin necesidad de navegar por páginas web complejas o PDFs confusos.


## Entorno de Trabajo

Sigue estos pasos para crear y ejecutar tu entorno de trabajo en Python:

1. **Crear un entorno virtual**:
    Navega al directorio del proyecto y crea un entorno virtual ejecutando el siguiente comando:
    ```bash
    python -m venv venv
    ```

2. **Activar el entorno virtual**:
    - En Windows:
      ```bash
      .\venv\Scripts\activate
      ```
    - En macOS y Linux:
      ```bash
      source venv/bin/activate
      ```


## Requisitos

Asegúrate de tener instalado Python 3.7 o superior.

## Configuración

Crea un archivo `.env` en el directorio raíz del proyecto y define tus variables de entorno. Por ejemplo:

```
UPAO_USER=000000
UPAO_PASS=password
BASE_URL=https://XXXXXXXXXX.pe/
BASE_HORARIOS=https://XXXXXXX
```

## Instalación de dependencias

Instala las dependencias necesarias ejecutando el siguiente comando:

```bash
pip install -r requirements.txt
```

## Ejecución

Para iniciar el web scraper, ejecuta el siguiente comando:

```bash
python main.py
```

Esto iniciará el proceso de scraping utilizando la URL definida en tu archivo `.env`.

## Licencia

Este proyecto está bajo la Licencia MIT.