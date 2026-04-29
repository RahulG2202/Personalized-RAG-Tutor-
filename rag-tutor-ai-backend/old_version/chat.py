from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=FutureWarning)
os.environ["TOKENIZERS_PARALLELISM"] = "False"
os.environ["ANONYMIZED_TELEMETRY"] = "False"


# 1. Disable Chroma Telemetry (Stops those messy capture() errors)
# from chromadb.config import Settings
# client_settings = Settings(anonymized_telemetry=False)

# 2. Load API Key
load_dotenv()


def start_tutor():
    # 3. Load Embedding Model
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 4. Connect to ChromaDB
    vector_db = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings
    )

    # 5. Initialize Gemini
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7  # Makes the tutor a bit more creative/friendly
    )

    # 6. Create the Tutor Persona
    system_prompt = (
        "You are a friendly and specialized Personalized Learning Tutor. "
        "Your goal is to explain concepts using ONLY the provided context. "

        "RULES FOR ACCURACY:"
        "1. If the answer is not in the context, say 'I'm sorry, my current study materials don't cover that specific detail. Would you like to ask something else about the Han Dynasty?'"
        "2. Always cite the source PDF name at the end of your answer."
        "3. Be educational: Explain the 'Why' behind a fact."
        "4. If the student's question is vague, use the context to ask a clarifying question."
        "Keep your explanation simple, educational, and encouraging."

        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # 7. Create the Retrieval Chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(
        vector_db.as_retriever(), question_answer_chain)

    print("\n--- Hello! I am your AI Tutor. Ask me anything about your PDF. ---\n")

    while True:
        query = input("Student: ")
        if query.lower() == "exit":
            break

        print("\nTutor is thinking...")
        try:
            response = rag_chain.invoke({"input": query})
            print(f"\nTutor: {response['answer']}\n")
        except Exception as e:
            print(f"\n[Error]: {e}")
            print(
                "Tip: Make sure your GOOGLE_API_KEY is correct and you have internet access.\n")

        print("-" * 50)


if __name__ == "__main__":
    start_tutor()
