"""
წიგნებზე მიწოდების დაწყების თარიღების გადანაწილება (20, 22 და 23 ნოემბერი).

გაშვება (manage.py-ის გვერდიდან):
    python set_delivery_dates.py          - მხოლოდ იმ წიგნებზე, რომლებსაც თარიღი ჯერ არ აქვთ
    python set_delivery_dates.py --force  - ყველა წიგნზე თავიდან
"""
import os
import sys
from datetime import date

DATES = [date(2026, 11, 20), date(2026, 11, 22), date(2026, 11, 23)]


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from shop.models import Book

    force = "--force" in sys.argv[1:]
    updated = 0
    for index, book in enumerate(Book.objects.order_by("id")):
        if book.delivery_start and not force:
            continue
        book.delivery_start = DATES[index % len(DATES)]
        book.save(update_fields=["delivery_start"])
        updated += 1
        print(f"{book.delivery_start}  {book.title}")
    print(f"განახლებულია: {updated}")


if __name__ == "__main__":
    main()