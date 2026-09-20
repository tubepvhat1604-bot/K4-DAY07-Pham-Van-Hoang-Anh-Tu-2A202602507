import csv
import re
from pathlib import Path

D = Path("data/ecommerce")
REQ = ["doc_id", "title", "source_url", "retrieved_at", "document_version", "audience"]

mds = sorted(D.glob("*.md"))
rows = list(csv.DictReader(open(D / "sources.csv", encoding="utf-8")))

ids = []
auds = {}

for p in mds:
    frontmatter_block = p.read_text(encoding="utf-8").split("---")[1]
    fm = dict(re.findall(r"^(\w+):\s*(.+)$", frontmatter_block, re.M))

    ids.append(fm.get("doc_id"))
    auds[fm.get("audience")] = auds.get(fm.get("audience"), 0) + 1

    has_all_fields = all(k in fm for k in REQ)
    doc_id_matches_filename = fm.get("doc_id") == p.stem
    status = "OK" if (has_all_fields and doc_id_matches_filename) else "THIEU METADATA"
    print(f"{p.name:40} {status}")

print("so file :", len(mds), "(can 5-10)")

csv_ids = sorted(r["doc_id"] for r in rows)
md_ids = sorted(ids)
print("csv     :", "khop" if csv_ids == md_ids else "LECH")

print("audience:", auds)
