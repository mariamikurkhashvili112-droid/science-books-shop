"""
წიგნების ჩამტვირთავი სკრიპტი.

გამოყენება (პროექტის ძირეული საქაღალდიდან, სადაც manage.py არის):
    python import_books.py books.txt
"""
import os
import re
import sys
from decimal import Decimal

# კატეგორია და ქვეკატეგორია თითოეული წიგნისთვის (სათაურის მიხედვით).
# კატეგორიები ზუსტად ისაა, როგორც books.txt-ის სათაურებში.
# ქვეკატეგორია PDF-ის მიხედვით აუცილებელია. სახელები admin-ში მერე ადვილად შეიცვლება.
TAXONOMY = {
    "Introduction to Quantum Mechanics": ("Quantum Physics", "Textbooks"),
    "Quantum Mechanics: The Theoretical Minimum": ("Quantum Physics", "Textbooks"),
    "QED: The Strange Theory of Light and Matter": ("Quantum Physics", "Popular Science"),
    "Something Deeply Hidden": ("Quantum Physics", "Popular Science"),
    "Biological Sequence Analysis": ("Bioinformatics", "Sequence Analysis & Algorithms"),
    "Bioinformatics Algorithms: An Active Learning Approach": ("Bioinformatics", "Sequence Analysis & Algorithms"),
    "Bioinformatics Data Skills": ("Bioinformatics", "Programming & Data Skills"),
    "Python for Bioinformatics": ("Bioinformatics", "Programming & Data Skills"),
    "The Emperor of All Maladies: A Biography of Cancer": ("Medicine", "Oncology"),
    "Gray's Anatomy for Students": ("Medicine", "Anatomy"),
    "Harrison's Principles of Internal Medicine": ("Medicine", "Internal Medicine"),
    "Molecular Biology of the Cell": ("Medicine", "Cell Biology"),
    "The Selfish Gene": ("Medicine", "Evolutionary Biology"),
    "Organic Chemistry": ("Chemistry", "Organic Chemistry"),
    "Atkins' Physical Chemistry": ("Chemistry", "Physical Chemistry"),
    "The Disappearing Spoon": ("Chemistry", "Popular Science"),
    "Introduction to Algorithms": ("Computer Science", "Algorithms"),
    "Clean Code": ("Computer Science", "Software Engineering"),
    "Python Crash Course": ("Computer Science", "Python Programming"),
    "Fluent Python": ("Computer Science", "Python Programming"),
}

# ჩანაწერები, რომლებსაც ვტოვებთ, სანამ მონაცემები გასწორდება
SKIP_TITLES = {
    "Organic Chemistry": "აღწერა და მონაცემები Introduction to Algorithms-ისაა, ჯერ გასასწორებელია",
}

DEFAULT_STOCK = 10

INTRO_RE = re.compile(r"^intro\s*:", re.IGNORECASE)

FIELD_RE = re.compile(
    r"^\s*(price|year|publisher|edition|dimensions?|print\s*length|page\s*length)\s*:\s*(.*)$",
    re.IGNORECASE,
)


def clean_text(text):
    # გატეხილი სიმბოლოები (youâ??ll -> you’ll)
    text = text.replace("â??", "’")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def next_nonempty(lines, i):
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return lines[j].strip() if j < len(lines) else ""


def split_authors(raw):
    raw = raw.strip().rstrip(".").strip()
    raw = re.sub(r"\s+et al$", "", raw)
    parts = re.split(r",\s*|\s+and\s+", raw)
    return [p.strip() for p in parts if p.strip()]


def make_short_description(description, limit=300):
    flat = re.sub(r"\s+", " ", description).strip()
    if len(flat) <= limit:
        return flat
    cut = flat[: limit - 1]
    dot = cut.rfind(". ")
    if dot > 120:
        return cut[: dot + 1]
    space = cut.rfind(" ")
    return cut[:space] + "…"


