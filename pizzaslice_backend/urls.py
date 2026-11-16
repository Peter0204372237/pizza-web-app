from django.contrib import admin
from django.urls import path, re_path

from ordering import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/deals/", views.deal_list, name="deal-list"),
    path("api/orders/quote/", views.quote_order, name="quote-order"),
    path("api/pizzas/", views.pizza_list, name="pizza-list"),
    path("api/pizzas/<slug:slug>/", views.pizza_detail, name="pizza-detail"),
    path("api/orders/", views.create_order, name="create-order"),
    path("api/orders/lookup/", views.track_order, name="track-order"),
    re_path(
        r"^(?P<asset_path>.+\.(?:css|js|jpg|jpeg|png|webp|svg|ico|woff2?))$",
        views.frontend_asset,
        name="frontend-asset",
    ),
    path("", views.frontend_home, name="frontend-home"),
    path("<str:page_name>", views.frontend_page, name="frontend-page"),
]
