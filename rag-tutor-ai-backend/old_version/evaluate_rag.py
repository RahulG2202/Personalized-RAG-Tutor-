import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# 1. Setup
load_dotenv()
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory="./chroma_db",
                   embedding_function=embeddings)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


def run_accuracy_test(question, ground_truth=None):
    print(f"\n{'='*60}\nTESTING QUESTION: {question}")

    # 2. STEP ONE: Test Retrieval Accuracy
    # Let's see exactly what the "Search Engine" found
    retrieved_docs = vector_db.similarity_search(question, k=3)

    print("\n[PHASE 1: RETRIEVAL]")
    for i, doc in enumerate(retrieved_docs):
        source = doc.metadata.get('source_file', 'Unknown')
        content_preview = doc.page_content[:200].replace('\n', ' ')
        print(f"Chunk {i+1} (Source: {source}): {content_preview}...")

    # 3. STEP TWO: Test Generation Accuracy
    context = "\n".join([doc.page_content for doc in retrieved_docs])
    prompt = f"""
    Answer the question based ONLY on the context below. 
    If the answer isn't there, say "Data not found".
    
    Context: {context}
    Question: {question}
    Answer:"""

    response = llm.invoke(prompt)
    answer = response.content
    print(f"\n[PHASE 2: GENERATION]\nTutor: {answer}")

    # 4. STEP THREE: LLM-as-a-Judge (Self-Grading)
    # We ask the AI to be its own teacher and grade its faithfulness
    grade_prompt = f"""
    You are an Accuracy Auditor.
    FACTS FROM PDF: {context}
    AI ANSWER: {answer}
    
    On a scale of 1-10:
    1. FAITHFULNESS: (Is the answer supported ONLY by the PDF facts?)
    2. RELEVANCE: (Did it actually answer the question?)
    
    Provide a score and a brief reason.
    """

    grade = llm.invoke(grade_prompt)
    print(f"\n[PHASE 3: ACCURACY SCORE]\n{grade.content}\n{'='*60}")


if __name__ == "__main__":
    # Add 3 specific questions from your PDF here
    test_queries = [
        "Who founded the Han dynasty?",
        "How many inhabitants were in Mohenjo Daro?",
        "What are the main contents of the Vedas?"
    ]

    for q in test_queries:
        run_accuracy_test(q)
