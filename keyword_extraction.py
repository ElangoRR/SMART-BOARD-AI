import spacy
import json

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Simple cache for results
cache = {}

def extract_keywords(transcript_text, top_n=10, use_cache=True):
    """
    Extract multi-word key phrases from the transcript text using spaCy noun chunks.

    Args:
        transcript_text (str): The input transcript.
        top_n (int): Number of top keywords to extract.
        use_cache (bool): Whether to use caching for repeated inputs.

    Returns:
        dict: A dictionary with keywords list.
    """
    if use_cache and transcript_text in cache:
        return cache[transcript_text]

    # Process the text with spaCy
    doc = nlp(transcript_text)

    # Extract noun chunks (multi-word phrases)
    noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]

    # Remove duplicates and filter
    unique_chunks = list(set(noun_chunks))

    # Sort by length (longer phrases first) and take top_n
    sorted_chunks = sorted(unique_chunks, key=len, reverse=True)[:top_n]

    # Format the output with dummy relevance scores (based on length)
    keyword_list = [{"phrase": phrase, "relevance": round(len(phrase.split()) * 0.1, 2)} for phrase in sorted_chunks]

    result = {
        "keywords": keyword_list
    }

    if use_cache:
        cache[transcript_text] = result

    return result

def highlight_keywords(transcript_text, keywords):
    """
    Highlight keywords in the original transcript (optional enhancement).

    Args:
        transcript_text (str): Original transcript.
        keywords (list): List of keyword dicts.

    Returns:
        str: Transcript with keywords highlighted.
    """
    highlighted = transcript_text
    for kw in keywords:
        phrase = kw["phrase"]
        highlighted = highlighted.replace(phrase, f"**{phrase}**")
    return highlighted

def handle_ambiguous_terms(keywords):
    """
    Placeholder for handling ambiguous terms.

    For now, just return as is.
    """
    return keywords

if __name__ == "__main__":
    # Example usage
    sample_transcript = "Human evolution is the process of change by which humans originated from ape ancestors — a journey spanning millions of years, marked by key stages like Homo Sapiens. This evolution involved significant biological and behavioral shifts such as walking on two legs, development of larger brains, and discovery of fire."
    result = extract_keywords(sample_transcript)
    print(json.dumps(result, indent=4))

    # With highlighting
    highlighted = highlight_keywords(sample_transcript, result["keywords"])
    print("\nHighlighted Transcript:")
    print(highlighted)