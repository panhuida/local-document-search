
import os
import sys
from tqdm import tqdm

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Document
import jieba
from sqlalchemy import func, text

# Define a limit for the text to be indexed, slightly less than 1MB
TSVECTOR_MAX_LENGTH = 1000000

def reindex_all_documents():
    """
    Iterates through all documents in the database and re-generates the 
    search_vector using jieba, truncating long texts to avoid errors.
    """
    app = create_app()
    with app.app_context():
        print("Starting re-indexing process for full-text search...")
        
        try:
            total_docs = db.session.query(Document.id).count()
            if total_docs == 0:
                print("No documents in the database to re-index.")
                return

            batch_size = 100
            
            with tqdm(total=total_docs, desc="Re-indexing documents") as pbar:
                for offset in range(0, total_docs, batch_size):
                    docs_batch = db.session.query(Document).offset(offset).limit(batch_size).all()
                    
                    for doc in docs_batch:
                        # Truncate content before segmentation
                        file_name_truncated = (doc.file_name or '')[:TSVECTOR_MAX_LENGTH]
                        content_truncated = (doc.markdown_content or '')[:TSVECTOR_MAX_LENGTH]

                        # Segment the truncated text
                        file_name_segmented = " ".join(jieba.cut_for_search(file_name_truncated))
                        content_segmented = " ".join(jieba.cut_for_search(content_truncated))
                        
                        # Combine, ensuring the total length does not exceed the limit again
                        full_text = (file_name_segmented + " " + content_segmented)[:TSVECTOR_MAX_LENGTH]
                        
                        update_stmt = text("""
                            UPDATE documents
                            SET search_vector = to_tsvector('simple', :full_text)
                            WHERE id = :doc_id
                        """)
                        db.session.execute(update_stmt, {'full_text': full_text, 'doc_id': doc.id})

                    db.session.commit()
                    pbar.update(len(docs_batch))

            print("\nRe-indexing completed successfully!")

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            db.session.rollback()

if __name__ == '__main__':
    reindex_all_documents()
