from langchain_core.prompts import ChatPromptTemplate
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

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(vector_db.db.as_retriever(search_kwargs={"k": chat_settings.RETRIVAL_K}), question_answer_chain)
