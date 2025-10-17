import streamlit as st
import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
import pandas as pd

STORAGE_FILE = "annonces_seloger.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_annonces(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    annonces = soup.select(".c-pa-list__item")  # À adapter si structure change
    results = []
    for a in annonces:
        title = a.text.strip()
        link_tag = a.find("a")
        link = link_tag["href"] if link_tag else "#"
        hash_id = hashlib.md5(title.encode()).hexdigest()
        results.append({"id": hash_id, "title": title, "link": link})
    return results

def load_previous():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return []

def save_current(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

def detect_delta(current, previous):
    previous_ids = {a["id"] for a in previous}
    return [a for a in current if a["id"] not in previous_ids]

def filter_annonces(annonces, keyword, min_price, max_price):
    filtered = []
    for a in annonces:
        if keyword and keyword.lower() not in a["title"].lower():
            continue
        if "€" in a["title"]:
            try:
                price = int(a["title"].split("€")[0].replace(" ", "").replace(",", ""))
                if min_price and price < min_price:
                    continue
                if max_price and price > max_price:
                    continue
            except:
                pass
        filtered.append(a)
    return filtered

st.set_page_config(page_title="SeLoger Delta", layout="centered")
st.title("🏡 Suivi des annonces SeLoger")
st.markdown("Entrez l’URL de recherche SeLoger (avec vos filtres) pour détecter les **nouvelles annonces**.")

url = st.text_input("🔗 URL de recherche SeLoger")
keyword = st.text_input("🔍 Mot-clé (optionnel)")
min_price = st.number_input("💰 Prix minimum (€)", min_value=0, step=1000)
max_price = st.number_input("💰 Prix maximum (€)", min_value=0, step=1000)

if url:
    with st.spinner("🔄 Scraping en cours..."):
        current_annonces = get_annonces(url)
        previous_annonces = load_previous()
        nouvelles = detect_delta(current_annonces, previous_annonces)
        filtered = filter_annonces(nouvelles, keyword, min_price, max_price)

    st.subheader(f"🆕 {len(filtered)} nouvelles annonces détectées")
    if filtered:
        df = pd.DataFrame(filtered)
        for a in filtered:
            st.markdown(f"- [{a['title']}]({a['link']})")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Télécharger en CSV", data=csv, file_name="nouvelles_annonces.csv", mime="text/csv")
    else:
        st.info("Aucune nouvelle annonce correspondant à vos critères.")

    save_current(current_annonces)
