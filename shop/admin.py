from django.contrib import admin

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
    Subcategory,
)

admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Publisher)
admin.site.register(Author)
admin.site.register(Cart)
admin.site.register(CartItem)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subcategory",
        "publisher",
        "price",
        "discount_percent",
        "language",
        "year",
        "stock",
        "delivery_start",
    )
    # ფასი, ფასდაკლება, მარაგი და მიწოდების თარიღი სიაშივე რედაქტირდება
    list_editable = ("price", "discount_percent", "stock", "delivery_start")
    list_per_page = 50
    list_filter = ("subcategory__category", "publisher", "language")
    search_fields = ("title", "isbn", "authors__name")
    filter_horizontal = ("authors",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "first_name", "last_name", "rating", "created_at")
    list_filter = ("rating",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("book", "title", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "phone",
        "delivery_zone",
        "total",
        "status",
        "created_at",
    )
    list_editable = ("status",)
    list_filter = ("status", "delivery_zone")
    search_fields = ("first_name", "last_name", "phone")
    readonly_fields = (
        "items_total",
        "delivery_fee",
        "total",
        "delivery_from",
        "delivery_to",
        "created_at",
    )
    inlines = [OrderItemInline]