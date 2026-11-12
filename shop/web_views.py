from datetime import date, timedelta
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FloatField,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .filters import BookFilter
from .models import (
    Author,
    Book,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Publisher,
    Review,
)

CART_SESSION_KEY = "cart_token"

# Delivery fee and estimated arrival
DELIVERY_FEE = {"tbilisi": Decimal("5.00"), "other": Decimal("10.00")}
# Days added to the book's earliest delivery date: (from, to)
DELIVERY_OFFSET = {"tbilisi": (0, 1), "other": (2, 4)}
DELIVERY_LABEL = {"tbilisi": "Tbilisi", "other": "Outside Tbilisi"}
# Used when a book has no delivery_start date set in the admin
DEFAULT_DELIVERY_START = date(2026, 11, 23)

SORTS = {
    "newest": ["-created_at", "-id"],
    "price_asc": ["sale_price", "title"],
    "price_desc": ["-sale_price", "title"],
    "rating": ["-avg_rating", "-reviews_total", "title"],
    "title": ["title"],
}

FILTER_KEYS = [
    "q",
    "category",
    "subcategory",
    "publisher",
    "author",
    "language",
    "min_price",
    "max_price",
    "min_rating",
    "sort",
]


# ---------- დამხმარე ფუნქციები ----------


def annotated_books():
    """წიგნები + ფასდაკლებული ფასი, საშუალო რეიტინგი და შეფასებების რაოდენობა"""
    return (
        Book.objects.select_related("subcategory__category", "publisher")
        .prefetch_related("authors", "reviews")
        .annotate(
            sale_price=ExpressionWrapper(
                F("price") * (100 - F("discount_percent")) * Value(Decimal("0.01")),
                output_field=DecimalField(max_digits=8, decimal_places=2),
            ),
            avg_rating=Coalesce(Avg("reviews__rating"), 0.0, output_field=FloatField()),
            reviews_total=Count("reviews", distinct=True),
        )
    )


def stars(rating):
    full = int((rating or 0) + 0.5)
    return "★" * full + "☆" * (5 - full)


def decorate(book):
    """შაბლონისთვის საჭირო მნიშვნელობები: ვარსკვლავები, რეიტინგი, ფასი"""
    rating = getattr(book, "avg_rating", None)
    if rating is None:
        rating = book.average_rating
    total = getattr(book, "reviews_total", None)
    if total is None:
        total = book.reviews_count
    price = getattr(book, "sale_price", None)
    if price is None:
        price = book.final_price
    book.rating_value = round(float(rating or 0), 1)
    book.review_total = total
    book.stars = stars(rating)
    book.price_now = price
    return book


def get_cart(request, create=False):
    """კალათა ინახება სესიაში (თემა 17): სესიაში ვინახავთ კალათის ტოკენს"""
    token = request.session.get(CART_SESSION_KEY)
    cart = Cart.objects.filter(token=token).first() if token else None
    if cart is None and create:
        cart = Cart.objects.create()
        request.session[CART_SESSION_KEY] = str(cart.token)
    return cart


def cart_count(request):
    cart = get_cart(request)
    if cart is None:
        return 0
    return cart.items.aggregate(total=Sum("quantity"))["total"] or 0


def render_page(request, template, context):
    context["cart_count"] = cart_count(request)
    return render(request, template, context)


def safe_next(request):
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return reverse("home")


def delivery_start(book):
    """Earliest delivery date of a book (never earlier than today)"""
    start = book.delivery_start or DEFAULT_DELIVERY_START
    return max(start, timezone.localdate())


def delivery_range(start, zone):
    low, high = DELIVERY_OFFSET[zone]
    return start + timedelta(days=low), start + timedelta(days=high)


# ---------- მთავარი გვერდი ----------


