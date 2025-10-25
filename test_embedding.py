import vertexai
from vertexai.language_models import TextEmbeddingModel

# Initialize Vertex AI
vertexai.init(project="tafsir-simplified", location="us-central1")

# Test the embedding model
model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
embeddings = model.get_embeddings(["test query"])
print(f"Embedding dimension: {len(embeddings[0].values)}")
print(f"First 5 values: {embeddings[0].values[:5]}")
