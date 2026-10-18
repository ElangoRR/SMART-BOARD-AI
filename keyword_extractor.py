import spacy
import warnings
from collections import Counter

# Suppress warnings from libraries
warnings.filterwarnings("ignore")

class KeywordExtractor:
    def __init__(self):
        print("Loading spaCy model...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Downloading spaCy model 'en_core_web_sm'...")
            from spacy.cli import download
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

        print("Loading KeyBERT model...")
        try:
            from keybert import KeyBERT
            self.kw_model = KeyBERT()
            self.use_keybert = True
        except ImportError:
            print("KeyBERT not found. Falling back to spaCy-only extraction.")
            self.use_keybert = False
        except Exception as e:
            print(f"Error loading KeyBERT: {e}. Falling back to spaCy-only.")
            self.use_keybert = False

    def extract(self, transcript, top_n=5):
        """
        Extract keywords from transcript using spaCy and KeyBERT.
        """
        if not transcript or not transcript.strip():
            return []

        # 1. Preprocessing with spaCy
        doc = self.nlp(transcript)
        
        # Extract candidates: Noun chunks and Named Entities
        candidates = set()
        
        # Noun chunks (e.g., "human evolution", "solar system")
        for chunk in doc.noun_chunks:
            clean_chunk = self._clean_phrase(chunk)
            if clean_chunk:
                candidates.add(clean_chunk)
                
        # Named entities (e.g., "Mars", "Einstein")
        for ent in doc.ents:
            clean_ent = self._clean_phrase(ent)
            if clean_ent:
                candidates.add(clean_ent)

        candidate_list = list(candidates)
        
        # If no candidates found, fallback to simple nouns
        if not candidate_list:
            candidate_list = [token.text.lower() for token in doc if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop]

        if not candidate_list:
            return []

        results = []

        # 2. Scoring/Ranking
        if self.use_keybert:
            try:
                # KeyBERT can rank specific candidates against the document
                # We use the candidates we found to guide KeyBERT
                keywords = self.kw_model.extract_keywords(
                    transcript, 
                    candidates=candidate_list, 
                    keyphrase_ngram_range=(1, 3), 
                    stop_words='english', 
                    top_n=top_n
                )
                # Format: [(phrase, score), ...]
                results = [{"phrase": kw[0], "score": round(kw[1], 4)} for kw in keywords]
            except Exception as e:
                print(f"KeyBERT extraction failed: {e}. Using fallback.")
                results = self._fallback_scoring(candidate_list, top_n)
        else:
            results = self._fallback_scoring(candidate_list, top_n)

        return results

    def _clean_phrase(self, span):
        """Clean a spaCy span (remove stopwords/punctuation from ends)."""
        # Filter out spans that are just stopwords or punctuation
        if not span.text.strip():
            return None
            
        # Convert to list of tokens to check content
        tokens = [t for t in span if not t.is_punct and not t.is_space]
        
        if not tokens:
            return None
            
        # Remove leading/trailing stopwords
        start = 0
        end = len(tokens)
        
        while start < end and tokens[start].is_stop:
            start += 1
        while end > start and tokens[end-1].is_stop:
            end -= 1
            
        if start >= end:
            return None
            
        # Reconstruct phrase
        phrase = " ".join([t.text for t in tokens[start:end]])
        
        # Filter very short phrases unless they are entities
        if len(phrase) < 3:
            return None
            
        return phrase.lower()

    def _fallback_scoring(self, candidates, top_n):
        """Simple scoring based on length and word count as a heuristic."""
        # Prefer longer phrases (more specific)
        scored = []
        for cand in candidates:
            score = 0.5 + (len(cand.split()) * 0.1) # Boost multi-word
            if len(cand) > 4: score += 0.1
            scored.append({"phrase": cand, "score": round(score, 2)})
        
        # Sort by score desc
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_n]
