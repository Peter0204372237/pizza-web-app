from django import forms
from django.contrib import admin

from .models import Category, Deal, Order, OrderItem, Pizza


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class DealAdminForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        promotion_type = cleaned_data.get("promotion_type")
        promotion_price = cleaned_data.get("promotion_price")
        eligible_category = cleaned_data.get("eligible_category")
        eligible_pizzas = cleaned_data.get("eligible_pizzas")

        if promotion_type != Deal.PromotionType.NONE and promotion_price is None:
            self.add_error("promotion_price", "Enter a fixed price for this promotion.")
        if (
            promotion_type == Deal.PromotionType.CATEGORY_PAIR
            and eligible_category is None
        ):
            self.add_error("eligible_category", "Choose the category for this offer.")
        if (
            promotion_type == Deal.PromotionType.BUNDLE
            and eligible_pizzas is not None
            and eligible_pizzas.count() < 2
        ):
            self.add_error(
                "eligible_pizzas",
                "Choose at least two pizzas for this bundle.",
            )
        if (
            promotion_type == Deal.PromotionType.PIZZA_PRICE
            and eligible_pizzas is not None
            and eligible_pizzas.count() < 1
        ):
            self.add_error("eligible_pizzas", "Choose at least one eligible pizza.")

        return cleaned_data


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    form = DealAdminForm
    list_display = (
        "title",
        "offer_text",
        "is_featured",
        "is_active",
        "sort_order",
    )
    list_filter = ("is_active", "is_featured")
    search_fields = ("title", "description", "badge")
    list_editable = ("is_featured", "is_active", "sort_order")
    fieldsets = (
        (None, {"fields": ("title", "badge", "description")}),
        ("Offer display", {"fields": ("offer_text", "previous_price")}),
        ("Image and action", {"fields": ("image", "image_alt", "button_text", "button_url")}),
        ("Visibility", {"fields": ("is_featured", "is_active", "sort_order")}),
        (
            "Automatic checkout promotion",
            {
                "fields": (
                    "promotion_type",
                    "promotion_price",
                    "promotion_schedule",
                    "eligible_category",
                    "eligible_pizzas",
                ),
                "description": (
                    "Only one eligible automatic offer applies per order. "
                    "Bundles, category pairs, and individual-pizza offers require "
                    "small pizzas with original crust and no extra toppings. "
                    "Set the display offer text and promotion price to the same amount."
                ),
            },
        ),
    )
    filter_horizontal = ("eligible_pizzas",)


@admin.register(Pizza)
class PizzaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "small_price",
        "medium_price",
        "large_price",
        "extra_large_price",
        "is_active",
    )
    list_filter = ("category", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "description", "ingredients", "image", "is_active")}),
        ("Prices (GH₵)", {"fields": ("small_price", "medium_price", "large_price", "extra_large_price")}),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("pizza", "pizza_name", "quantity", "unit_price", "options")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer_name", "phone", "status", "total", "placed_at")
    list_filter = ("status", "placed_at")
    search_fields = ("reference", "customer_name", "phone")
    readonly_fields = (
        "reference",
        "subtotal",
        "discount_total",
        "discounts",
        "total",
        "placed_at",
    )
    inlines = [OrderItemInline]
