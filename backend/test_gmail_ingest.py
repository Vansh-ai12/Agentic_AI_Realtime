from connectors.gmail_connector import ingest_gmail

result = ingest_gmail(
    user_id="c0a65264-dc6c-4198-8e88-7c63c180d1cf",
    connection_id="7fbb1e79-1846-4268-a689-8a20949ef24a",
    max_results=5
)
print(result)