def parse_books(text):
    lines = text.splitlines()
    books = []
    current = None
    in_intro = False
    seen_field = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # ახალი წიგნის დასაწყისი: "N. სათაური by ავტორები." და შემდეგ ხაზზე Intro
        m = re.match(r"^\s*(?:\d+\s*\.\s*)?(.+)$", line)
        if (
            m
            and stripped
            and " by " in stripped
            and INTRO_RE.match(next_nonempty(lines, i))
            and not INTRO_RE.match(stripped)
        ):
            title, authors = m.group(1).strip().rsplit(" by ", 1)
            current = {
                "title": title.strip(),
                "authors": split_authors(authors),
                "intro_lines": [],
                "fields": {},
            }
            books.append(current)
            in_intro = False
            seen_field = False
            continue

        if current is None:
            continue

        if INTRO_RE.match(stripped) and not seen_field and not in_intro:
            in_intro = True
            current["intro_lines"].append(re.sub(r"^intro\s*:\s*", "", stripped, flags=re.I))
            continue

        field = FIELD_RE.match(line)
        if field:
            seen_field = True
            in_intro = False
            key = field.group(1).lower().replace(" ", "")
            if key.startswith("dimension"):
                key = "dimensions"
            elif key in ("printlength", "pagelength"):
                key = "pages"
            current["fields"][key] = field.group(2).strip()
            continue

        if in_intro and not seen_field:
            current["intro_lines"].append(line.rstrip())

    result = []
    for b in books:
        f = b["fields"]
        description = clean_text("\n".join(b["intro_lines"]))
        price_match = re.search(r"\d+(?:[.,]\d+)?", f.get("price", ""))
        year_match = re.search(r"\d{4}", f.get("year", ""))
        pages_match = re.search(r"\d+", f.get("pages", ""))
        result.append(
            {
                "title": b["title"],
                "authors": b["authors"],
                "description": description,
                "short_description": make_short_description(description),
                "price": Decimal(price_match.group().replace(",", ".")) if price_match else None,
                "year": int(year_match.group()) if year_match else None,
                "pages": int(pages_match.group()) if pages_match else None,
                "publisher": f.get("publisher", "").strip(),
                "edition": f.get("edition", "").replace(" ", ""),
                "dimensions": f.get("dimensions", "").strip(),
            }
        )
    return result


def main():
    if len(sys.argv) < 2:
        print("გამოყენება: python import_books.py books.txt")
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from shop.models import Author, Book, Category, Publisher, Subcategory

    with open(sys.argv[1], encoding="utf-8") as fh:
        parsed = parse_books(fh.read())

    created_count = 0
    updated_count = 0

    for item in parsed:
        title = item["title"]

        if title in SKIP_TITLES:
            print(f"გამოტოვებულია: {title} ({SKIP_TITLES[title]})")
            continue
        if title not in TAXONOMY:
            print(f"გამოტოვებულია: {title} (კატეგორია არ არის განსაზღვრული)")
            continue
        if item["price"] is None or item["year"] is None or not item["publisher"]:
            print(f"გამოტოვებულია: {title} (ფასი, წელი ან გამომცემლობა აკლია)")
            continue

        cat_name, sub_name = TAXONOMY[title]
        category, _ = Category.objects.get_or_create(name=cat_name)
        subcategory, _ = Subcategory.objects.get_or_create(category=category, name=sub_name)
        publisher, _ = Publisher.objects.get_or_create(name=item["publisher"])

        fields = {
            "short_description": item["short_description"],
            "description": item["description"],
            "subcategory": subcategory,
            "publisher": publisher,
            "price": item["price"],
            "language": Book.Language.ENGLISH,
            "year": item["year"],
            "pages": item["pages"],
            "edition": item["edition"],
            "dimensions": item["dimensions"],
        }

        book, created = Book.objects.get_or_create(
            title=title, defaults={**fields, "stock": DEFAULT_STOCK}
        )
        if created:
            created_count += 1
        else:
            for name, value in fields.items():
                setattr(book, name, value)
            book.save()
            updated_count += 1

        authors = [Author.objects.get_or_create(name=a)[0] for a in item["authors"]]
        book.authors.set(authors)

    print(f"დამატებულია: {created_count}, განახლებულია: {updated_count}")


if __name__ == "__main__":
    main()