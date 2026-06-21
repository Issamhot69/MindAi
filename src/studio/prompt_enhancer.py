TRANSLATIONS = {
    "une": "a", "un": "a", "dans": "in", "avec": "with", "sur": "on",
    "et": "and", "le": "the", "la": "the", "les": "the", "de": "of",
    "des": "", "du": "of the", "au": "at the", "aux": "at the",
    "qui": "who", "est": "is", "sont": "are", "a": "has",
    "fille": "girl", "femme": "woman", "homme": "man", "garcon": "boy",
    "vieux": "old", "jeune": "young", "beau": "beautiful", "belle": "beautiful",
    "grand": "tall", "petit": "short", "gros": "fat", "mince": "slim",
    "yeux": "eyes", "bleu": "blue", "vert": "green", "marron": "brown", "noir": "black",
    "cheveux": "hair", "rouge": "red", "blond": "blonde", "brun": "brunette",
    "robe": "dress", "costume": "suit", "chic": "elegant chic",
    "restaurant": "restaurant", "maison": "house", "plage": "beach",
    "foret": "forest", "ville": "city", "montagne": "mountain",
    "nuit": "night", "jour": "day", "coucher de soleil": "sunset",
    "alien": "alien creature", "dragon": "dragon", "robot": "robot",
    "egypte": "ancient Egypt", "palais": "palace", "desert": "desert",
    "mer": "ocean", "espace": "space", "galaxie": "galaxy",
    "debout": "standing", "assis": "sitting", "courir": "running",
    "sourire": "smiling", "triste": "sad", "colere": "angry",
    "pluie": "rain", "neige": "snow", "soleil": "sun",
}

QUALITY_SUFFIX = ", cinematic lighting, professional photography, 8K, hyperrealistic, RAW photo, sharp focus, detailed"

def enhance_prompt(user_input: str) -> str:
    text = user_input.strip()
    
    # Détecte si c est déjà en anglais
    english_words = ["the", "a", "with", "on", "beautiful", "woman", "man", "dragon", "alien"]
    is_english = any(w in text.lower().split() for w in english_words)
    
    if not is_english:
        try:
            from deep_translator import GoogleTranslator
            text = GoogleTranslator(source="auto", target="en").translate(text)
            print(f"🌍 Traduit : {text}")
        except:
            # Fallback : traduction manuelle français
            text = text.lower()
            for fr, en in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
                text = text.replace(fr, en)
    
    # Ajoute la qualité si pas déjà présent
    if "8K" not in text and "cinematic" not in text:
        text += QUALITY_SUFFIX
    
    return text

if __name__ == "__main__":
    tests = [
        "une belle fille avec des yeux bleu dans un restaurant",
        "un dragon dans l espace",
        "un vieux homme triste dans la pluie",
        "alien bleu dans une galaxie",
    ]
    for t in tests:
        print(f"Input:  {t}")
        print(f"Output: {enhance_prompt(t)}")
        print()
