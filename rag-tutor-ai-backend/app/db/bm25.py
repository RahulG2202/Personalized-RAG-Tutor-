import hashlib
from collections import Counter, defaultdict

import bm25s


def token_to_pinecone_index(token: str):
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


def to_pinecone_sparse_vector(weighted_indices: dict[int, float]):
    items = [
        (index, value)
        for index, value in weighted_indices.items()
        if value > 0
    ]
    items.sort(key=lambda item: item[0])

    return {
        "indices": [int(index) for index, _ in items],
        "values": [float(value) for _, value in items]
    }


def map_bm25s_scores_to_pinecone_sparse_vectors(scores, vocab_dict):
    num_docs = int(scores.get("num_docs", 0) or 0)
    document_weights = [defaultdict(float) for _ in range(num_docs)]
    token_by_id = {
        int(token_id): str(token)
        for token, token_id in vocab_dict.items()
    }
    data = scores["data"]
    indices = scores["indices"]
    indptr = scores["indptr"]

    for token_id in range(len(indptr) - 1):
        token = token_by_id.get(token_id)

        if not token:
            continue

        pinecone_index = token_to_pinecone_index(token)

        for score_index in range(int(indptr[token_id]), int(indptr[token_id + 1])):
            doc_index = int(indices[score_index])
            value = float(data[score_index])

            if value > 0:
                document_weights[doc_index][pinecone_index] += value

    return [
        to_pinecone_sparse_vector(weights)
        for weights in document_weights
    ]


class BM25SparseEncoder:
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        stopwords: str | list[str] = "english"
    ):
        self.k1 = k1
        self.b = b
        self.stopwords = stopwords

    def encode_documents(self, texts: list[str]):
        if not texts:
            return []

        tokenized_documents = bm25s.tokenize(
            texts,
            stopwords=self.stopwords,
            return_ids=False,
            show_progress=False
        )
        retriever = bm25s.BM25(k1=self.k1, b=self.b)
        retriever.index(tokenized_documents, show_progress=False)

        return map_bm25s_scores_to_pinecone_sparse_vectors(
            retriever.scores,
            retriever.vocab_dict
        )

    def encode_query(self, text: str):
        tokenized_query = bm25s.tokenize(
            text,
            stopwords=self.stopwords,
            return_ids=False,
            show_progress=False
        )
        tokens = tokenized_query[0] if tokenized_query else []
        token_counts = Counter(tokens)
        weighted_indices = {
            token_to_pinecone_index(token): float(count)
            for token, count in token_counts.items()
        }

        return to_pinecone_sparse_vector(weighted_indices)
