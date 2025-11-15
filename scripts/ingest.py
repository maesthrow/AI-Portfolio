import psycopg
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from settings import get_settings


def load_docs(db_url: str):
    with psycopg.connect(db_url) as conn:
        cur = conn.execute("select id, title, kind, content from documents")
        for row in cur:
            yield {"id": row[0], "title": row[1], "kind": row[2], "content": row[3]}


def main():
    settings = get_settings()

    emb = OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.embedding_model
    )
    db = Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=emb,
        client_kwargs={"host": settings.chroma_host, "port": settings.chroma_port}
    )
    texts, metadatas, ids = [], [], []
    for d in load_docs(settings.database_url):
        texts.append(d["content"])
        metadatas.append({"id": d["id"], "title": d["title"], "kind": d["kind"]})
        ids.append(str(d["id"]))
    if texts:
        db.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        print(f"Indexed {len(texts)} docs.")
    else:
        print("No documents found.")


if __name__ == "__main__":
    main()
