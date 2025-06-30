#paso 1: ejecutar este archivo cuando se extraigan los comentarios
import json
import pandas as pd

# Leer el archivo JSON
with open("comentarios/comentarios.json", encoding="utf-8") as f:
    data = json.load(f)

# Preparar datos para el DataFrame
registros = []
for docente, info in data.items():
    comentarios = info.get("comentarios", [])
    for comentario in comentarios:
        registros.append({
            "Docente": docente,
            "comentarios": comentario.strip()
        })

# Crear DataFrame
df = pd.DataFrame(registros)

# Guardar a CSV
df.to_csv("comentarios/datacoment.csv", index=False, sep=';')

print("Archivo 'datacoment.csv' generado correctamente.")