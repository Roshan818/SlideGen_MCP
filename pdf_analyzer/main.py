from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import re
import json
import sys
from typing import List, Dict, Any
from collections import Counter
import PyPDF2
import fitz  
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

# Add debug output
print("Starting PDF Analyzer MCP Server...", file=sys.stderr)

# Load environment variables
try:
    load_dotenv("../.env")
    print("Environment loaded", file=sys.stderr)
except Exception as e:
    print(f"Environment load error: {e}", file=sys.stderr)

# Initialize MCP
mcp = FastMCP("pdf-analyzer")


# NLTK setup with better error handling
def setup_nltk():
    """Setup NLTK with fallback options"""
    try:
        import nltk

        # Set local NLTK data path
        nltk_data_dir = os.path.join(os.path.dirname(__file__), "nltk_data")
        if os.path.exists(nltk_data_dir):
            nltk.data.path.insert(0, nltk_data_dir)
            print(f"Using local NLTK data: {nltk_data_dir}", file=sys.stderr)

        # Try to find required data
        required_data = {
            "punkt": "tokenizers/punkt",
            "stopwords": "corpora/stopwords",
            "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
            "maxent_ne_chunker": "chunkers/maxent_ne_chunker",
            "words": "corpora/words",
        }

        missing_data = []
        for name, path in required_data.items():
            try:
                nltk.data.find(path)
                print(f"✓ Found {name}", file=sys.stderr)
            except LookupError:
                missing_data.append(name)
                print(f"✗ Missing {name}", file=sys.stderr)

        # Try to download missing data (but don't fail if it doesn't work)
        if missing_data:
            print(
                f"Attempting to download missing NLTK data: {missing_data}",
                file=sys.stderr,
            )
            for data_name in missing_data:
                try:
                    nltk.download(data_name, quiet=True)
                    print(f"Downloaded {data_name}", file=sys.stderr)
                except Exception as e:
                    print(f"Could not download {data_name}: {e}", file=sys.stderr)

        return True

    except ImportError:
        print("NLTK not available - using fallback text processing", file=sys.stderr)
        return False
    except Exception as e:
        print(f"NLTK setup error: {e}", file=sys.stderr)
        return False


# Initialize NLTK
nltk_available = setup_nltk()

# Import NLTK components only if available
if nltk_available:
    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import sent_tokenize, word_tokenize
        from nltk.tag import pos_tag
        from nltk.chunk import ne_chunk

        print("NLTK components loaded successfully", file=sys.stderr)
    except Exception as e:
        print(f"NLTK import error: {e}", file=sys.stderr)
        nltk_available = False


