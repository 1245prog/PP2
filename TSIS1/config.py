from __future__ import annotations

import os

DB_CONFIG = {
    "dbname": os.getenv("PHONEBOOK_DB_NAME", "phonebook_db"),
    "user": os.getenv("PHONEBOOK_DB_USER", "postgres"),
    "password": os.getenv("PHONEBOOK_DB_PASSWORD", "1234"),
    "host": os.getenv("PHONEBOOK_DB_HOST", "localhost"),
    "port": int(os.getenv("PHONEBOOK_DB_PORT", "5432")),
}

DEFAULT_PAGE_SIZE = 5
DEFAULT_SORT = "name"
CSV_DEFAULT_PATH = r"C:\Study\PP2\TSIS\TSIS1\contacts.csv"
JSON_DEFAULT_EXPORT = r"C:\Study\PP2\TSIS\TSIS1\contacts_export.json"
JSON_DEFAULT_IMPORT = r"C:\Study\PP2\TSIS\TSIS1\contacts_import.json"
