from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import global_settings, chat_settings
from app.db.database import vector_db


def get_rag_chat():
    llm = ChatGoogleGenerativeAI(
        model=chat_settings.LLM_MODEL,
        google_api_key=global_settings.GOOGLE_API_KEY,
        temperature=chat_settings.TEMPERATURE
    )

    system_prompt = (
        "You are a friendly and specialized Personalized Learning Tutor.\n"
        "Your goal is to explain concepts using ONLY the provided context.\n\n"
        "RULES FOR ACCURACY:\n"
        "1. If the answer is not in the context, say 'I'm sorry, my current study materials don't cover that specific detail. Would you like to ask something else from your uploaded material?'\n"
        "2. Do not append source PDF names in the answer text; the application shows retrieved PDFs separately.\n"
        "3. Be educational: Explain the 'Why' behind a fact.\n"
        "4. If the student's question is vague, use the context to ask a clarifying question.\n"
        "Keep your explanation simple, educational, and encouraging.\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    retriever = RunnableLambda(
        lambda inputs: vector_db.hybrid_search(
            inputs["input"],
            k=chat_settings.RETRIVAL_K,
            alpha=chat_settings.HYBRID_ALPHA
        )
    )
    return create_retrieval_chain(retriever, question_answer_chain)
