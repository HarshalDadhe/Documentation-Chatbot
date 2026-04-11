#LangChain TextLoader (better for pipelines)
from langchain_community.document_loaders import TextLoader

loader = TextLoader("source/CUSTOMER.py", encoding="utf-8")
documents = loader.load()
raw_code = documents[0].page_content
#print(raw_code)

#For Chunking
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=1000,
    chunk_overlap=100
)
chunks = splitter.create_documents([raw_code])
print(chunks)