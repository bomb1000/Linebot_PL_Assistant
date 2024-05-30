import os
import psycopg2
from sqlalchemy import create_engine, text as sql_text
import openai
import configparser
from langchain_openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import ChatOpenAI

# Set OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize embedding model and pass API key explicitly
embeddings = OpenAIEmbeddings(openai_api_key=openai.api_key)

# Connect to PostgreSQL using environment variables
connection_string = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@" \
                    f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(connection_string)

# Create connection and run SQL command to install pgvector extension
with engine.connect() as connection:
    connection.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector;"))
    result = connection.execute(sql_text("SELECT extname FROM pg_extension WHERE extname = 'vector';")).fetchone()
    if result:
        print("pgvector extension enabled successfully")
        vector_check = connection.execute(sql_text("SELECT typname FROM pg_type WHERE typname = 'vector';")).fetchone()
        if vector_check:
            print("vector type enabled successfully")
        else:
            raise Exception("vector type not enabled successfully")
    else:
        raise Exception("pgvector extension not enabled successfully")

def get_query_embedding(query):
    return embeddings.embed_query(query)

def search_documents(query_embedding):
    with engine.connect() as connection:
        query_embedding_str = ','.join(map(str, query_embedding))
        search_query = f"""
        SELECT content, 1 - (embedding <=> '[{query_embedding_str}]'::vector) AS similarity
        FROM documents_week6
        ORDER BY similarity DESC
        LIMIT 5;
        """
        result = connection.execute(sql_text(search_query))
        docs = [{'content': row[0], 'similarity': row[1]} for row in result]
    return docs

def format_docs(docs):
    return "\n\n".join(doc['content'] for doc in docs)

custom_prompt_template = """
system: You are a highly knowledgeable teaching assistant for a data science course. You are well-versed in the course material and lectures, which are summarized in the "Context" provided. Use the retrieved context to answer the question or fulfill the user's requests. If the information is not available, respond with "I don't know."

user: {question}
Context: {context}

assistant:
"""

llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai.api_key, temperature=0.7, max_tokens=4096)

class ContextWithDocs:
    def __init__(self, docs):
        self.docs = docs

    def __call__(self, inputs):
        formatted_docs = format_docs(self.docs)
        return {"context": formatted_docs, "question": inputs}

class CustomPrompt:
    def __init__(self, template):
        self.template = template

    def __call__(self, inputs):
        return self.template.format(**inputs)

def generate_response(query):
    query_embedding = get_query_embedding(query)
    docs = search_documents(query_embedding)
    
    context_with_docs = ContextWithDocs(docs)
    formatted_inputs = context_with_docs(query)
    
    custom_prompt = CustomPrompt(custom_prompt_template)
    prompt_input = custom_prompt(formatted_inputs)
    
    messages = [
        {"role": "system", "content": "You are a highly knowledgeable teaching assistant for a data science course. You are well-versed in the course material and lectures, which are summarized in the \"Context\" provided. Use the retrieved context to answer the question or fulfill the user's requests. If the information is not available, respond with \"I don't know.\""},
        {"role": "user", "content": f"Question: {formatted_inputs['question']}\nContext: {formatted_inputs['context']}\nAnswer:"}
    ]
    response = llm.invoke(messages)
    
    return response.content
