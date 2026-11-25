param([Parameter(Mandatory=$true)][string]$Delivery)
$ErrorActionPreference = "Stop"
$Delivery = (Resolve-Path $Delivery).Path
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$storage = Join-Path $Delivery "qdrant_storage"
$zip = "$Delivery.zip"
if (Test-Path $zip) { throw "ZIP already exists: $zip" }
New-Item -ItemType Directory -Path $storage -Force | Out-Null
$server = "team13-fy-" + [guid]::NewGuid().ToString("N")
docker run -d --name $server --mount "type=bind,source=$storage,target=/qdrant/storage" qdrant/qdrant:v1.14.0
if ($LASTEXITCODE) { throw "Qdrant startup failed" }
try {
    @"
import json, time
from pathlib import Path
from qdrant_client import QdrantClient
from hybrid_search.config import load_config
from hybrid_search.models.document import Chunk
from hybrid_search.indexing.qdrant_index import QdrantIndexManager

db = QdrantClient(url='http://127.0.0.1:6333', timeout=120)
for attempt in range(60):
    try:
        db.get_collections()
        break
    except Exception:
        if attempt == 59:
            raise
        time.sleep(1)
mgr = QdrantIndexManager(config=load_config(), client=db)
assert mgr.collection_name == 'team_docs'
with Path('data/processed/chunks.jsonl').open(encoding='utf-8') as f:
    chunks = [Chunk.model_validate_json(line) for line in f if line.strip()]
expected = {c.chunk_id: c for c in chunks}
assert len(expected) == len(chunks) == 13137
mgr.index_chunks(chunks, batch_size=4)
seen = set()
offset = None
while True:
    points, offset = db.scroll('team_docs', offset=offset, limit=128, with_payload=True)
    for point in points:
        r = point.payload
        c = expected[r['chunk_id']]
        assert r['fiscal_period'] == c.fiscal_period and r['text'] == c.text
        seen.add(c.chunk_id)
    if offset is None:
        break
assert len(seen) == db.count('team_docs', exact=True).count == len(expected)
print('Verified 13137 stored chunks and fiscal labels')
"@ | docker run --rm -i --network "container:$server" -w /project -e PYTHONPATH=/project/src -e PYTHONUNBUFFERED=1 -e QDRANT_COLLECTION=team_docs --mount "type=bind,source=$repo/src,target=/project/src,readonly" --mount "type=bind,source=$repo/config,target=/project/config,readonly" --mount "type=bind,source=$Delivery/data,target=/project/data,readonly" --entrypoint python hybrid-finance:da-index -
    if ($LASTEXITCODE) { throw "Index or verification failed" }
} finally {
    docker stop -t 60 $server
    if ($LASTEXITCODE) { throw "Qdrant stop failed" }
    docker rm $server
}
tar.exe -a -cf $zip -C $Delivery data qdrant_storage
if ($LASTEXITCODE) { throw "ZIP creation failed" }
Write-Host "ZIP ready: $zip"
