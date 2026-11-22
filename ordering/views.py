import json
import mimetypes
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Category, Deal, Order, OrderItem, Pizza


PIZZA_SIZES = {"S", "M", "L", "XL"}
DOUGH_CHOICES = {"Classic", "Thin and crispy", "Whole wheat"}
CRUST_SURCHARGES = {
    "Original": Decimal("0.00"),
    "Stuffed crust": Decimal("5.00"),
    "Gluten-free": Decimal("5.00"),
}
EXTRA_TOPPINGS = {
    "Extra mozzarella",
    "Mushrooms",
    "Olives",
    "Jalapeños",
    "Bacon",
    "Pineapple",
}
PAGE_NAMES = {
    "cart.html",
    "categories.html",
    "checkout.html",
    "deals.html",
    "index.html",
    "menu.html",
    "pizza-details.html",
    "trackorders.html",
}


def error_response(message, status=400):
    return JsonResponse({"error": message}, status=status)


def static_asset_url(path):
    if path.startswith(("http://", "https://")):
        return path

    path = unquote(path).lstrip("/")
    if path.startswith("static/"):
        path = path[len("static/"):]
    return static(path)


def serialize_pizza(pizza):
    return {
        "slug": pizza.slug,
        "name": pizza.name,
        "category": pizza.category.name,
        "category_slug": pizza.category.slug,
        "description": pizza.description,
        "ingredients": pizza.ingredients,
        "image": static_asset_url(pizza.image),
        "prices": {
            size: str(pizza.price_for_size(size))
            for size in ("S", "M", "L", "XL")
        },
    }


def serialize_deal(deal):
    return {
        "title": deal.title,
        "badge": deal.badge,
        "description": deal.description,
        "image": static_asset_url(deal.image),
        "image_alt": deal.image_alt,
        "offer_text": (
            f"GH₵{deal.promotion_price}"
            if deal.promotion_price is not None
            and deal.promotion_type != Deal.PromotionType.NONE
            else deal.offer_text
        ),
        "previous_price": (
            str(deal.previous_price) if deal.previous_price is not None else None
        ),
        "promotion_type": deal.promotion_type,
        "promotion_price": (
            str(deal.promotion_price)
            if deal.promotion_price is not None
            and deal.promotion_type != Deal.PromotionType.NONE
            else None
        ),
        "promotion_schedule": deal.promotion_schedule,
        "button_text": deal.button_text,
        "button_url": deal.button_url,
        "is_featured": deal.is_featured,
    }


def serialize_order(order):
    return {
        "reference": order.reference,
        "status": order.status,
        "status_label": order.get_status_display(),
        "placed_at": order.placed_at.isoformat(),
        "payment_method": order.payment_method,
        "subtotal": str(order.subtotal),
        "discount_total": str(order.discount_total),
        "discounts": order.discounts,
        "total": str(order.total),
        "items": [
            {
                "pizza": item.pizza_name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.unit_price * item.quantity),
                **item.options,
            }
            for item in order.items.all()
        ],
    }


@require_GET
def pizza_list(request):
    pizzas = Pizza.objects.filter(is_active=True).select_related("category")
    categories = Category.objects.filter(pizzas__is_active=True).distinct()
    return JsonResponse(
        {
            "categories": [
                {"name": category.name, "slug": category.slug}
                for category in categories
            ],
            "pizzas": [serialize_pizza(pizza) for pizza in pizzas],
        }
    )


@require_GET
def pizza_detail(request, slug):
    pizza = get_object_or_404(
        Pizza.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )
    return JsonResponse(serialize_pizza(pizza))


@require_GET
def deal_list(request):
    deals = Deal.objects.filter(is_active=True)
    return JsonResponse({"deals": [serialize_deal(deal) for deal in deals]})


def clean_text(value, field, max_length, required=True):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required.")
    if len(value) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer.")
    return value


def normalize_phone(value):
    phone = re.sub(r"\D", "", value)
    if not 7 <= len(phone) <= 15:
        raise ValueError("Enter a valid phone number.")
    return phone


def clean_string_list(value, field, allowed_values):
    if not isinstance(value, list) or len(value) > len(allowed_values):
        raise ValueError(f"{field} must be a list of valid options.")
    if any(not isinstance(item, str) or item not in allowed_values for item in value):
        raise ValueError(f"{field} contains an unavailable option.")
    if len(set(value)) != len(value):
        raise ValueError(f"{field} cannot contain duplicates.")
    return value


