from rest_framework import serializers

from .models import (
    Author,
    Book,
    Cart,
    CartItem,
    Category,
    Publisher,
    Review,
    Subcategory,
)


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = ["id", "name", "category"]


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "subcategories"]


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ["id", "name"]


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name"]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "first_name", "last_name", "rating", "text", "created_at"]
        read_only_fields = ["id", "created_at"]


class BookListSerializer(serializers.ModelSerializer):
    """ბარათისთვის საჭირო ველები (მთავარი გვერდი და კალათა)"""

    price = serializers.FloatField(read_only=True)
    final_price = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    authors = AuthorSerializer(many=True, read_only=True)
    category = serializers.CharField(source="subcategory.category.name", read_only=True)
    category_id = serializers.IntegerField(source="subcategory.category_id", read_only=True)
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)
    publisher_name = serializers.CharField(source="publisher.name", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "cover",
            "short_description",
            "authors",
            "category_id",
            "category",
            "subcategory",
            "subcategory_name",
            "publisher",
            "publisher_name",
            "language",
            "year",
            "price",
            "discount_percent",
            "final_price",
            "rating",
            "reviews_count",
            "stock",
        ]

    # ანოტირებული მნიშვნელობები (sale_price, avg_rating, reviews_total) სიაში მოდის;
    # თუ არ არის (მაგ. კალათაში), ვიყენებთ მოდელის თვისებებს.
    def get_final_price(self, obj):
        value = getattr(obj, "sale_price", None)
        if value is None:
            value = obj.final_price
        return float(round(value, 2))

    def get_rating(self, obj):
        value = getattr(obj, "avg_rating", None)
        if value is None:
            value = obj.average_rating
        return round(float(value or 0), 1)

    def get_reviews_count(self, obj):
        value = getattr(obj, "reviews_total", None)
        if value is None:
            value = obj.reviews_count
        return value


class BookDetailSerializer(BookListSerializer):
    """დეტალური გვერდი: Details და Review ჩანართები"""

    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + [
            "description",
            "isbn",
            "pages",
            "edition",
            "dimensions",
            "reviews",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "book", "quantity", "subtotal"]

    def get_subtotal(self, obj):
        return float(round(obj.subtotal, 2))


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["token", "items", "items_count", "total_price"]

    def get_total_price(self, obj):
        return float(round(obj.total_price, 2))

    def get_items_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class CartItemInputSerializer(serializers.Serializer):
    """კალათაში დამატება: {"book_id": 3, "quantity": 2}"""

    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source="book"
    )
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartItemUpdateSerializer(serializers.Serializer):
    """რაოდენობის შეცვლა: {"quantity": 3}"""

    quantity = serializers.IntegerField(min_value=1)