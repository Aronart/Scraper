#!/usr/bin/env python3
import pandas as pd
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

CSV_PATH = Path(__file__).resolve().parent / "clustered_representatives.csv"

load_dotenv()
client = OpenAI()


def load_clustered_reps(csv_path):
    df = pd.read_csv(csv_path)
    reps = []
    for cluster_id in sorted(df['cluster'].unique()):
        cluster_df = df[df['cluster'] == cluster_id]
        samples = [
            {"source": row['source'], "text": row['text']}
            for _, row in cluster_df.iterrows()
        ]
        reps.append({
            "cluster": cluster_id,
            "samples": samples
        })
    return reps

def build_openai_prompt(reps):
    blocks = []
    for rep in reps:
        block = f"Cluster {rep['cluster']}:\n"
        for sample in rep["samples"]:
            snippet = sample["text"].strip()
            block += f"- ({sample['source']}): [ANFANG] {snippet} [ENDE]\n"
        blocks.append(block)

    return f"""
Hier sind Cluster von Reddit-Posts und -Kommentaren zu Themen wie Quereinstieg, Weiterbildung, Arbeitslosigkeit und Umschulung. 
Bitte analysiere sie tief und gib eine strukturierte Antwort auf **Deutsch** zurück:

---

**1. Inhaltliche Insights:**
Fasse die wichtigsten Erkenntnisse, wiederkehrenden Probleme, Chancen oder Meinungen aus den Reddit-Beiträgen zusammen. Ziel ist es, ein Gefühl für die Sorgen, Fragen und Bedürfnisse der Zielgruppe zu bekommen.

---

**2. 3-5 Carousel-Post-Ideen für Instagram (@franklin_ias):**
Für jeden Post gib bitte folgende Struktur zurück (alles auf Deutsch, kein Englisch):

- **Titel:** Kurz & klar
- **Format-Typ:** (z. B. Story, Vergleich, Zitat, Anleitung…)
- **Slides:** Eine Liste von 5 Slides mit echtem Text (max. 250 Zeichen pro Slide)
  - Slide 1: Hook
  - Slide 2–4: Inhaltliche Aufbereitung
  - Slide 5: Call-to-Action („Link in Bio“, „Was denkst du?“ etc.)

Schreibe den tatsächlichen Text pro Slide, nicht nur eine Beschreibung. Nutze eine aktivierende, sympathische Sprache. Vermeide Floskeln. Ziehe konkrete Reddit-Aussagen und Erfahrungen heran.

---

**Datenbasis:**
{'\n\n'.join(blocks)}
"""

def call_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        temperature=0.7,
        messages=[
            {"role": "system", "content": (
            "Du bist ein erfahrener deutscher Content-Stratege für Instagram. "
            "Du entwickelst Carousel-Posts für @franklin_ias – ein Bildungsinstitut, das Erwachsenen zwischen 25 und 45 Jahren hilft, sich beruflich neu zu orientieren, weiterzubilden oder eine Umschulung zu machen. "
            "Deine Sprache ist aktivierend, verständlich, sympathisch und auf die Zielgruppe zugeschnitten. "
            "Du nutzt konkrete Sprache, vermeidest Floskeln und beziehst dich auf reale Erfahrungen."
        )},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    reps = load_clustered_reps(CSV_PATH)
    prompt = build_openai_prompt(reps)
    response = call_openai(prompt)
    print(response)