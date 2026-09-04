from connectors.notion_connector import ingest_notion
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

result = ingest_notion(
    user_id="c0a65264-dc6c-4198-8e88-7c63c180d1cf",
    connection_id="bf7d525e-1554-4eab-961a-df2ca37027e5",
    access_token=os.getenv("NOTION_TEST_TOKEN")
)
print(result)