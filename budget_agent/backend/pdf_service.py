import fitz  # PyMuPDF
import re

class PDFStore:
    def __init__(self):
        self.doc = None
        self.doc_id = None
        self.pages_text = {}
        self.headings = []

    def load_pdf(self, file_path: str, doc_id: str):
        """Parses the PDF and stores it in memory for the session."""
        self.doc = fitz.open(file_path)
        self.doc_id = doc_id
        self.pages_text = {}
        for i in range(len(self.doc)):
            # Pages are 1-indexed for the agent to make it intuitive
            self.pages_text[i + 1] = self.doc[i].get_text("text")
        
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

    def search_keyword(self, doc_id: str, keyword: str):
        if doc_id != self.doc_id:
            return "Error: Document ID mismatch or not found."
        
        # PyMuPDF's search_for is highly optimized and case-insensitive by default
        matches = []
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            if page.search_for(keyword):
                matches.append(page_num + 1)
        
        if not matches:
            return f"Keyword '{keyword}' not found in the document."
            
        return matches

# Singleton instance for the hackathon (single active user state)
pdf_store = PDFStore()
