# Full pipeline
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.schema import Document
from py_to_JSON import script_to_json

# Step 1: Parse script to JSON
structured = script_to_json("my_dag.py")

# Step 2: Serialize JSON sections into LLM-readable text chunks
def json_to_text_chunks(data: dict) -> list[Document]:
    chunks = []
    
    # DAG overview chunk
    chunks.append(Document(
        page_content=f"DAG: {data['airflow_metadata']['dag_id']}\n"
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
llm = Ollama(model="codellama")  # or mistral, codellama, llama3.2 etc.
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
)

# Step 5: Generate documentation
response = qa_chain.invoke(
    "Generate complete documentation for this Airflow DAG including all tasks and SQL queries."
)
print(response["result"])