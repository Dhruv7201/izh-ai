import re
import spacy
import torch
from sentence_transformers import SentenceTransformer, util
from dateparser import parse as date_parse
from typing import Dict, Any

# Load language & embedding models
nlp = spacy.load("en_core_web_sm")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Predefined semantic intent clusters
INTENT_EXAMPLES = {
    "plan_trip": [
        "plan a trip",
        "create travel itinerary",
        "make holiday plan",
        "suggest destinations",
        "weekend getaway ideas"
    ],
    "find_food": [
        "find restaurants",
        "recommend local food",
        "best cafes nearby",
        "places to eat",
        "where to have dinner"
    ],
    "translate_text": [
        "translate this text",
        "what does this mean",
        "say this in french",
        "language translation"
    ],
    "check_safety": [
        "is it safe",
        "any travel alerts",
        "emergency nearby",
        "show safe areas",
        "safety warning"
    ],
    "general_query": [
        "general question",
        "tell me more",
        "recommend something",
        "give me info"
    ]
}

# Precompute intent embeddings
INTENT_EMBEDDINGS = {
    key: embedder.encode(value, convert_to_tensor=True) for key, value in INTENT_EXAMPLES.items()
}

def preprocess_text(text: str) -> str:
    """Normalize input text."""
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Z0-9\s,.-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def detect_intent_semantic(text: str) -> str:
    """Semantic intent detection using cosine similarity."""
    input_emb = embedder.encode(text, convert_to_tensor=True)
    best_intent, best_score = None, -1

    for intent, examples_emb in INTENT_EMBEDDINGS.items():
        sim = util.cos_sim(input_emb, examples_emb).max().item()
        if sim > best_score:
            best_score = sim
            best_intent = intent

    return best_intent if best_intent else "general_query"

def extract_entities(text: str) -> Dict[str, Any]:
    """Extract entities like destinations, dates, budget, preferences."""
    doc = nlp(text)
    entities = {"destinations": [], "dates": [], "budget": None, "preferences": []}

    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            entities["destinations"].append(ent.text)

    date_matches = re.findall(r"\b(\d{1,2}\s\w+|\w+\s\d{1,2}|\bnext\s\w+|\bthis\s\w+|\btomorrow|\btoday)\b", text)
    for d in date_matches:
        parsed = date_parse(d)
        if parsed:
            entities["dates"].append(str(parsed.date()))

    match = re.search(r"(under|below|around|upto|budget of)\s?₹?(\d{1,3}(?:,\d{3})*|\d+)", text)
    if match:
        entities["budget"] = int(match.group(2).replace(",", ""))

    preferences = [token.text for token in doc if token.pos_ == "ADJ"]
    entities["preferences"] = list(set(preferences))
    return entities

def enrich_with_profile(entities: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Merge extracted entities with user profile context."""
    enriched = {**entities}
    enriched["user_type"] = user_profile.get("type", "general")
    enriched["home_base"] = user_profile.get("home_city", "")
    enriched["travel_style"] = user_profile.get("style", "balanced")
    enriched["food_pref"] = user_profile.get("food", "any")
    return enriched

def build_gpt_payload(text: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Full NPL + NPU pipeline for structured GPT-4o input."""
    clean_text = preprocess_text(text)
    intent = detect_intent_semantic(clean_text)
    entities = extract_entities(clean_text)
    enriched = enrich_with_profile(entities, user_profile)

    return {
        "intent": intent,
        "query": clean_text,
        "context": enriched
    }

# Example usage
if __name__ == "__main__":
    user_text = "Book me a romantic 5-day Bali honeymoon under ₹80,000 with beaches and nice cafes."
    user_profile = {
        "type": "couple",
        "home_city": "punjab",
        "style": "romantic",
        "food": "vegetarian"
    }

    structured = build_gpt_payload(user_text, user_profile)
    print(structured)
