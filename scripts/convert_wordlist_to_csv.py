#!/usr/bin/env python3
import sys
import csv


def main():
    if len(sys.argv) < 3:
        print("Usage: convert_wordlist_to_csv.py <input.txt> <output.csv>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow(["word"]) 
        for line in fin:
            word = line.strip()
            if word:
                writer.writerow([word])


if __name__ == "__main__":
    main()