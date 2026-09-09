"""Inspect relocated indexes; --apply backs up all local data before repair."""

from datetime import datetime
from pathlib import Path
import shutil
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bids.services.document_paths import portable_document_source, resolve_document_source


def integrity(connection):
    return [row[0] for row in connection.execute("PRAGMA integrity_check")]


class Command(BaseCommand):
    help = "Inspect Chroma integrity and document paths; stop Django before --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        server = Path(settings.BASE_DIR).resolve()
        root = server / "chroma_db"
        paths = sorted(root.glob("*/chroma.sqlite3"))
        plans = []
        for path in paths:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
                checks = integrity(connection)
                sources = [row[0] for row in connection.execute(
                    "SELECT DISTINCT string_value FROM embedding_metadata WHERE key='source'"
                )]
                missing = [s for s in sources if not resolve_document_source(s).is_file()]
                changes = sum(portable_document_source(s) != s for s in sources)
                self.stdout.write(f"{path.parent.name}: integrity={checks}; sources={len(sources)}; changes={changes}; missing={len(missing)}")
                if missing:
                    raise CommandError("Referenced documents are missing; no repairs were applied.")
                plans.append((path, checks, changes))
        if not options["apply"]:
            self.stdout.write("Inspection only. Stop Django, then run with --apply to back up and repair.")
            return
        if not any(checks != ["ok"] or changes for _, checks, changes in plans):
            self.stdout.write("All indexes are healthy and portable. No changes needed.")
            return
        backup = server.parent / ".backups" / datetime.now().strftime("repair-%Y%m%d-%H%M%S-%f")
        backup.mkdir(parents=True, exist_ok=False)
        # Preserve the vector files, cached generations and user uploads together.
        for name in ("chroma_db", "media"):
            source = server / name
            if source.exists():
                shutil.copytree(source, backup / name)
        database = server / "db.sqlite3"
        if database.exists():
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as source:
                with sqlite3.connect(backup / "db.sqlite3") as destination:
                    source.backup(destination)
        self.stdout.write(f"Backup: {backup}")
        # Check a rebuilt copy before touching each original SQLite file.
        for path, checks, _ in plans:
            if checks == ["ok"]:
                continue
            trial = backup / f"{path.parent.name}-repair-trial.sqlite3"
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
                with sqlite3.connect(trial) as destination:
                    source.backup(destination)
                    destination.execute("INSERT INTO embedding_fulltext_search(embedding_fulltext_search) VALUES('rebuild')")
                    destination.commit()
                    if integrity(destination) != ["ok"]:
                        raise CommandError(f"Repair trial failed; original unchanged: {path.parent.name}")
            with sqlite3.connect(path) as connection:
                connection.execute("INSERT INTO embedding_fulltext_search(embedding_fulltext_search) VALUES('rebuild')")
                connection.commit()
                if integrity(connection) != ["ok"]:
                    raise CommandError(f"Repair failed. Backup is at {backup}")
        import chromadb
        from chromadb.config import Settings

        for path, _, changes in plans:
            if not changes:
                continue
            client = chromadb.PersistentClient(str(path.parent), settings=Settings(anonymized_telemetry=False))
            count = 0
            for collection in client.list_collections():
                before = collection.count()
                for offset in range(0, before, 200):
                    records = collection.get(limit=200, offset=offset, include=["metadatas"])
                    ids, metadatas = [], []
                    for item_id, metadata in zip(records["ids"], records["metadatas"]):
                        if metadata and metadata.get("source"):
                            replacement = portable_document_source(metadata["source"])
                            if replacement != metadata["source"]:
                                ids.append(item_id)
                                metadatas.append({**metadata, "source": replacement})
                    if ids:
                        collection.update(ids=ids, metadatas=metadatas)
                        count += len(ids)
                if collection.count() != before:
                    raise CommandError("Document count changed unexpectedly; consult the backup.")
            with sqlite3.connect(path) as connection:
                if integrity(connection) != ["ok"]:
                    raise CommandError(f"Post-repair integrity failure: {path.parent.name}")
            self.stdout.write(f"{path.parent.name}: updated {count} source references; integrity=ok")
        self.stdout.write(self.style.SUCCESS("Repair completed. Embeddings were preserved; no AI API was called."))
