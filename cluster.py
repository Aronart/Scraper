#!/usr/bin/env python3
import re
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import csv


CSV_INPUT_PATH = Path(__file__).resolve().parent / "db_output_all.csv"
CSV_OUTPUT_PATH = Path(__file__).resolve().parent / "clustered_representatives.csv"
N_CLUSTERS = 5


def is_low_effort(text: str) -> bool:
    """Filter out very short or empty/deleted texts."""
    wc = len(re.findall(r"\w+", text))
    return wc < 10 or text.strip().lower() in {"", "deleted", "[deleted]"}

def load_and_filter_texts(csv_path):
    df = pd.read_csv(csv_path, dtype=str)
    text = df.iloc[:, 2].fillna("").tolist()
    source = df.iloc[:, 0].fillna("").tolist()

    filtered = [
        {"text": t, "source": src}
        for src, t in zip(source, text)
        if not is_low_effort(t)
    ]
    return filtered


def cluster_texts(filtered_data, n_clusters):
    texts = [entry["text"] for entry in filtered_data]
    sources = [entry["source"] for entry in filtered_data]

    german_stop_words = [
        "aber", "alle", "allem", "allen", "aller", "alles", "als", "also", "am", "an", "ander", "andere", "anderem", "anderen",
        "anderer", "anderes", "anderm", "andern", "anderr", "anders", "auch", "auf", "aus", "bei", "bin", "bis", "bist", "da",
        "damit", "dann", "der", "den", "des", "dem", "die", "das", "dass", "du", "dein", "deine", "deinem", "deinen", "deiner",
        "deines", "doch", "dort", "durch", "ein", "eine", "einem", "einen", "einer", "eines", "er", "es", "etwas", "für", "hat",
        "haben", "ich", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres", "im", "in", "ist", "ja", "jede", "jedem", "jeden",
        "jeder", "jedes", "kein", "keine", "keinem", "keinen", "keiner", "keines", "man", "mit", "muss", "nicht", "noch", "nun",
        "oder", "seid", "sein", "seine", "seinem", "seinen", "seiner", "seines", "selbst", "sich", "sie", "sind", "so", "solche",
        "solchem", "solchen", "solcher", "solches", "und", "uns", "unser", "unserem", "unseren", "unserer", "unseres", "unter",
        "viel", "vom", "von", "vor", "war", "waren", "warst", "was", "weg", "weil", "weiter", "welche", "welchem", "welchen",
        "welcher", "welches", "wenn", "wer", "werde", "werden", "wie", "wieder", "will", "wir", "wird", "wirst", "wo", "wollen",
        "wollte", "würde", "würden", "zu", "zum", "zur", "über"
    ]

    vec = TfidfVectorizer(stop_words=german_stop_words, max_df=0.85)
    # X is a sparse matrix of shape (n_samples, n_features) where:
    # - Each row corresponds to a post or comment (as a TF-IDF vector)
    # - Each column corresponds to a unique word (feature) in the vocabulary
    # This matrix represents how important each word is in each text sample.
    X = vec.fit_transform(texts)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    # labels is a 1D array of shape (n_samples,) containing the cluster index (0 to n_clusters-1)
    # for each corresponding row in X — i.e., each post or comment.
    # It tells us which cluster each text was assigned to by KMeans.
    labels = km.fit_predict(X)

    n=5
    token_limit=2000

    reps = []

    for cid in range(km.n_clusters):
        idxs = np.where(labels == cid)[0]
        if len(idxs) == 0:
            continue

        cluster_vecs = X[idxs]
        centroid = km.cluster_centers_[cid].reshape(1, -1)
        sims = cosine_similarity(cluster_vecs, centroid).flatten()

        # most similar first
        sorted_idxs = idxs[np.argsort(sims)[::-1]]
        cluster_samples = []

        total_tokens = 0
        for idx in sorted_idxs:
            text = texts[idx]
            approx_tokens = len(text) // 4
            if total_tokens + approx_tokens > token_limit:
                break

            cluster_samples.append({
                "text": text,
                "source": sources[idx]
            })
            total_tokens += approx_tokens

            if len(cluster_samples) >= n:
                break

        reps.append({
            "cluster": cid,
            "samples": cluster_samples
        })

    return reps


if __name__ == '__main__':
    data = load_and_filter_texts(CSV_INPUT_PATH)
    reps = cluster_texts(data, N_CLUSTERS)
    with open(CSV_OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cluster", "source", "text"])
        for rep in reps:
            cluster_id = rep["cluster"]
            for sample in rep["samples"]:
                writer.writerow([cluster_id, sample["source"], sample["text"]])
    print(f"✅ Clustered texts written to {CSV_OUTPUT_PATH}")
