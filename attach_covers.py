"""
ყდების მიმაგრება წიგნებზე.

1) python attach_covers.py --list    - აჩვენებს წიგნებს და მათ ნომრებს
2) სურათები ჩააგდე საქაღალდეში covers_src, სახელად წიგნის ნომრით: 1.jpg, 2.png, 3.webp ...
3) python attach_covers.py           - მიამაგრებს სურათებს წიგნებზე
   python attach_covers.py --force   - უკვე მიმაგრებულ ყდებსაც ჩაანაცვლებს
"""
import os
import sys
from pathlib import Path

ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.core.files import File

    from shop.models import Book

    args = sys.argv[1:]

    if "--list" in args:
        for book in Book.objects.order_by("id"):
            mark = "   [ყდა უკვე აქვს]" if book.cover else ""
            print(f"{book.id:>3} – {book.title}{mark}")
        return

    force = "--force" in args
    source = Path("covers_src")
    if not source.is_dir():
        print("საქაღალდე covers_src ვერ ვიპოვე. შექმენი ის manage.py-ის გვერდით.")
        sys.exit(1)

    books = {book.id: book for book in Book.objects.all()}
    attached = 0

    for path in sorted(source.iterdir()):
        if path.suffix.lower() not in ALLOWED:
            continue
        if not path.stem.isdigit():
            print(f"გამოტოვებულია {path.name}: ფაილის სახელი უნდა იყოს წიგნის ნომერი (მაგ. 5.jpg)")
            continue
        book = books.get(int(path.stem))
        if book is None:
            print(f"გამოტოვებულია {path.name}: ასეთი ნომრის წიგნი არ არსებობს")
            continue
        if book.cover and not force:
            print(f"გამოტოვებულია {path.name}: {book.title}-ს უკვე აქვს ყდა (ჩასანაცვლებლად --force)")
            continue
        if book.cover:
            book.cover.delete(save=False)
        with path.open("rb") as fh:
            book.cover.save(f"book_{book.id}{path.suffix.lower()}", File(fh), save=True)
        attached += 1
        print(f"მიმაგრებულია: {book.title}")

    print(f"სულ მიმაგრებულია: {attached}")


if __name__ == "__main__":
    main()