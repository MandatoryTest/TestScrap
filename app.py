import streamlit as st
import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
import pandas as pd
import re
from datetime import datetime

STORAGE_FILE = "annonces_seloger.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 🔍 Extraction du prix
def extract_price(text):
    match = re.search(r"(\d[\d\s,.]*)\s*€", text)
    if match:
        try:
            return int(match.group(1).replace(" ", "").replace(",", ""))
        except:
            return None
    return None

# 🧩 Parsing d'une annonce
def parse_annonce(card):
    try:
        link_tag = card.select_one("a[data-testid='card-mfe-covering-link-testid']")
        title = link_tag["title"].strip() if link_tag and link_tag.has_attr("title") else "Sans titre"
        link = link_tag["href"] if link_tag else "#"

        address_tag = card.select_one("div[data-testid='cardmfe-description-box-address']")
        address = address_tag.text.strip() if address_tag else ""

        description_tag = card.select_one("div[data-testid='cardmfe-description-text-test-id']")
        description = description_tag.text.strip() if description_tag else ""

        price_tag = card.select_one("div[data-testid='cardmfe-price-testid']")
        price_text = price_tag.text.strip() if price_tag else title
        price = extract_price(price_text)

        keyfacts = card.select("div[data-testid='cardmfe-keyfacts-testid'] .css-9u48bm")
        keyfacts_text = " · ".join([k.text.strip() for k in keyfacts]) if keyfacts else ""

        image_tags = card.select("img.css-hclm2j")
        images = [img["src"] for img in image_tags if img.has_attr("src")]

        agency_tag = card.select_one("div[data-testid*='agency-publisher']")
        agency = agency_tag.text.strip() if agency_tag else ""

        hash_id = hashlib.md5((title + link).encode()).hexdigest()

        return {
            "id": hash_id,
            "title": title,
            "link": link,
            "address": address,
            "description": description,
            "price": price,
            "keyfacts": keyfacts_text,
            "images": images,
            "agency": agency,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Erreur parsing annonce: {e}")
        return None

# 🔄 Scraping de la page
def get_annonces(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("div[data-testid='serp-core-classified-card-testid']")
    results = [parse_annonce(card) for card in cards]
    return [r for r in results if r is not None]

# 📦 Sauvegarde et chargement
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

# 🖥️ Interface Streamlit
st.set_page_config(page_title="SeLoger Delta", layout="centered")
st.title("🏡 Suivi des annonces SeLoger")
st.markdown("Scraping des annonces visibles sur SeLoger. Fonctionne uniquement avec les pages HTML statiques.")

url = st.text_input("🔗 URL de recherche SeLoger", value="https://www.seloger.com/immobilier/achat/immo-lyon-3eme-69/bien-appartement/")
keyword = st.text_input("🔍 Mot-clé (optionnel)")
min_price = st.number_input("💰 Prix minimum (€)", min_value=0, step=1000)
max_price = st.number_input("💰 Prix maximum (€)", min_value=0, step=1000)

if url:
    with st.spinner("🔄 Scraping en cours..."):
        current_annonces = get_annonces(url)
        filtered = filter_annonces(current_annonces, keyword, min_price, max_price)


    st.subheader(f"📊 {len(filtered)} annonces trouvées")
    if filtered:
        df = pd.DataFrame(filtered)
        for a in filtered:
            st.markdown(f"""
**[{a['title']}]({a['link']})**  
📍 {a['address']}  
💬 {a['description']}  
💰 {a['price']} €  
📐 {a['keyfacts']}  
🏢 {a['agency']}  
""")
            if a["images"]:
                st.image(a["images"][0], width=400)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Télécharger en CSV", data=csv, file_name="nouvelles_annonces.csv", mime="text/csv")
    else:
        st.info("Aucune nouvelle annonce correspondant à vos critères.")

    save_current(current_annonces)
