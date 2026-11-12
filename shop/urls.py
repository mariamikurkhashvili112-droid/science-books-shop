from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthorViewSet,
    BookViewSet,
    CartCreateView,
    CartDetailView,
    CartItemDetailView,
    CartItemsView,
    CategoryViewSet,
    PublisherViewSet,
)

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("categories", CategoryViewSet, basename="category")
router.register("publishers", PublisherViewSet, basename="publisher")
router.register("authors", AuthorViewSet, basename="author")

urlpatterns = router.urls + [
    path("carts/", CartCreateView.as_view()),
    path("carts/<uuid:token>/", CartDetailView.as_view()),
    path("carts/<uuid:token>/items/", CartItemsView.as_view()),
    path("carts/<uuid:token>/items/<int:item_id>/", CartItemDetailView.as_view()),
]