def prepare_item(raw_item):
    if not isinstance(raw_item, dict):
        raise ValueError("Each cart item must be an object.")

    slug = raw_item.get("slug")
    if isinstance(slug, str) and slug:
        pizza = Pizza.objects.filter(slug=slug, is_active=True).first()
    else:
        name = raw_item.get("pizza")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Each cart item must identify a menu pizza.")
        pizza = Pizza.objects.filter(name__iexact=name.strip(), is_active=True).first()
    if pizza is None:
        raise ValueError("A pizza in your cart is no longer available.")

    quantity = raw_item.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 99:
        raise ValueError("Choose a quantity between 1 and 99.")

    size = raw_item.get("size", "S")
    if not isinstance(size, str) or size not in PIZZA_SIZES:
        raise ValueError("Choose a valid pizza size.")
    dough = raw_item.get("dough", "Classic")
    if not isinstance(dough, str) or dough not in DOUGH_CHOICES:
        raise ValueError("Choose a valid dough.")
    crust = raw_item.get("crust", "Original")
    if not isinstance(crust, str) or crust not in CRUST_SURCHARGES:
        raise ValueError("Choose a valid crust.")

    extras = clean_string_list(
        raw_item.get("extraToppings", []),
        "Extra toppings",
        EXTRA_TOPPINGS,
    )
    removed = clean_string_list(
        raw_item.get("removedIngredients", []),
        "Removed ingredients",
        pizza.ingredients,
    )
    base_price = pizza.price_for_size(size)
    if base_price < 0:
        raise ValueError("This pizza has an invalid price and cannot be ordered.")

    unit_price = (
        base_price
        + CRUST_SURCHARGES[crust]
        + Decimal("3.00") * len(extras)
    )
    return {
        "pizza": pizza,
        "quantity": quantity,
        "unit_price": unit_price,
        "options": {
            "size": size,
            "dough": dough,
            "crust": crust,
            "extraToppings": extras,
            "removedIngredients": removed,
        },
    }


def is_promotion_day(deal, today):
    if deal.promotion_schedule == Deal.Schedule.TUESDAY:
        return today.weekday() == 1
    if deal.promotion_schedule == Deal.Schedule.WEEKEND:
        return today.weekday() in (5, 6)
    return True


def is_standard_small(item):
    options = item["options"]
    return (
        options["size"] == "S"
        and options["crust"] == "Original"
        and not options["extraToppings"]
    )


def bundle_regular_price(items, eligible_pizzas):
    pizzas_in_cart = {item["pizza"].pk for item in items if is_standard_small(item)}
    if not eligible_pizzas or any(pizza.pk not in pizzas_in_cart for pizza in eligible_pizzas):
        return None
    return sum(
        (pizza.price_for_size("S") for pizza in eligible_pizzas),
        Decimal("0.00"),
    )


def category_pair_regular_price(items, deal):
    eligible_units = [
        item["pizza"].price_for_size("S")
        for item in items
        if is_standard_small(item)
        and deal.eligible_category_id is not None
        and item["pizza"].category_id == deal.eligible_category_id
        for _ in range(item["quantity"])
    ]
    if len(eligible_units) < 2:
        return None
    return sum(
        sorted(eligible_units, reverse=True)[:2],
        Decimal("0.00"),
    )


def pizza_price_regular_price(items, deal):
    eligible_units = [
        item["pizza"].price_for_size("S")
        for item in items
        if is_standard_small(item)
        and item["pizza"].pk in {pizza.pk for pizza in deal.eligible_pizzas.all()}
        for _ in range(item["quantity"])
    ]
    if not eligible_units:
        return None
    return eligible_units[0]


REGULAR_PRICE_CALCULATORS = {
    Deal.PromotionType.BUNDLE: bundle_regular_price,
    Deal.PromotionType.CATEGORY_PAIR: category_pair_regular_price,
    Deal.PromotionType.PIZZA_PRICE: pizza_price_regular_price,
}


def calculate_order_discount(items):
    today = timezone.localdate()
    candidates = []

    for deal in (
        Deal.objects.filter(is_active=True)
        .exclude(promotion_type=Deal.PromotionType.NONE)
        .prefetch_related("eligible_pizzas")
        .select_related("eligible_category")
    ):
        if (
            deal.promotion_price is None
            or deal.promotion_price < 0
            or not is_promotion_day(deal, today)
        ):
            continue

        calculator = REGULAR_PRICE_CALCULATORS.get(deal.promotion_type)
        if calculator is None:
            continue
        if deal.promotion_type == Deal.PromotionType.BUNDLE:
            regular_price = bundle_regular_price(items, list(deal.eligible_pizzas.all()))
        else:
            regular_price = calculator(items, deal)
        if regular_price is None:
            continue

        savings = regular_price - deal.promotion_price
        if savings > 0:
            candidates.append((savings, deal))

    if not candidates:
        return Decimal("0.00"), []

    savings, deal = max(candidates, key=lambda candidate: candidate[0])
    return savings, [{"title": deal.title, "amount": str(savings)}]


