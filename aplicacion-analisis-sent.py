# Paso 2: Generación de clasificación de profesores
import torch
import pandas as pd
import json  # Se importa json para guardar también el resultado en ese formato
from transformers import BertTokenizer, BertForSequenceClassification

MODEL_DIR = "./modelo_entrenado"

def clasificar_profesores(model, tokenizer):
    # Leer comentarios desde archivo CSV
    df = pd.read_csv("comentarios/datacoment.csv", sep=';')
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=['comentarios'])

    # Tokenizar comentarios
    textos = df['comentarios'].tolist()
    tokens = tokenizer(textos, padding=True, truncation=True, return_tensors="pt")

    # Realizar predicciones sin gradiente (modo inferencia)
    with torch.no_grad():
        outputs = model(**tokens)
        preds = torch.argmax(outputs.logits, dim=1).numpy()

    # Añadir columna de sentimiento según predicción
    df['sentimiento'] = ['positivo' if p == 1 else 'negativo' for p in preds]

    clasificacion = []

    # Clasificar cada docente según la mayoría de opiniones
    for profesor, grupo in df.groupby('Docente'):
        positivos = (grupo['sentimiento'] == 'positivo').sum()
        negativos = (grupo['sentimiento'] == 'negativo').sum()

        if positivos > negativos:
            clasif = 'bueno'
        elif negativos > positivos:
            clasif = 'malo'
        else:
            clasif = 'neutro'

        clasificacion.append({'Docente': profesor, 'clasificacion': clasif})

    # Guardar resultados en CSV
    resultado_df = pd.DataFrame(clasificacion)
    resultado_df.to_csv("clasificacion_profesores.csv", index=False, sep=';')
    print("✅ Clasificación generada en 'clasificacion_profesores.csv'")

    # Guardar resultados en JSON
    with open("clasificacion_profesores.json", "w", encoding="utf-8") as f:
        json.dump(clasificacion, f, ensure_ascii=False, indent=4)
    print("✅ Clasificación generada en 'clasificacion_profesores.json'")

if __name__ == "__main__":
    tokenizer = BertTokenizer.from_pretrained(MODEL_DIR)
    model = BertForSequenceClassification.from_pretrained(MODEL_DIR)
    clasificar_profesores(model, tokenizer)
