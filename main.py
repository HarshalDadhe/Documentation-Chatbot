# Full pipeline
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from py_to_JSON import script_to_json

# Step 1: Parse script to JSON
structured = script_to_json("source/CUSTOMER.py")

# Step 2: Serialize JSON sections into LLM-readable text chunks
# When using any Textsplitter or other chunking method, the result is JSON file with metadata and page_content.
# We creating different document/lines for dag, function and queries.
def json_to_text_chunks(data: dict) -> list[Document]:
    chunks = []
    
    # DAG overview chunk
    chunks.append(Document(
        page_content=f"DAG: {data['airflow_metadata']['dag']}\n"
                     f"Schedule: {data['airflow_metadata']['schedule_interval']}\n"
                     f"Operators: {', '.join(data['airflow_metadata']['operators_used'])}",
        metadata={"section": "dag_overview"}
    ))
    
    # Each function as its own chunk
    for fn in data["functions"]:
        chunks.append(Document(
            page_content=f"Function: {fn['name']}\nArgs: {fn['args']}\nDocstring: {fn['docstring']}",
            metadata={"section": "function", "name": fn["name"]}
        ))
    
    # Each SQL query as its own chunk
    for i, sql in enumerate(data["sql_queries"]):
        chunks.append(Document(
            page_content=f"SQL Query {i+1}:\n{sql}",
            metadata={"section": "sql", "index": i}
        ))
    
    return chunks

chunks = json_to_text_chunks(structured)

# Step 3: Embed and store
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma.from_documents(chunks, embeddings)

# Step 4: RAG chain with local LLM
# codellama understands code better, we will try others as well.
llm = Ollama(model="codellama")  # or mistral, codellama, llama3.2 etc.
# 4a. Define the prompt — {context} is injected by the retriever,
#     {input} is the user's question
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a technical documentation assistant. "
     "Use the following retrieved context from an Airflow Python script to answer the question. "
     "Be detailed, structured, and cover all tasks and SQL queries mentioned.\n\n"
     "Context:\n{context}"),
    ("human", "{input}")
])

# 4b. Chain that stuffs retrieved docs into the prompt
combine_docs_chain = create_stuff_documents_chain(llm, prompt)

# 4c. Full retrieval chain: retriever → combine_docs_chain
rag_chain = create_retrieval_chain(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
    combine_docs_chain=combine_docs_chain
)

# Step 5: Generate documentation
response = rag_chain.invoke({
    "input": "Generate complete documentation for this Airflow DAG including all tasks and SQL queries."
})

print(response["answer"])