def quote_items(raw_items):
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 50:
        raise ValueError("Your order must contain between 1 and 50 cart items.")
    return [prepare_item(raw_item) for raw_item in raw_items]


@require_POST
def quote_order(request):
    if request.content_type != "application/json":
        return error_response("Send the order items as JSON.", status=415)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("The order data must be an object.")
        items = quote_items(payload.get("items"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response("The order body must contain valid JSON.")
    except ValueError as error:
        return error_response(str(error))

    subtotal = sum(
        (item["unit_price"] * item["quantity"] for item in items),
        Decimal("0.00"),
    )
    discount_total, discounts = calculate_order_discount(items)
    return JsonResponse(
        {
            "subtotal": str(subtotal),
            "discount_total": str(discount_total),
            "discounts": discounts,
            "total": str(subtotal - discount_total),
            "items": [
                {
                    "pizza": item["pizza"].name,
                    "size": item["options"]["size"],
                    "quantity": item["quantity"],
                    "unit_price": str(item["unit_price"]),
                    "line_total": str(item["unit_price"] * item["quantity"]),
                }
                for item in items
            ],
        }
    )


@require_POST
def create_order(request):
    if request.content_type != "application/json":
        return error_response("Send the order as JSON.", status=415)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("The order data must be an object.")

        customer = payload.get("customer")
        raw_items = payload.get("items")
        if not isinstance(customer, dict):
            raise ValueError("Delivery details are required.")
        customer_name = clean_text(customer.get("name"), "Name", 120)
        phone_value = clean_text(customer.get("phone"), "Phone number", 40)
        phone = normalize_phone(phone_value)
        address = clean_text(customer.get("address"), "Street address", 250)
        city = clean_text(customer.get("city"), "City or area", 100)
        instructions = clean_text(
            customer.get("instructions", ""),
            "Delivery instructions",
            500,
            required=False,
        )
        items = quote_items(raw_items)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error_response("The order body must contain valid JSON.")
    except ValueError as error:
        return error_response(str(error))

    subtotal = sum(
        (item["unit_price"] * item["quantity"] for item in items),
        Decimal("0.00"),
    )
    discount_total, discounts = calculate_order_discount(items)
    total = subtotal - discount_total
    with transaction.atomic():
        order = Order.objects.create(
            customer_name=customer_name,
            phone=phone,
            address=address,
            city=city,
            instructions=instructions,
            subtotal=subtotal,
            discount_total=discount_total,
            discounts=discounts,
            total=total,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    pizza=item["pizza"],
                    pizza_name=item["pizza"].name,
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    options=item["options"],
                )
                for item in items
            ]
        )

    return JsonResponse(serialize_order(order), status=201)


@require_POST
def track_order(request):
    if request.content_type != "application/json":
        return error_response("Send the tracking details as JSON.", status=415)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError
        reference = payload.get("order", "").strip().upper()
        phone_value = payload.get("phone", "").strip()
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError, ValueError):
        return error_response("Enter a valid order reference and phone number.")
    if not re.fullmatch(r"PS-[A-Z0-9]{12}", reference):
        return error_response("Enter a valid order reference.")
    try:
        phone = normalize_phone(phone_value)
    except ValueError as error:
        return error_response(str(error))

    order = (
        Order.objects.prefetch_related("items")
        .filter(reference=reference, phone=phone)
        .first()
    )
    if order is None:
        return error_response("No order matches that reference and phone number.", status=404)
    return JsonResponse(serialize_order(order))


@ensure_csrf_cookie
def frontend_home(request):
    return frontend_page(request, "index.html")


@ensure_csrf_cookie
def frontend_page(request, page_name):
    if page_name not in PAGE_NAMES:
        raise Http404
    return FileResponse(open(settings.BASE_DIR / page_name, "rb"), content_type="text/html")


def frontend_asset(request, asset_path):
    asset_path = unquote(asset_path).replace("\\", "/")
    parts = Path(asset_path).parts
    if Path(asset_path).is_absolute() or any(
        part.startswith(".") or part == ".." for part in parts
    ):
        raise Http404
    if asset_path.startswith("static/"):
        asset_path = asset_path[len("static/"):]

    asset_file = finders.find(asset_path)
    if asset_file is None:
        raise Http404

    content_type, _encoding = mimetypes.guess_type(asset_file)
    return FileResponse(
        open(asset_file, "rb"),
        content_type=content_type or "application/octet-stream",
    )
