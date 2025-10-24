import sys
import os
# get parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print(sys.path)

import os
import re
import torch
import requests
import spacy
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
from dateparser import parse as date_parse
from app.config.settings import settings


nlp = spacy.load("en_core_web_sm")
GOOGLE_PLACES_API_KEY = settings.GOOGLE_PLACES_API_KEY

embedder_main = SentenceTransformer("all-MiniLM-L6-v2")
embedder_e5 = SentenceTransformer("intfloat/e5-base-v2")



def combine_embeddings(text: str):
    e1 = embedder_main.encode(text, convert_to_tensor=True, normalize_embeddings=True)
    e2 = embedder_e5.encode(text, convert_to_tensor=True, normalize_embeddings=True)
    return torch.cat([e1, e2])


def get_place_from_google(query: str):
    """Return only the main city/place name from Google Places Autocomplete."""
    query = query.strip()
    if not query:
        return None

    url_auto = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "key": GOOGLE_PLACES_API_KEY,
        "types": "(cities)"  # restrict to cities
    }
    resp = requests.get(url_auto, params=params).json()
    preds = resp.get("predictions", [])

    if preds:
        # Return only the main city/town name
        return preds[0]["terms"][0]["value"]

    return query.title()


def extract_destination(user_input: str):
    """Dynamic hybrid destination extractor using NLP + embeddings + Google Places."""
    doc = nlp(user_input)

    candidates = [ent.text.strip() for ent in doc.ents if ent.label_ in ["GPE", "LOC", "FACILITY", "ORG"]]

    if not candidates:
        for chunk in doc.noun_chunks:
            if any(tok.pos_ == "PROPN" for tok in chunk):
                candidates.append(chunk.text.strip())

    if not candidates:
        return None

    ref_vec = embedder_main.encode("travel destination or tourist location", convert_to_tensor=True)
    cand_vecs = embedder_main.encode(candidates, convert_to_tensor=True)
    sims = util.cos_sim(ref_vec, cand_vecs)[0]
    top_candidate = candidates[int(torch.argmax(sims))]

    place = get_place_from_google(top_candidate)
    return place


def extract_budget(user_input: str):
    """Handle patterns like 20k, 20000rs, 1 lakh, hajar, thousand etc."""
    text = user_input.lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s?(k|thousand|lakh|rs|inr|₹|hajar)?", text)
    if match:
        num = float(match.group(1))
        unit = match.group(2) or ""
        if "lakh" in unit:
            num *= 100000
        elif "k" in unit or "thousand" in unit:
            num *= 1000
        return f"₹{int(num)}"
    return None


def extract_duration_and_dates(user_input: str):
    duration_days = None
    dates = None

    dur = re.search(r"(\d+)\s*(day|days|week|weeks)", user_input.lower())
    if dur:
        num = int(dur.group(1))
        unit = dur.group(2)
        duration_days = num * 7 if "week" in unit else num

    parsed_date = date_parse(user_input, settings={"PREFER_DATES_FROM": "future"})
    if parsed_date:
        dates = parsed_date.strftime("%Y-%m-%d")

    return duration_days, dates


def classify_trip_type(user_input: str):
    trip_types = [
        "honeymoon", "family", "solo", "friends", "adventure", "relaxing",
        "cultural", "luxury", "budget", "romantic", "business"
    ]
    sims = util.cos_sim(
        combine_embeddings(user_input),
        torch.stack([combine_embeddings(t) for t in trip_types])
    )[0]
    return trip_types[int(torch.argmax(sims))]


def extract_preferences(user_input: str):
    doc = nlp(user_input.lower())
    pref_keywords = [
        "beach", "mountain", "trek", "museum", "shopping", "scuba", "food",
        "adventure", "temple", "heritage", "nightlife", "wildlife",
        "relax", "party", "luxury", "cultural", "nature", "history"
    ]
    prefs = []
    for token in doc:
        if token.lemma_ in pref_keywords and token.lemma_ not in prefs:
            prefs.append(token.lemma_)
    return prefs


def parse_user_input(user_input: str):
    """Unified entrypoint for NLP-NPU preprocessing."""
    destination = extract_destination(user_input)
    budget = extract_budget(user_input)
    duration_days, dates = extract_duration_and_dates(user_input)
    trip_type = classify_trip_type(user_input)
    preferences = extract_preferences(user_input)

    return {
        "destination": destination,
        "duration_days": duration_days,
        "budget": budget,
        "dates": dates,
        "trip_type": trip_type,
        "preferences": preferences,
    }


if __name__ == "__main__":
    user_text = "Plan a short family trip to ahmedabad next weekend under 25k."
    print(parse_user_input(user_text))
