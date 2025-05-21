# Import and re-export functionality from lda_topic_modeler.py
from analysis.lda_topic_modeler import (
    clean_text_for_lda, tokenize_text, create_lda_model,
    extract_topic_keywords, assign_topic_names, 
    analyze_topics_with_lda, analyze_article_topics_with_lda
)

import gensim
from gensim import corpora
from gensim.models import LdaModel

class LdaModel_Test:
    """
    A wrapper class for LDA topic modeling functionality.
    This class is referenced in routes.py and provides a simpler interface
    to the more complex functions in lda_topic_modeler.py
    """
    
    def __init__(self, num_topics=5, passes=10, random_state=42):
        self.num_topics = num_topics
        self.passes = passes
        self.lda_model = None
        self.dictionary = None
        self.topics = None
        
    def train(self, documents):
        """
        Train the LDA model on the provided documents
        """
        if not documents or len(documents) == 0:
            print("Warning: No documents provided for training")
            return
            
        # Clean and tokenize texts
        cleaned_texts = [clean_text_for_lda(doc) for doc in documents]
        tokenized_texts = [tokenize_text(text) for text in cleaned_texts]
        
        # Create dictionary and corpus
        self.dictionary = corpora.Dictionary(tokenized_texts)
        corpus = [self.dictionary.doc2bow(text) for text in tokenized_texts]
        
        # Create and train LDA model
        self.lda_model = LdaModel(
            corpus=corpus,
            id2word=self.dictionary,
            num_topics=self.num_topics,
            passes=self.passes,
            random_state=42
        )
        
        # Extract topics
        raw_topics = extract_topic_keywords(self.lda_model)
        self.topics = assign_topic_names(raw_topics)
        
        print(f"Model trained with {self.num_topics} topics")
        
    def get_topics(self):
        """
        Return the topics from the trained model
        """
        if not self.lda_model or not self.topics:
            print("Model not trained yet")
            return []
            
        return self.topics
    
    def predict_topic(self, text):
        """
        Predict the topic distribution for a new document
        """
        if not self.lda_model or not self.dictionary:
            print("Model not trained yet")
            return None
            
        # Clean and tokenize the text
        cleaned_text = clean_text_for_lda(text)
        tokenized_text = tokenize_text(cleaned_text)
        
        # Convert to bag of words
        bow = self.dictionary.doc2bow(tokenized_text)
        
        # Get topic distribution
        return self.lda_model.get_document_topics(bow)
    
    @staticmethod
    def analyze_article_topics(article_id, db_session, num_topics=5, force_refresh=False):
        """
        Static method to analyze topics for an article's comments
        """
        return analyze_article_topics_with_lda(
            article_id, 
            db_session, 
            num_topics=num_topics, 
            force_refresh=force_refresh
        ) 