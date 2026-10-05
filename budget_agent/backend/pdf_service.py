import fitz  # PyMuPDF
import re
import nltk
import difflib
from nltk.corpus import wordnet

# Automatically download required NLTK datasets on startup
try:
    wordnet.ensure_loaded()
except LookupError:
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)

class PDFStore:
    def __init__(self):
        self.doc = None
        self.doc_id = None
        self.pages_text = {}
        self.headings = []
        self.vocabulary = set()

    def load_pdf(self, file_path: str, doc_id: str):
        """Parses the PDF and stores it in memory for the session."""
        self.doc = fitz.open(file_path)
        self.doc_id = doc_id
        self.pages_text = {}
        self.vocabulary = set()
        
        for i in range(len(self.doc)):
            # Pages are 1-indexed for the agent to make it intuitive
            text = self.doc[i].get_text("text")
            self.pages_text[i + 1] = text
            
            # Extract words (4 letters or more) for our auto-spellchecker
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            self.vocabulary.update(words)
        
        # Extract headings (TOC) if available
        toc = self.doc.get_toc()
        self.headings = [f"Level {item[0]}: {item[1]} (Page {item[2]})" for item in toc]
        
    def list_documents(self):
        if not self.doc:
            return []
        return [{"doc_id": self.doc_id, "total_pages": len(self.doc)}]

    def list_headings(self, doc_id: str):
        if doc_id != self.doc_id:
            return "Error: Document ID mismatch or not found."
        if not self.headings:
            return "No Table of Contents found in this document."
        return self.headings

    def get_page(self, doc_id: str, page_number: int):
        if doc_id != self.doc_id:
            return "Error: Document ID mismatch or not found."
        try:
            page_num = int(page_number)
            if page_num not in self.pages_text:
                return f"Error: Page {page_num} does not exist. Total pages: {len(self.pages_text)}."
            text = self.pages_text[page_num]
            if not text.strip():
                return "Page is empty or contains only images."
            return text
        except ValueError:
            return "Error: page_number must be an integer."

    def search_keyword(self, doc_id: str, keywords: list):
        if doc_id != self.doc_id:
            return "Error: Document ID mismatch or not found."
            
        if not isinstance(keywords, list):
            # Fallback in case LLM passes a string
            keywords = [str(keywords)]
            
        if not keywords or all(not k for k in keywords):
            return "Error: No keywords provided."

        # Start with all pages as valid candidates
        valid_pages = set(range(1, len(self.doc) + 1))
        
        for original_keyword in keywords:
            keyword = str(original_keyword)
            # 0. Auto-Spellcheck!
            keyword_lower = keyword.lower()
            if keyword_lower not in self.vocabulary and len(keyword_lower) >= 4:
                closest = difflib.get_close_matches(keyword_lower, self.vocabulary, n=1, cutoff=0.75)
                if closest:
                    keyword = closest[0]
                    keyword_lower = closest[0]
                    
            # 1. Try exact keyword first
            keyword_matches = set()
            for page_num in range(len(self.doc)):
                if (page_num + 1) not in valid_pages:
                    continue
                page = self.doc.load_page(page_num)
                if page.search_for(keyword):
                    keyword_matches.add(page_num + 1)
                    
            # 2. If exact match fails, fallback to NLTK WordNet synonyms
            if not keyword_matches:
                search_terms = set()
                try:
                    for syn in wordnet.synsets(keyword):
                        for lemma in syn.lemmas():
                            term = lemma.name().replace('_', ' ').lower()
                            if term != keyword_lower:
                                search_terms.add(term)
                except Exception:
                    pass 
                    
                if search_terms:
                    for page_num in range(len(self.doc)):
                        if (page_num + 1) not in valid_pages:
                            continue
                        page = self.doc.load_page(page_num)
                        for term in search_terms:
                            if page.search_for(term):
                                keyword_matches.add(page_num + 1)
            
            # Intersect with the running list of valid pages
            valid_pages = valid_pages.intersection(keyword_matches)
            
            # If at any point the intersection is empty, we fail early
            if not valid_pages:
                return f"No pages found containing ALL of the keywords (or their synonyms): {keywords}"
                
        return sorted(list(valid_pages))

# Singleton instance for the hackathon (single active user state)
pdf_store = PDFStore()
