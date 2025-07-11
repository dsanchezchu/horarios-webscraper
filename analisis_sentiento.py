# paso opcional si ya se entrenó: este código no es necesario ejecutar si ya se hizo antes,
# pero si se desea agregar más información a la data para el entrenamiento, se puede volver a entrenar

import torch
from sklearn.metrics import classification_report
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset
import pandas as pd
import re
import unicodedata

MODEL_NAME = "dccuchile/bert-base-spanish-wwm-uncased"
OUTPUT_DIR = "./modelo_entrenado"

def limpiar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8', 'ignore')
    texto = texto.lower()
    texto = re.sub(r'http\S+|www\S+|https\S+', '', texto)
    texto = re.sub(r'@\w+|#\w+', '', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = re.sub(r'\d+', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def cargar_datos_entrenamiento():
    df = pd.read_csv('comentarios_entrenamiento.csv', sep=';')
    df.columns = df.columns.str.strip().str.lower()
    df['sentimiento'] = df['sentimiento'].str.lower().str.strip()
    df = df[df['sentimiento'].isin(['positivo', 'negativo'])]
    df['label'] = df['sentimiento'].map({'positivo': 1, 'negativo': 0})
    df['comentario'] = df['comentario'].apply(limpiar_texto)
    return Dataset.from_pandas(df[['comentario', 'label']])

def tokenize(batch):
    return tokenizer(batch["comentario"], padding=True, truncation=True)

if __name__ == "__main__":
    tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
    dataset = cargar_datos_entrenamiento()
    dataset = dataset.train_test_split(test_size=0.2)
    dataset = dataset.map(tokenize, batched=True)

    model = BertForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)

    training_args = TrainingArguments(
        output_dir="./results",
        eval_strategy="epoch",
        logging_strategy="epoch",
        save_strategy="epoch",
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        logging_dir="./logs",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset['train'],
        eval_dataset=dataset['test'],
        tokenizer=tokenizer,
    )

    trainer.train()

    print("📊 Evaluando modelo...")
    preds = trainer.predict(dataset['test'])
    y_pred = preds.predictions.argmax(axis=1)
    y_true = preds.label_ids
    print(classification_report(y_true, y_pred, target_names=["negativo", "positivo"]))

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"✅ Modelo y tokenizer guardados en {OUTPUT_DIR}")
