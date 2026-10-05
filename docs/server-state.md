# Versioned server state (0.10 development)

The supported web profile remains one process, one local SQLite database, and
one notebook. Starting the application now runs ordered schema migrations before
accepting requests. It no longer generates the current ORM schema on every
start. Migration version 1 establishes the supported account and contact inbox
tables and records the baseline in `pnbp_schema_migrations`.

Existing 0.9 tables are retained. Account IDs, password hashes, token revocation
state, inbox payloads/timestamps, and SQLite sequence counters are preserved.
Missing supported tables are created; incompatible legacy columns stop startup
instead of rebuilding accounts. Unknown future versions or inconsistent history
also stop startup. Use a matching application version and verified backup.

Before upgrading an existing database, the application uses SQLite's backup API
to write a consistent private snapshot, including committed WAL data, under
`DATABASE_DIRECTORY/migration-backups/`. Each migration record includes its name,
UTC time, backup path, and SHA-256 receipt. The database backup uses owner-only
file permissions. Fresh empty databases and in-memory tests need no backup;
starting an already-current database creates no additional migration backup.

Migrations use one SQL transaction. A schema failure rolls back its changes and
leaves the backup available. A backup failure stops before schema changes. Keep
backup receipts and previous application versions locally; these files contain
account/token data and belong in private, encrypted backup storage.

## Recovery

Take a complete stopped-site backup before deploying an upgrade, following the
[supported backup instructions](web.md#backup-restore-and-recovery). Automatic migration
snapshots cover the database; they do not replace a complete backup of images,
settings, and page content.

If startup fails, stop the process and retain the current database, its SQLite
sidecars, and the recorded backup before changing files. A rolled-back migration
can be retried after repairing storage or configuration. Do not remove migration
history or regenerate account tables to get past an error.

To restore a pre-upgrade version, stop the application, preserve the failed state
separately, and restore one complete version-matched stopped-site backup into a
new private data directory. Configure that directory and run the corresponding
application version. Check `/healthz`, owner authentication, token state, inbox
messages, and public pages before returning the site to service. Never combine
unrelated databases, pages, or sidecars from different backups.

This baseline prepares the publication catalog migration. Existing flat pages
and upload behavior remain in place until that migration is implemented.