def home(request):
    books = BookFilter(request.GET, queryset=annotated_books()).qs

    query = request.GET.get("q", "").strip()
    if query:
        books = books.filter(title__icontains=query)

    sort = request.GET.get("sort", "newest")
    books = books.order_by(*SORTS.get(sort, SORTS["newest"]))

    paginator = Paginator(books, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    for book in page_obj:
        decorate(book)

    params = request.GET.copy()
    params.pop("page", None)

    filters = {key: request.GET.get(key, "") for key in FILTER_KEYS}
    active_author = None
    if filters["author"].isdigit():
        active_author = Author.objects.filter(pk=filters["author"]).first()

    languages = list(Book.Language.choices)

    return render_page(
        request,
        "shop/home.html",
        {
            "page_obj": page_obj,
            "paginator": paginator,
            "qs_string": params.urlencode(),
            "categories": Category.objects.prefetch_related("subcategories"),
            "publishers": Publisher.objects.all(),
            "languages": languages,
            "filters": filters,
            "active_author": active_author,
        },
    )


# ---------- ნივთის დეტალური გვერდი ----------


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["first_name", "last_name", "rating", "text"]


def book_detail(request, pk):
    book = decorate(get_object_or_404(annotated_books(), pk=pk))

    reviews = list(book.reviews.all())
    for review in reviews:
        review.stars = stars(review.rating)

    authors = list(book.authors.all())
    others = annotated_books().exclude(pk=book.pk)

    # მსგავსი წიგნები: ჯერ იგივე ქვეკატეგორია, მერე იგივე კატეგორია
    similar = list(
        others.filter(subcategory=book.subcategory).order_by("-avg_rating", "title")[:4]
    )
    if len(similar) < 4:
        taken = [b.pk for b in similar]
        similar += list(
            others.filter(subcategory__category=book.subcategory.category)
            .exclude(pk__in=taken)
            .order_by("-avg_rating", "title")[: 4 - len(similar)]
        )
    author_books = list(others.filter(authors__in=authors).order_by("-year")[:4])
    for item in similar + author_books:
        decorate(item)

    delivery = []
    if book.stock > 0:
        start = delivery_start(book)
        for zone in ("tbilisi", "other"):
            date_from, date_to = delivery_range(start, zone)
            delivery.append(
                {
                    "label": DELIVERY_LABEL[zone],
                    "fee": DELIVERY_FEE[zone],
                    "date_from": date_from,
                    "date_to": date_to,
                }
            )

    return render_page(
        request,
        "shop/book_detail.html",
        {
            "book": book,
            "authors": authors,
            "reviews": reviews,
            "similar": similar,
            "author_books": author_books,
            "delivery": delivery,
            "active_tab": "reviews" if request.GET.get("tab") == "reviews" else "details",
        },
    )


@require_POST
def add_review(request, pk):
    book = get_object_or_404(Book, pk=pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.book = book
        review.save()
        messages.success(request, "Thank you, your review has been added")
    else:
        messages.error(
            request,
            "Could not add the review: please enter your first and last name and choose 1 to 5 stars",
        )
    return redirect(f"{reverse('book_detail', args=[pk])}?tab=reviews")


# ---------- კალათა ----------


@require_POST
def cart_add(request, pk):
    book = get_object_or_404(Book, pk=pk)
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        quantity = 1

    if book.stock <= 0:
        messages.error(request, f"“{book.title}” is currently out of stock")
        return redirect(safe_next(request))

    cart = get_cart(request, create=True)
    item, created = CartItem.objects.get_or_create(
        cart=cart, book=book, defaults={"quantity": quantity}
    )
    if not created:
        item.quantity += quantity
        item.save()
    messages.success(request, f"“{book.title}” was added to your cart")
    return redirect(safe_next(request))


def cart_view(request):
    cart = get_cart(request)
    items = []
    total = Decimal("0.00")
    if cart is not None:
        items = list(
            cart.items.select_related("book__subcategory__category", "book__publisher")
        )
        for item in items:
            decorate(item.book)
        total = cart.total_price

    zone = request.GET.get("zone", "tbilisi")
    if zone not in DELIVERY_FEE:
        zone = "tbilisi"
    fee = DELIVERY_FEE[zone] if items else Decimal("0.00")
    stock_problem = bool(stock_problems(items))

    date_from = date_to = None
    if items:
        # the order arrives when the latest book is available
        start = max(delivery_start(item.book) for item in items)
        date_from, date_to = delivery_range(start, zone)

    return render_page(
        request,
        "shop/cart.html",
        {
            "items": items,
            "total": total,
            "fee": fee,
            "grand_total": total + fee,
            "zone": zone,
            "delivery_fees": DELIVERY_FEE,
            "stock_problem": stock_problem,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@require_POST
def cart_update(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart=get_cart(request))
    operation = request.POST.get("op")
    if operation == "inc":
        item.quantity += 1
        item.save()
    elif operation == "dec" and item.quantity > 1:
        item.quantity -= 1
        item.save()
    return redirect(f"{reverse('cart')}?zone={request.POST.get('zone', 'tbilisi')}")


@require_POST
def cart_delete(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart=get_cart(request))
    item.delete()
    return redirect(f"{reverse('cart')}?zone={request.POST.get('zone', 'tbilisi')}")


# ---------- შეკვეთის გაფორმება (checkout) ----------


class StockError(Exception):
    pass


def stock_problems(items):
    """ტექსტები იმ წიგნებზე, რომელთა მარაგი კალათაში არსებულ რაოდენობაზე ნაკლებია"""
    problems = []
    for item in items:
        stock = item.book.stock
        if item.quantity <= stock:
            continue
        if stock <= 0:
            problems.append(f"“{item.book.title}” is out of stock. Please remove it from your cart.")
        else:
            problems.append(
                f"Only {stock} cop{'y' if stock == 1 else 'ies'} of “{item.book.title}” left. "
                "Please reduce the quantity."
            )
    return problems


class CheckoutForm(forms.ModelForm):
    phone = forms.RegexField(
        regex=r"^\+?[0-9 ()-]{9,20}$",
        max_length=30,
        error_messages={"invalid": "Enter a valid phone number, e.g. +995 555 123 456"},
    )

    class Meta:
        model = Order
        fields = ["first_name", "last_name", "phone", "delivery_zone", "address", "note"]
        widgets = {
            "delivery_zone": forms.RadioSelect(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "delivery_zone":
                field.widget.attrs["class"] = "form-control"
        self.fields["phone"].widget.attrs["placeholder"] = "+995 555 123 456"
        self.fields["delivery_zone"].choices = Order.Zone.choices  # ცარიელი "-----" ვარიანტის გარეშე


def place_order(form, cart, items):
    """ქმნის შეკვეთას, ამცირებს მარაგს და ასუფთავებს კალათას (ერთ ტრანზაქციაში)"""
    with transaction.atomic():
        order = form.save(commit=False)
        items_total = sum((item.subtotal for item in items), Decimal("0.00"))
        fee = DELIVERY_FEE[order.delivery_zone]
        start = max(delivery_start(item.book) for item in items)
        order.delivery_from, order.delivery_to = delivery_range(start, order.delivery_zone)
        order.items_total = items_total
        order.delivery_fee = fee
        order.total = items_total + fee
        order.save()

        for item in items:
            updated = Book.objects.filter(pk=item.book_id, stock__gte=item.quantity).update(
                stock=F("stock") - item.quantity
            )
            if not updated:
                raise StockError(item.book.title)
            OrderItem.objects.create(
                order=order,
                book=item.book,
                title=item.book.title,
                unit_price=item.book.final_price,
                quantity=item.quantity,
            )
        cart.delete()
    return order


def checkout(request):
    cart = get_cart(request)
    items = list(cart.items.select_related("book")) if cart else []
    if not items:
        messages.info(request, "Your cart is empty")
        return redirect("cart")

    problems = stock_problems(items)
    if problems:
        for problem in problems:
            messages.error(request, problem)
        return redirect("cart")

    items_total = sum((item.subtotal for item in items), Decimal("0.00"))

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(form, cart, items)
            except StockError as error:
                messages.error(request, f"Sorry, “{error}” just went out of stock. Please check your cart.")
                return redirect("cart")
            request.session.pop(CART_SESSION_KEY, None)
            request.session["last_order_id"] = order.pk
            return redirect("order_done", pk=order.pk)
    else:
        zone = request.GET.get("zone", "tbilisi")
        if zone not in DELIVERY_FEE:
            zone = "tbilisi"
        form = CheckoutForm(initial={"delivery_zone": zone})

    return render_page(
        request,
        "shop/checkout.html",
        {
            "form": form,
            "items": items,
            "items_total": items_total,
            "fees": DELIVERY_FEE,
        },
    )


def order_done(request, pk):
    # შეკვეთის გვერდი მხოლოდ იმ ბრაუზერს ჩანს, რომელმაც ის გააფორმა
    if request.session.get("last_order_id") != pk:
        raise Http404
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    return render_page(request, "shop/order_done.html", {"order": order})