import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import hashlib
import json
import os
import pandas as pd
import re
from datetime import datetime

STORAGE_FILE = "annonces_seloger.json"

def extract_price(text):
    match = re.search(r"(\d[\d\s,.]*)\s*€", text)
    if match:
        try:
            return int(match.group(1).replace(" ", "").replace(",", ""))
        except:
            return None
    return None

def get_annonces_selenium(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    cards = soup.select("div[data-testid='serp-core-classified-card-testid']")
    results = []

    for card in cards:
        try:
            link_tag = card.select_one("a[data-testid='card-mfe-covering-link-testid']")
            link = link_tag["href"] if link_tag else "#"
            title = link_tag["title"].strip() if link_tag and link_tag.has_attr("title") else "Annonce sans titre"
            description_tag = card.select_one("div[data-testid='cardmfe-description-text-test-id']")
            description = description_tag.text.strip() if description_tag else ""
            address_tag = card.select_one("div[data-testid='cardmfe-description-box-address']")
            address = address_tag.text.strip() if address_tag else ""
            price = extract_price(title)
            hash_id = hashlib.md5((title + link).encode()).hexdigest()

            results.append({
                "id": hash_id,
                "title": title,
                "link": link,
                "description": description,
                "address": address,
                "price": price,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Erreur parsing carte: {e}")
            continue

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
        if a["price"] is not None:
            if min_price and a["price"] < min_price:
                continue
            if max_price and a["price"] > max_price:
                continue
        filtered.append(a)
    return filtered

# Interface Streamlit
st.set_page_config(page_title="SeLoger Delta", layout="centered")
st.title("🏡 Suivi des annonces SeLoger")
st.markdown("Entrez l’URL de recherche SeLoger (avec vos filtres) pour détecter les **nouvelles annonces**.")

url = st.text_input("🔗 URL de recherche SeLoger")
keyword = st.text_input("🔍 Mot-clé (optionnel)")
min_price = st.number_input("💰 Prix minimum (€)", min_value=0, step=1000)
max_price = st.number_input("💰 Prix maximum (€)", min_value=0, step=1000)

if url:
    with st.spinner("🔄 Scraping en cours..."):
        current_annonces = get_annonces_selenium(url)
        previous_annonces = load_previous()
        nouvelles = detect_delta(current_annonces, previous_annonces)
        filtered = filter_annonces(nouvelles, keyword, min_price, max_price)

    st.subheader(f"🆕 {len(filtered)} nouvelles annonces détectées")
    if filtered:
        df = pd.DataFrame(filtered)
        for a in filtered:
            st.markdown(f"**[{a['title']}]({a['link']})**  \n📍 {a['address']}  \n💬 {a['description']}  \n💰 {a['price'] if a['price'] else 'Prix inconnu'} €")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Télécharger en CSV", data=csv, file_name="nouvelles_annonces.csv", mime="text/csv")
    else:
        st.info("Aucune nouvelle annonce correspondant à vos critères.")

    save_current(current_annonces)
