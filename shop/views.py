from decimal import Decimal

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FloatField,
    Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import BookFilter
from .models import Author, Book, Cart, CartItem, Category, Publisher
from .serializers import (
    AuthorSerializer,
    BookDetailSerializer,
    BookListSerializer,
    CartItemInputSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    CategorySerializer,
    PublisherSerializer,
    ReviewSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.prefetch_related("subcategories")
    serializer_class = CategorySerializer


class PublisherViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/books/                 - სია + ფილტრები + ძებნა
    GET /api/books/<id>/            - დეტალური გვერდი
    GET/POST /api/books/<id>/reviews/ - შეფასებები
    """

    filterset_class = BookFilter
    search_fields = ["title"]
    ordering_fields = ["sale_price", "avg_rating", "year", "created_at", "title"]

    def get_queryset(self):
        return (
            Book.objects.select_related("subcategory__category", "publisher")
            .prefetch_related("authors", "reviews")
            .annotate(
                # ფასი ფასდაკლების შემდეგ (ბაზის დონეზე, რომ შეიძლებოდეს ფილტრი და დალაგება)
                sale_price=ExpressionWrapper(
                    F("price")
                    * (100 - F("discount_percent"))
                    * Value(Decimal("0.01")),
                    output_field=DecimalField(max_digits=8, decimal_places=2),
                ),
                avg_rating=Coalesce(
                    Avg("reviews__rating"), 0.0, output_field=FloatField()
                ),
                reviews_total=Count("reviews", distinct=True),
            )
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BookDetailSerializer
        return BookListSerializer

    @action(detail=True, methods=["get", "post"])
    def reviews(self, request, pk=None):
        book = self.get_object()
        if request.method == "GET":
            serializer = ReviewSerializer(book.reviews.all(), many=True)
            return Response(serializer.data)

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(book=book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------- კალათა (ლოგინის გარეშე, ტოკენით) ----------


def cart_response(request, cart, status_code=status.HTTP_200_OK):
    return Response(CartSerializer(cart, context={"request": request}).data, status=status_code)


class CartCreateView(APIView):
    """POST /api/carts/ - ქმნის ახალ კალათას და აბრუნებს token-ს"""

    def post(self, request):
        cart = Cart.objects.create()
        return cart_response(request, cart, status.HTTP_201_CREATED)


class CartDetailView(APIView):
    """GET /api/carts/<token>/ - კალათის შიგთავსი და ჯამური ფასი"""

    def get(self, request, token):
        cart = get_object_or_404(Cart, token=token)
        return cart_response(request, cart)


class CartItemsView(APIView):
    """POST /api/carts/<token>/items/ - წიგნის დამატება კალათაში"""

    def post(self, request, token):
        cart = get_object_or_404(Cart, token=token)
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data["book"]
        quantity = serializer.validated_data["quantity"]

        item, created = CartItem.objects.get_or_create(
            cart=cart, book=book, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return cart_response(request, cart, code)


class CartItemDetailView(APIView):
    """PATCH /api/carts/<token>/items/<id>/ - რაოდენობის შეცვლა; DELETE - წაშლა"""

    def get_item(self, token, item_id):
        return get_object_or_404(CartItem, pk=item_id, cart__token=token)

    def patch(self, request, token, item_id):
        item = self.get_item(token, item_id)
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data["quantity"]
        item.save()
        return cart_response(request, item.cart)

    def delete(self, request, token, item_id):
        item = self.get_item(token, item_id)
        cart = item.cart
        item.delete()
        return cart_response(request, cart)