"""Script pour réindexer sigma_spec avec le nouveau chunker."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    print("=== Réindexation de sigma_spec ===\n")

    # Importer les composants
    from src.core.pipeline.indexer import UnifiedIndexer, IndexRoute
    from src.infrastructure.database import DatabaseService
    from src.config.settings import Config

    # Initialiser la base de données
    config = Config()
    db = DatabaseService(config.paths_duckdb_path)
    db.initialize()

    # Créer l'indexer
    indexer = UnifiedIndexer(db=db)

    # Définir la route pour sigma_spec
    route = IndexRoute("sigma_spec", "sigma_spec")

    # Vérifier les entrées pending
    pending = db.get_pending_sigma_spec()
    print(f"Entrées pending: {len(pending)}")

    if not pending:
        # Marquer toutes les entrées comme discovery
        print("Aucune entrée pending. Marquage de toutes les entrées comme 'discovery'...")
        db._writer_conn.execute("UPDATE sigma_spec SET embed_status = 'discovery'")
        db._writer_conn.commit()
        pending = db.get_pending_sigma_spec()
        print(f"Nouvelles entrées pending: {len(pending)}")

    if not pending:
        print("Aucune entrée à indexer!")
        return

    # Exécuter l'indexation
    print(f"\nIndexation de {len(pending)} entrées...")
    result = await indexer.index(route)

    print("\n=== Résultat ===")
    print(f"Traitée: {result.processed}")
    if result.errors:
        print(f"Erreurs: {len(result.errors)}")
        for err in result.errors[:5]:
            print(f"  - {err}")


if __name__ == "__main__":
    asyncio.run(main())
