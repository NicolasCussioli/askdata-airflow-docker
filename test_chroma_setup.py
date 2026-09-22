import chromadb

# 1. Configurar o cliente persistente (cria ou usa a pasta ./chroma_db)
client = chromadb.PersistentClient(path="./chroma_db")

# 2. Criar ou obter a colecao configurada com distancia de cosseno
collection = client.get_or_create_collection(
    name="teste_configuracao",
    metadata={"hnsw:space": "cosine"}
)

# 3. Teste de insercao direta (sem chamada de API externa)
collection.upsert(
    ids=["doc_1", "doc_2"],
    documents=["Documentacao oficial sobre engenharia de software.", "Manual de boas praticas da DataLakers."],
    embeddings=[[0.1] * 768, [0.9] * 768], # Vetores de teste
    metadatas=[{"arquivo": "manual.pdf", "pagina": 1}, {"arquivo": "doc.pdf", "pagina": 5}]
)

# 4. Inspecionar o banco vetorial
print("=" * 50)
print(f"Total de documentos na colecao: {collection.count()}")
print("Amostra dos metadados:", collection.peek()["metadatas"])
print("=" * 50)
print("ChromaDB configurado e persistindo localmente com sucesso!")