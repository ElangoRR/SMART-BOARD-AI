import spacy
import json

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    try:
        from spacy.cli import download
        download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")

# Simple cache for results
cache = {}

def extract_keywords(transcript_text, top_n=10, use_cache=True):
    """
    Extract multi-word key phrases from the transcript text using spaCy noun chunks.
    """
    if not transcript_text or not transcript_text.strip():
        return {"keywords": []}

    if use_cache and transcript_text in cache:
        return cache[transcript_text]

    doc = nlp(transcript_text)

    # Extract noun chunks
    if doc.has_annotation("DEP") or hasattr(doc, "noun_chunks"):
        noun_chunks = [chunk.text.lower().strip() for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
    else:
        noun_chunks = [token.text.lower() for token in doc if not token.is_stop and len(token.text) > 2]

    unique_chunks = list(set(noun_chunks))
    sorted_chunks = sorted(unique_chunks, key=len, reverse=True)[:top_n]

    keyword_list = [{"phrase": phrase, "relevance": round(len(phrase.split()) * 0.1, 2)} for phrase in sorted_chunks]
    result = {"keywords": keyword_list}

    if use_cache:
        cache[transcript_text] = result

    return result

def highlight_keywords(transcript_text, keywords):
    """Highlight keywords in the original transcript."""
    highlighted = transcript_text
    for kw in keywords:
        phrase = kw["phrase"]
        highlighted = highlighted.replace(phrase, f"**{phrase}**")
    return highlighted

if __name__ == "__main__":
    sample = "Human evolution is the process of change by which humans originated from ape ancestors."
    result = extract_keywords(sample)
    print(json.dumps(result, indent=4))