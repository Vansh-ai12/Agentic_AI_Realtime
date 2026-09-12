import os
import sys
from pathlib import Path
from dotenv import load_dotenv
sys.path.append(str(Path(__file__).resolve().parents[0]))

env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from db.supabase_client import supabase

print("=" * 80)
print("INSPECTING REAL SUPABASE DATA FOR EVAL CASE CREATION")
print("=" * 80)

# Query documents to see what real content exists
print("\nFetching documents from Supabase...")
try:
    documents_result = supabase.table("documents").select("*").execute()
    documents = documents_result.data
    print(f"Found {len(documents)} documents")
    
    for doc in documents[:10]:  # Show first 10
        print(f"\nDocument ID: {doc['id']}")
        print(f"Source: {doc['source']}")
        print(f"Title: {doc.get('title', 'N/A')}")
        content_preview = doc.get('raw_content', '')[:100]
        print(f"Content preview: {content_preview}")
except Exception as e:
    print(f"Error fetching documents: {e}")
    documents = []

# Query chunks to see what real content exists
print("\n" + "=" * 80)
print("Fetching chunks from Supabase...")
try:
    chunks_result = supabase.table("chunks").select("*").execute()
    chunks = chunks_result.data
    print(f"Found {len(chunks)} chunks")
    
    # Group chunks by document to understand content structure
    from collections import defaultdict
    chunks_by_doc = defaultdict(list)
    for chunk in chunks:
        chunks_by_doc[chunk['document_id']].append(chunk)
    
    print(f"Chunks distributed across {len(chunks_by_doc)} documents")
    
    # Show sample chunk content from different documents
    doc_ids = list(chunks_by_doc.keys())[:5]
    for doc_id in doc_ids:
        doc_chunks = chunks_by_doc[doc_id]
        if doc_chunks:
            # Find the corresponding document title
            doc_title = "Unknown"
            for doc in documents:
                if doc['id'] == doc_id:
                    doc_title = doc.get('title', 'Unknown')
                    break
            
        print(f"Document: {doc_title[:50]}... (ID: {doc_id[:8]}...)")
        print(f"  Chunks: {len(doc_chunks)}")
        content_preview = doc_chunks[0]['content'][:100]
        print(f"  Sample chunk: {content_preview}")
except Exception as e:
    print(f"Error fetching chunks: {e}")
    chunks = []

# Show document sources distribution
print("\n" + "=" * 80)
print("DOCUMENT SOURCES DISTRIBUTION")
print("=" * 80)
source_counts = {}
for doc in documents:
    source = doc['source']
    source_counts[source] = source_counts.get(source, 0) + 1

for source, count in source_counts.items():
    print(f"{source}: {count} documents")

print("\n" + "=" * 80)
print("DATA INSPECTION COMPLETE")
print("=" * 80)
