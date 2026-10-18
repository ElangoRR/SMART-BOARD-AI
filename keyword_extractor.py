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
            print("Model 'en_core_web_sm' not found locally. Attempting download...")
            try:
                from spacy.cli import download
                download("en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                print(f"Warning: spaCy model download failed: {e}. Falling back to blank English pipeline.")
                self.nlp = spacy.blank("en")

        # Optional KeyBERT check (gracefully disabled by default without error)
        try:
            from keybert import KeyBERT
            self.kw_model = KeyBERT()
            self.use_keybert = True
        except (ImportError, Exception):
            self.use_keybert = False

    def extract(self, transcript, top_n=5):
        """
        Extract relevant keywords and key phrases from transcript using spaCy NLP.
        """
        if not transcript or not transcript.strip():
            return []

        doc = self.nlp(transcript)
        candidates = set()

        # 1. Extract Noun Chunks (e.g., "human evolution", "solar system")
        if doc.has_annotation("DEP") or hasattr(doc, "noun_chunks"):
            try:
                for chunk in doc.noun_chunks:
                    clean_chunk = self._clean_phrase(chunk)
                    if clean_chunk:
                        candidates.add(clean_chunk)
            except Exception:
                pass

        # 2. Extract Named Entities (e.g., "Mars", "Einstein", "NASA")
        if doc.has_annotation("ENT_IOB"):
            try:
                for ent in doc.ents:
                    clean_ent = self._clean_phrase(ent)
                    if clean_ent:
                        candidates.add(clean_ent)
            except Exception:
                pass

        candidate_list = list(candidates)

        # 3. Fallback to significant nouns / proper nouns if chunks are sparse
        if not candidate_list:
            candidate_list = [
                token.text.lower() for token in doc 
                if (token.pos_ in ['NOUN', 'PROPN'] or not token.pos_) and not token.is_stop and len(token.text) > 2
            ]

        # 4. Fallback to non-stopwords if still empty
        if not candidate_list:
            candidate_list = [
                token.text.lower() for token in doc
                if not token.is_stop and not token.is_punct and len(token.text) > 2
            ]

        if not candidate_list:
            return []

        # 5. Rank and score candidate keyphrases
        if self.use_keybert:
            try:
                keywords = self.kw_model.extract_keywords(
                    transcript,
                    candidates=candidate_list,
                    keyphrase_ngram_range=(1, 3),
                    stop_words='english',
                    top_n=top_n
                )
                return [{"phrase": kw[0], "score": round(kw[1], 4)} for kw in keywords]
            except Exception:
                pass

        return self._rank_candidates(candidate_list, transcript, top_n)

    def _clean_phrase(self, span):
        """Clean a spaCy span (remove stopwords/punctuation from ends)."""
        if not span.text.strip():
            return None

        tokens = [t for t in span if not t.is_punct and not t.is_space]
        if not tokens:
            return None

        start = 0
        end = len(tokens)

        while start < end and tokens[start].is_stop:
            start += 1
        while end > start and tokens[end - 1].is_stop:
            end -= 1

        if start >= end:
            return None

        phrase = " ".join([t.text for t in tokens[start:end]]).strip()
        if len(phrase) < 3:
            return None

        return phrase.lower()

    def _rank_candidates(self, candidates, transcript, top_n):
        """Linguistic heuristic relevance scoring based on specificity, word count, and frequency."""
        lower_transcript = transcript.lower()
        scored = []

        for cand in candidates:
            words = cand.split()
            word_count = len(words)
            
            # Base relevance score
            score = 0.5 + (word_count * 0.12)
            if len(cand) > 6:
                score += 0.08
            
            # Frequency boost
            occurrences = lower_transcript.count(cand)
            if occurrences > 1:
                score += min(0.15, occurrences * 0.05)
            
            scored.append({
                "phrase": cand,
                "score": round(min(0.98, score), 2)
            })

        # Sort descending by score, then by length
        scored.sort(key=lambda x: (x['score'], len(x['phrase'])), reverse=True)
        return scored[:top_n]