class PDFAnalyzer:
    def __init__(self):
        if nltk_available:
            try:
                self.stop_words = set(stopwords.words("english"))
                print("Using NLTK stopwords", file=sys.stderr)
            except:
                self.stop_words = self._get_basic_stopwords()
                print("Using fallback stopwords", file=sys.stderr)
        else:
            self.stop_words = self._get_basic_stopwords()
            print("Using basic stopwords", file=sys.stderr)

        # Add common academic/document words to stop words
        self.stop_words.update(
            [
                "page",
                "pages",
                "figure",
                "table",
                "section",
                "chapter",
                "appendix",
                "reference",
                "references",
                "et",
                "al",
                "etc",
                "eg",
                "ie",
                "pdf",
                "document",
            ]
        )

    def _get_basic_stopwords(self):
        """Fallback stopwords if NLTK is not available"""
        return set(
            [
                "i",
                "me",
                "my",
                "myself",
                "we",
                "our",
                "ours",
                "ourselves",
                "you",
                "your",
                "yours",
                "yourself",
                "yourselves",
                "he",
                "him",
                "his",
                "himself",
                "she",
                "her",
                "hers",
                "herself",
                "it",
                "its",
                "itself",
                "they",
                "them",
                "their",
                "theirs",
                "themselves",
                "what",
                "which",
                "who",
                "whom",
                "this",
                "that",
                "these",
                "those",
                "am",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "having",
                "do",
                "does",
                "did",
                "doing",
                "a",
                "an",
                "the",
                "and",
                "but",
                "if",
                "or",
                "because",
                "as",
                "until",
                "while",
                "of",
                "at",
                "by",
                "for",
                "with",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "up",
                "down",
                "in",
                "out",
                "on",
                "off",
                "over",
                "under",
                "again",
                "further",
                "then",
                "once",
            ]
        )

    def _basic_sentence_tokenize(self, text):
        """Basic sentence tokenization without NLTK"""
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _basic_word_tokenize(self, text):
        """Basic word tokenization without NLTK"""
        words = re.findall(r"\b\w+\b", text.lower())
        return words

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF for better accuracy"""
        try:
            print(f"Extracting text from: {file_path}", file=sys.stderr)
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            print(f"Extracted {len(text)} characters", file=sys.stderr)
            return text
        except Exception as e:
            print(f"PyMuPDF failed: {e}, trying PyPDF2", file=sys.stderr)
            # Fallback to PyPDF2
            try:
                with open(file_path, "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                return text
            except Exception as e2:
                raise Exception(
                    f"Failed to extract text from PDF: {str(e)}, Fallback error: {str(e2)}"
                )

    def clean_text(self, text: str) -> str:
        """Clean and preprocess text"""
        # Remove excessive whitespace and newlines
        text = re.sub(r"\s+", " ", text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r"[^\w\s.,;:!?()-]", " ", text)
        # Remove URLs and email addresses
        text = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            text,
        )
        text = re.sub(r"\S+@\S+", "", text)
        return text.strip()

    def chunk_text(
        self, text: str, chunk_size: int = 500, overlap: int = 50
    ) -> List[str]:
        """Split text into overlapping chunks"""
        if nltk_available:
            try:
                sentences = sent_tokenize(text)
            except:
                sentences = self._basic_sentence_tokenize(text)
        else:
            sentences = self._basic_sentence_tokenize(text)

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            words = len(sentence.split())

            if current_size + words > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))

                # Start new chunk with overlap
                overlap_sentences = (
                    current_chunk[-overlap // 20 :]
                    if len(current_chunk) > overlap // 20
                    else current_chunk
                )
                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_size += words

        # Add the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def extract_keywords_and_phrases(self, text: str, top_n: int = 20) -> List[str]:
        """Extract important keywords and phrases using TF-IDF"""
        # Tokenize and filter
        if nltk_available:
            try:
                words = word_tokenize(text.lower())
                pos_tags = pos_tag(words)
                important_words = [
                    word for word, pos in pos_tags if pos.startswith(("NN", "JJ", "VB"))
                ]
            except:
                words = self._basic_word_tokenize(text)
                important_words = words
        else:
            words = self._basic_word_tokenize(text)
            important_words = words

        # Filter words
        important_words = [
            word
            for word in important_words
            if word.isalpha() and word not in self.stop_words and len(word) > 2
        ]

        # Use TF-IDF for single words
        if nltk_available:
            try:
                sentences = sent_tokenize(text)
            except:
                sentences = self._basic_sentence_tokenize(text)
        else:
            sentences = self._basic_sentence_tokenize(text)

        if len(sentences) < 2:
            return list(set(important_words[:top_n]))

        # Create TF-IDF vectorizer for phrases
        try:
            vectorizer = TfidfVectorizer(
                max_features=top_n * 2,
                ngram_range=(1, 3),
                stop_words="english",
                min_df=1,
                max_df=0.95,
            )

            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()

            # Get average TF-IDF scores
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            top_indices = mean_scores.argsort()[-top_n:][::-1]

            keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0]
            return keywords
        except Exception as e:
            print(f"TF-IDF failed: {e}, using frequency analysis", file=sys.stderr)
            # Fallback to simple frequency analysis
            word_freq = Counter(important_words)
            return [word for word, _ in word_freq.most_common(top_n)]

    def identify_topics_with_clustering(
        self, chunks: List[str], n_topics: int = 5
    ) -> Dict[int, List[str]]:
        """Use clustering to identify topics and their associated chunks"""
        if len(chunks) < 2:
            return {0: chunks}

        # Adjust number of topics based on content size
        n_topics = min(n_topics, len(chunks))

        try:
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words="english",
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95,
            )

            tfidf_matrix = vectorizer.fit_transform(chunks)

            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_topics, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)

            # Group chunks by cluster
            topics = {}
            for i, label in enumerate(cluster_labels):
                if label not in topics:
                    topics[label] = []
                topics[label].append(chunks[i])

            return topics
        except Exception as e:
            print(f"Clustering failed: {e}, using simple division", file=sys.stderr)
            # Fallback: simple topic division
            chunk_size = len(chunks) // n_topics if len(chunks) >= n_topics else 1
            topics = {}
            for i in range(0, len(chunks), chunk_size):
                topic_id = i // chunk_size
                topics[topic_id] = chunks[i : i + chunk_size]
            return topics

    def generate_topic_summary(self, topic_chunks: List[str]) -> Dict[str, Any]:
        """Generate summary and key points for a topic"""
        combined_text = " ".join(topic_chunks)

        # Extract key phrases
        key_phrases = self.extract_keywords_and_phrases(combined_text, top_n=10)

        # Extract key sentences (simple approach)
        if nltk_available:
            try:
                sentences = sent_tokenize(combined_text)
            except:
                sentences = self._basic_sentence_tokenize(combined_text)
        else:
            sentences = self._basic_sentence_tokenize(combined_text)

        # Score sentences based on keyword frequency
        sentence_scores = {}
        for sentence in sentences:
            score = 0
            if nltk_available:
                try:
                    words = word_tokenize(sentence.lower())
                except:
                    words = self._basic_word_tokenize(sentence)
            else:
                words = self._basic_word_tokenize(sentence)

            for phrase in key_phrases:
                phrase_words = phrase.split()
                if all(word in words for word in phrase_words):
                    score += len(phrase_words)
            sentence_scores[sentence] = score

        # Get top sentences as key points
        top_sentences = sorted(
            sentence_scores.items(), key=lambda x: x[1], reverse=True
        )
        key_points = [sentence for sentence, score in top_sentences[:5] if score > 0]

        if not key_points:  # Fallback if no scored sentences
            key_points = sentences[:3]

        return {
            "key_phrases": key_phrases,
            "key_points": key_points,
            "chunk_count": len(topic_chunks),
        }


@mcp.tool()
async def analyze_pdf(file_path: str, n_topics: int = 5, chunk_size: int = 500) -> str:
    """
    Analyze a PDF file to extract topics and key information.

    Args:
        file_path: Path to the PDF file to analyze
        n_topics: Number of topics to identify (default: 5)
        chunk_size: Size of text chunks for processing (default: 500 words)

    Returns:
        JSON string containing structured analysis of the PDF with topics and key points
    """
    try:
        print(f"Analyzing PDF: {file_path}", file=sys.stderr)

        if not os.path.exists(file_path):
            return json.dumps({"error": f"File not found: {file_path}"})

        if not file_path.lower().endswith(".pdf"):
            return json.dumps({"error": "File must be a PDF"})

        analyzer = PDFAnalyzer()

        # Extract and process text
        raw_text = analyzer.extract_text_from_pdf(file_path)

        if not raw_text.strip():
            return json.dumps({"error": "No text could be extracted from the PDF"})

        cleaned_text = analyzer.clean_text(raw_text)

        # Create chunks
        chunks = analyzer.chunk_text(cleaned_text, chunk_size=chunk_size)

        # Identify topics through clustering
        topics = analyzer.identify_topics_with_clustering(chunks, n_topics=n_topics)

        # Analyze each topic
        analysis_result = {
            "file_path": file_path,
            "total_chunks": len(chunks),
            "text_length": len(cleaned_text),
            "topics": {},
        }

        for topic_id, topic_chunks in topics.items():
            topic_summary = analyzer.generate_topic_summary(topic_chunks)

            analysis_result["topics"][f"Topic_{topic_id + 1}"] = {
                "summary": {
                    "key_phrases": topic_summary["key_phrases"],
                    "key_points": topic_summary["key_points"],
                    "chunks_in_topic": topic_summary["chunk_count"],
                },
                "sample_text": topic_chunks[0][:200] + "..."
                if len(topic_chunks[0]) > 200
                else topic_chunks[0],
            }

        # Add overall document keywords
        overall_keywords = analyzer.extract_keywords_and_phrases(cleaned_text, top_n=15)
        analysis_result["overall_keywords"] = overall_keywords

        print("Analysis completed successfully", file=sys.stderr)
        return json.dumps(analysis_result, indent=2)

    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        print(error_msg, file=sys.stderr)
        return json.dumps({"error": error_msg})


@mcp.tool()
async def extract_pdf_text(file_path: str) -> str:
    """
    Extract raw text from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text from the PDF
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if not file_path.lower().endswith(".pdf"):
            return "Error: File must be a PDF"

        analyzer = PDFAnalyzer()
        text = analyzer.extract_text_from_pdf(file_path)

        if not text.strip():
            return "Error: No text could be extracted from the PDF"

        return text

    except Exception as e:
        return f"Error extracting text: {str(e)}"


@mcp.tool()
async def get_pdf_keywords(file_path: str, top_n: int = 20) -> str:
    """
    Extract keywords and key phrases from a PDF.

    Args:
        file_path: Path to the PDF file
        top_n: Number of top keywords to return (default: 20)

    Returns:
        JSON string containing the extracted keywords
    """
    try:
        if not os.path.exists(file_path):
            return json.dumps({"error": f"File not found: {file_path}"})

        analyzer = PDFAnalyzer()
        text = analyzer.extract_text_from_pdf(file_path)
        cleaned_text = analyzer.clean_text(text)

        keywords = analyzer.extract_keywords_and_phrases(cleaned_text, top_n=top_n)

        return json.dumps(
            {
                "file_path": file_path,
                "keywords": keywords,
                "total_keywords": len(keywords),
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps({"error": f"Keyword extraction failed: {str(e)}"})


if __name__ == "__main__":
    print("PDF Analysis MCP Server starting...", file=sys.stderr)
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        raise
