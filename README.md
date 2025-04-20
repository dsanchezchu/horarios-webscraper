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

## Instalación de Tesseract OCR

Para que el script de reconocimiento de CAPTCHA funcione, necesitas tener instalado Tesseract OCR y disponible en tu PATH.

### Windows

1. Descarga e instala Tesseract desde  
   https://github.com/tesseract-ocr/tesseract/releases  
2. Añade la carpeta de instalación al PATH del sistema:
   - Abre **Propiedades del sistema** → **Variables de entorno**.
   - En **Variables del sistema**, edita **Path** y añade:
     ```
     C:\Program Files\Tesseract-OCR
     ```
3. Verifica en un nuevo CMD:
   ```bash
   tesseract --version
# macOS con Homebrew
brew install tesseract

# Ubuntu / Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

Configuración en Python
En tu script, si por algún motivo tesseract no queda en el PATH del entorno virtual, define la ruta explícita:


import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


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