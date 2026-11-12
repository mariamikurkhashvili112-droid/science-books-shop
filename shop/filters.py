from django_filters import rest_framework as filters

from .models import Book


class BookFilter(filters.FilterSet):
    """ფილტრები PDF-ის მიხედვით: კატეგორია, ქვეკატეგორია, ბრენდი (გამომცემლობა), ფასი, რეიტინგი"""

    category = filters.NumberFilter(field_name="subcategory__category_id")
    subcategory = filters.NumberFilter(field_name="subcategory_id")
    publisher = filters.NumberFilter(field_name="publisher_id")
    author = filters.NumberFilter(field_name="authors__id")
    language = filters.CharFilter(field_name="language")
    min_price = filters.NumberFilter(field_name="sale_price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="sale_price", lookup_expr="lte")
    min_rating = filters.NumberFilter(field_name="avg_rating", lookup_expr="gte")

    class Meta:
        model = Book
        fields = []