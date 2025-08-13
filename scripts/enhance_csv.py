#!/usr/bin/env python3
import sys
import csv
import sqlite3
from pathlib import Path


def lookup_definition(conn, word):
    cur = conn.cursor()
    cur.execute("SELECT definition, pos FROM stardict WHERE word = ? COLLATE NOCASE LIMIT 1", (word,))
    row = cur.fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def main():
    if len(sys.argv) < 4:
        print("Usage: enhance_csv.py <stardict.db> <input.csv> <output.csv>")
        sys.exit(1)

    dict_path = Path(sys.argv[1])
    input_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    if not dict_path.exists():
        print("Dictionary DB not found:", dict_path)
        sys.exit(2)

    conn = sqlite3.connect(str(dict_path))

    with open(input_path, newline='', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        fieldnames = list(reader.fieldnames or [])
        if 'word' not in fieldnames:
            print("Input CSV must contain a 'word' column")
            sys.exit(3)

        # Ensure columns exist
        for col in ['meaning', 'part_of_speech']:
            if col not in fieldnames:
                fieldnames.append(col)

        rows = []
        for row in reader:
            word = (row.get('word') or '').strip()
            if word and not (row.get('meaning') or '').strip():
                definition, pos = lookup_definition(conn, word)
                if definition:
                    row['meaning'] = definition
                if pos:
                    row['part_of_speech'] = pos
            rows.append(row)

    with open(output_path, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    conn.close()


if __name__ == '__main__':
    main()