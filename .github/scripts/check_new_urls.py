import csv
import os

pending_urls = 0
csv_file = "article_links.csv"

if os.path.exists(csv_file):
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            next(reader)  # Skip header
            for row in reader:
                if len(row) < 2 or not row[1]:
                    pending_urls += 1
        except StopIteration:
            pass  # Handle empty file

if pending_urls > 0:
    print(f"{pending_urls} new URLs to process.")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write("has_new_urls=true\n")
else:
    print("No new URLs to process.")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write("has_new_urls=false\n")