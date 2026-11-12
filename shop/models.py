import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    """კატეგორია (მაგ. Quantum Physics, Bioinformatics, Medicine...)"""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    """ქვეკატეგორია (მაგ. Medicine -> Anatomy)"""

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="subcategories"
    )
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "subcategories"
        ordering = ["category__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"], name="unique_subcategory_per_category"
            )
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Publisher(models.Model):
    """გამომცემლობა (PDF-ში ამას 'ბრენდი' ჰქვია)"""

    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    class Language(models.TextChoices):
        GEORGIAN = "ka", "Georgian"
        ENGLISH = "en", "English"
        FRENCH = "fr", "French"

    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)
    short_description = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    authors = models.ManyToManyField(Author, related_name="books")
    subcategory = models.ForeignKey(
        Subcategory, on_delete=models.PROTECT, related_name="books"
    )
    publisher = models.ForeignKey(
        Publisher, on_delete=models.PROTECT, related_name="books"
    )

    price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100)]
    )

    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.GEORGIAN
    )
    year = models.PositiveSmallIntegerField()
    pages = models.PositiveIntegerField(blank=True, null=True)
    edition = models.CharField(max_length=30, blank=True)
    dimensions = models.CharField(max_length=50, blank=True)
    stock = models.PositiveIntegerField(default=0)
    delivery_start = models.DateField(
        blank=True,
        null=True,
        help_text="Earliest estimated delivery date in Tbilisi",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def final_price(self):
        """ფასი ფასდაკლების შემდეგ"""
        discount = Decimal(self.discount_percent) / Decimal(100)
        return (self.price * (Decimal(1) - discount)).quantize(Decimal("0.01"))

    @property
    def average_rating(self):
        result = self.reviews.aggregate(avg=models.Avg("rating"))["avg"]
        return round(result, 1) if result else 0

    @property
    def reviews_count(self):
        return self.reviews.count()


class Review(models.Model):
    """შეფასება: PDF-ის მიხედვით შემფასებლის სახელი, გვარი, ტექსტი და ვარსკვლავები"""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.book.title} ({self.rating})"


class Cart(models.Model):
    """კალათა. ლოგინი არ გვაქვს, ამიტომ კალათას ერთგვაროვანი ტოკენი (UUID) ცნობს."""

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.token}"

    @property
    def total_price(self):
        total = Decimal("0.00")
        for item in self.items.select_related("book"):
            total += item.subtotal
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "book"], name="unique_book_per_cart"
            )
        ]

    def __str__(self):
        return f"{self.book.title} x {self.quantity}"

    @property
    def subtotal(self):
        return self.book.final_price * self.quantity


class Order(models.Model):
    """შეკვეთა: მომხმარებლის მონაცემები და ფასების "სურათი" შეკვეთის მომენტში"""

    class Zone(models.TextChoices):
        TBILISI = "tbilisi", "Tbilisi"
        OTHER = "other", "Outside Tbilisi"

    class Status(models.TextChoices):
        NEW = "new", "New"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    note = models.CharField(max_length=255, blank=True)

    delivery_zone = models.CharField(max_length=10, choices=Zone.choices)
    items_total = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    delivery_from = models.DateField(blank=True, null=True)
    delivery_to = models.DateField(blank=True, null=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.first_name} {self.last_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # წიგნი რომ წაიშალოს, შეკვეთის ისტორია მაინც დარჩება (title და unit_price ინახება)
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.title} x {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity