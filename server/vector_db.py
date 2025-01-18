#  Date: 18.01.2025
# 
#  Author: Amanda Uccello
#  Class: ICS4UR-1
#  School: Port Credit Secondary School
#  Teacher: Mrs. Kim
#  Description: 
#      Handles the weaviate vector database connection and queries
#      Used for handling the document questions

import os
import fitz  # PyMuPDF
import weaviate
from weaviate.classes.config import Configure, Property, DataType, Tokenization
from datetime import datetime


# Initialize the client
headers = {
    "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
} 
weaviate_client = weaviate.connect_to_local(headers=headers)

doc_collection = weaviate_client.collections.get("Document")
if doc_collection is None:
    # Create a new collection
    weaviate_client.collections.create(
                        "Document",
                        # vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
                        vectorizer_config = Configure.Vectorizer.text2vec_openai(vectorize_collection_name=True),
                        properties= [  # properties configuration is optional
                            # Property(name="title", data_type=DataType.TEXT),
                            # Property(name="summary", data_type=DataType.TEXT),
                            Property(name="content", data_type=DataType.TEXT, vectorize_property_name=True,tokenization=Tokenization.LOWERCASE),
                            Property(name="upload_date", data_type=DataType.DATE),
                            ]
                        )



def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    # Open the PDF from bytes
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text

def ingest_text_to_weaviate(content: str) -> None:
    # Create a new document
    document = {
        "content": content,
        "upload_date": datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    }
    uuid = weaviate_client.collections.get("Document").data.insert(document)
    print(f"Document with UUID {uuid} has been created")

def search_documents(text: str) -> dict:
    # Search for similar documents

    collection = weaviate_client.collections.get("Document")
    search_results = collection.query.near_text(
        query=text,
        limit=2
    )

    docs = search_results.objects

    return docs
