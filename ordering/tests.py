import json
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .admin import PizzaAdminForm
from .models import Category, Deal, Order, Pizza


class FrontendAssetTests(SimpleTestCase):
    def test_project_assets_are_found_and_served_under_static_url(self):
        self.assertIsNotNone(finders.find("pizza.css"))
        self.assertIsNotNone(finders.find("js/cart.js"))

        response = self.client.get("/static/pizza.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])
        response.close()

        admin_response = self.client.get("/static/admin/css/base.css")
        self.assertEqual(admin_response.status_code, 200)
        admin_response.close()

    def test_mp4_assets_are_served(self):
        content = b"sample video"

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "banner.mp4").write_bytes(content)

            with override_settings(STATICFILES_DIRS=[directory]):
                response = self.client.get("/banner.mp4")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "video/mp4")
            self.assertEqual(b"".join(response.streaming_content), content)
            response.close()


class OrderingApiTests(TestCase):
    def setUp(self):
        self.pizza = Pizza.objects.get(slug="margherita")
        self.payload = {
            "customer": {
                "name": "Test Customer",
                "phone": "+233 24 123 4567",
                "address": "1 Sample Street",
                "city": "Accra",
                "instructions": "",
            },
            "items": [
                {
                    "slug": self.pizza.slug,
                    "pizza": self.pizza.name,
                    "quantity": 2,
                    "size": "M",
                    "dough": "Classic",
                    "crust": "Stuffed crust",
                    "extraToppings": ["Mushrooms", "Olives"],
                    "removedIngredients": [],
                    "unitPrice": 0,
                    "price": 0,
                }
            ],
        }

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def standard_item(self, slug, size="S"):
        pizza = Pizza.objects.get(slug=slug)
        return {
            "slug": pizza.slug,
            "quantity": 1,
            "size": size,
            "dough": "Classic",
            "crust": "Original",
            "extraToppings": [],
            "removedIngredients": [],
        }

    def test_catalog_lists_seeded_pizzas_and_server_prices(self):
        response = self.client.get("/api/pizzas/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["pizzas"]), 12)
        self.assertIn(
            {"name": self.pizza.category.name, "slug": self.pizza.category.slug},
            response.json()["categories"],
        )
        self.assertEqual(
            response.json()["pizzas"][0]["prices"],
            {"S": "20.00", "M": "30.00", "L": "40.00", "XL": "50.00"},
        )
        margherita = next(
            pizza
            for pizza in response.json()["pizzas"]
            if pizza["slug"] == "margherita"
        )
        self.assertEqual(margherita["image"], "/static/Pizza-Margheritta.webp")

    def test_catalog_normalizes_encoded_image_filenames(self):
        self.pizza.image = "hot%20honey.jpg"
        self.pizza.save(update_fields=["image"])

        response = self.client.get("/api/pizzas/")
        margherita = next(
            pizza
            for pizza in response.json()["pizzas"]
            if pizza["slug"] == "margherita"
        )

        self.assertEqual(margherita["image"], "/static/hot%20honey.jpg")

    def test_admin_created_category_is_available_in_menu_api(self):
        category = Category.objects.create(name="Limited Time", slug="limited-time")
        self.pizza.category = category
        self.pizza.save(update_fields=["category"])

        response = self.client.get("/api/pizzas/")
        catalog_pizza = next(
            pizza
            for pizza in response.json()["pizzas"]
            if pizza["slug"] == self.pizza.slug
        )

        self.assertIn(
            {"name": "Limited Time", "slug": "limited-time"},
            response.json()["categories"],
        )
        self.assertEqual(catalog_pizza["category_slug"], "limited-time")

    def test_pizza_admin_form_rejects_negative_prices_and_invalid_ingredients(self):
        form = PizzaAdminForm(
            data={
                "slug": self.pizza.slug,
                "name": self.pizza.name,
                "category": str(self.pizza.category_id),
                "description": self.pizza.description,
                "ingredients": json.dumps({"not": "a list"}),
                "image": self.pizza.image,
                "small_price": "-1.00",
                "medium_price": "30.00",
                "large_price": "40.00",
                "extra_large_price": "50.00",
                "is_active": "on",
            },
            instance=self.pizza,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("small_price", form.errors)
        self.assertIn("ingredients", form.errors)

    def test_deals_api_lists_active_deals_and_hides_inactive_deals(self):
        Deal.objects.create(
            title="Weekend special",
            badge="Weekends",
            description="A weekend offer.",
            image="four-cheese.jpg",
            image_alt="Four cheese pizza",
            offer_text="GH₵18",
            previous_price=Decimal("20.00"),
            button_text="View pizza",
            button_url="menu.html#classic",
            is_featured=True,
        )
        Deal.objects.create(
            title="Hidden offer",
            description="Not currently available.",
            image="vegan.jpg",
            image_alt="Vegan pizza",
            offer_text="GH₵15",
            button_url="menu.html",
            is_active=False,
        )

        response = self.client.get("/api/deals/")

        self.assertEqual(response.status_code, 200)
        deals = response.json()["deals"]
        visible_deal = next(deal for deal in deals if deal["title"] == "Weekend special")
        self.assertEqual(visible_deal["image"], "/static/four-cheese.jpg")
        self.assertEqual(visible_deal["previous_price"], "20.00")
        self.assertTrue(visible_deal["is_featured"])
        self.assertNotIn("Hidden offer", [deal["title"] for deal in deals])

    def test_quote_applies_best_classic_pair_and_order_saves_discount(self):
        self.payload["items"] = [
            self.standard_item("margherita"),
            self.standard_item("four-cheese"),
        ]

        quote = self.post_json(
            "/api/orders/quote/",
            {"items": self.payload["items"]},
        )

        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["subtotal"], "40.00")
        self.assertEqual(quote.json()["discount_total"], "5.00")
        self.assertEqual(quote.json()["total"], "35.00")
        self.assertEqual(quote.json()["discounts"][0]["title"], "Two Classics")

        created = self.post_json("/api/orders/", self.payload)

        self.assertEqual(created.status_code, 201)
        order = Order.objects.get(reference=created.json()["reference"])
        self.assertEqual(order.subtotal, Decimal("40.00"))
        self.assertEqual(order.discount_total, Decimal("5.00"))
        self.assertEqual(order.total, Decimal("35.00"))
        self.assertEqual(order.discounts[0]["title"], "Two Classics")
        self.assertEqual(created.json()["discount_total"], "5.00")
        self.assertEqual(created.json()["subtotal"], "40.00")

    def test_family_feast_requires_all_three_standard_pizzas(self):
        self.payload["items"] = [
            self.standard_item("meat-lovers"),
            self.standard_item("four-cheese"),
            self.standard_item("margherita"),
        ]

        quote = self.post_json(
            "/api/orders/quote/",
            {"items": self.payload["items"]},
        )

        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["subtotal"], "60.00")
        self.assertEqual(quote.json()["discount_total"], "10.00")
        self.assertEqual(quote.json()["total"], "50.00")
        self.assertEqual(quote.json()["discounts"][0]["title"], "Family Feast")

    @patch("ordering.views.timezone.localdate", return_value=date(2026, 11, 17))
    def test_veggie_tuesday_offer_applies_only_on_tuesday(self, _localdate):
        items = [self.standard_item("garden-veggie")]

        tuesday = self.post_json("/api/orders/quote/", {"items": items})
        self.assertEqual(tuesday.json()["discount_total"], "5.00")
        self.assertEqual(tuesday.json()["discounts"][0]["title"], "Veggie Tuesday")

        with patch("ordering.views.timezone.localdate", return_value=date(2026, 11, 16)):
            monday = self.post_json("/api/orders/quote/", {"items": items})
        self.assertEqual(monday.json()["discount_total"], "0.00")
        self.assertEqual(monday.json()["discounts"], [])

    @patch("ordering.views.timezone.localdate", return_value=date(2026, 11, 15))
    def test_cheese_weekend_offer_applies_to_standard_small_pizza(self, _localdate):
        quote = self.post_json(
            "/api/orders/quote/",
            {"items": [self.standard_item("four-cheese")]},
        )

        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["discount_total"], "2.00")
        self.assertEqual(quote.json()["total"], "18.00")
        self.assertEqual(quote.json()["discounts"][0]["title"], "Cheese Weekend")

    @patch("ordering.views.timezone.localdate", return_value=date(2026, 11, 16))
    def test_automatic_offer_does_not_apply_to_custom_or_larger_pizza(self, _localdate):
        customized = self.standard_item("margherita")
        customized["size"] = "M"
        customized["crust"] = "Stuffed crust"
        quote = self.post_json(
            "/api/orders/quote/",
            {"items": [customized, self.standard_item("four-cheese")]},
        )

        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["discount_total"], "0.00")
        self.assertEqual(quote.json()["discounts"], [])

    def test_catalog_uses_admin_configured_price_for_each_size(self):
        self.pizza.medium_price = Decimal("34.50")
        self.pizza.large_price = Decimal("46.00")
        self.pizza.extra_large_price = Decimal("57.25")
        self.pizza.save(
            update_fields=("medium_price", "large_price", "extra_large_price")
        )

        response = self.client.get("/api/pizzas/margherita/")

        self.assertEqual(
            response.json()["prices"],
            {"S": "20.00", "M": "34.50", "L": "46.00", "XL": "57.25"},
        )

    def test_pizza_detail_returns_catalog_data_and_hides_inactive_pizzas(self):
        response = self.client.get("/api/pizzas/margherita/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Margherita")

        self.pizza.is_active = False
        self.pizza.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/pizzas/margherita/").status_code, 404)
        self.assertNotIn(
            "margherita",
            [pizza["slug"] for pizza in self.client.get("/api/pizzas/").json()["pizzas"]],
        )

    def test_order_uses_server_prices_and_can_be_tracked(self):
        response = self.post_json("/api/orders/", self.payload)

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertRegex(created["reference"], r"^PS-[A-F0-9]{12}$")
        self.assertEqual(created["total"], "82.00")
        self.assertEqual(created["status"], Order.Status.RECEIVED)
        order = Order.objects.get(reference=created["reference"])
        self.assertEqual(order.phone, "233241234567")
        item = order.items.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("41.00"))
        self.assertEqual(
            item.options,
            {
                "size": "M",
                "dough": "Classic",
                "crust": "Stuffed crust",
                "extraToppings": ["Mushrooms", "Olives"],
                "removedIngredients": [],
            },
        )

        tracked = self.post_json(
            "/api/orders/lookup/",
            {"order": created["reference"], "phone": "233 241 234 567"},
        )
        self.assertEqual(tracked.status_code, 200)
        self.assertEqual(tracked.json()["items"][0]["pizza"], "Margherita")
        self.assertEqual(tracked.json()["total"], "82.00")

    def test_order_saves_custom_options_and_uses_server_price(self):
        self.payload["items"] = [
            {
                "slug": self.pizza.slug,
                "pizza": "Untrusted client name",
                "quantity": 2,
                "size": "XL",
                "dough": "Whole wheat",
                "crust": "Gluten-free",
                "extraToppings": ["Mushrooms"],
                "removedIngredients": ["basil"],
                "unitPrice": 1,
                "price": 2,
            }
        ]

        response = self.post_json("/api/orders/", self.payload)

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(reference=response.json()["reference"])
        item = order.items.get()
        self.assertEqual(order.subtotal, Decimal("116.00"))
        self.assertEqual(order.total, Decimal("116.00"))
        self.assertEqual(item.pizza, self.pizza)
        self.assertEqual(item.pizza_name, self.pizza.name)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("58.00"))
        self.assertEqual(
            item.options,
            {
                "size": "XL",
                "dough": "Whole wheat",
                "crust": "Gluten-free",
                "extraToppings": ["Mushrooms"],
                "removedIngredients": ["basil"],
            },
        )

    def test_order_rejects_invalid_dough_crust_and_removed_ingredients(self):
        invalid_options = (
            ("dough", "Invalid dough"),
            ("crust", "Invalid crust"),
            ("removedIngredients", ["Not an ingredient"]),
        )
        for field, value in invalid_options:
            with self.subTest(field=field):
                self.payload["items"][0][field] = value
                response = self.post_json("/api/orders/", self.payload)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(Order.objects.count(), 0)
                self.payload["items"][0][field] = {
                    "dough": "Classic",
                    "crust": "Stuffed crust",
                    "removedIngredients": [],
                }[field]

    def test_order_rejects_a_negative_admin_price(self):
        self.pizza.small_price = Decimal("-1.00")
        self.pizza.save(update_fields=["small_price"])
        self.payload["items"][0]["size"] = "S"

        response = self.post_json("/api/orders/", self.payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_total_uses_configured_size_price(self):
        self.pizza.medium_price = Decimal("35.50")
        self.pizza.save(update_fields=["medium_price"])

        response = self.post_json("/api/orders/", self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["total"], "93.00")

    def test_order_lookup_requires_matching_phone(self):
        created = self.post_json("/api/orders/", self.payload).json()

        response = self.post_json(
            "/api/orders/lookup/",
            {"order": created["reference"], "phone": "024 999 0000"},
        )

        self.assertEqual(response.status_code, 404)

    def test_order_lookup_returns_status_updated_in_admin(self):
        created = self.post_json("/api/orders/", self.payload).json()
        order = Order.objects.get(reference=created["reference"])
        order.status = Order.Status.PREPARING
        order.save(update_fields=["status"])

        tracked = self.post_json(
            "/api/orders/lookup/",
            {"order": created["reference"], "phone": "233 241 234 567"},
        )

        self.assertEqual(tracked.status_code, 200)
        self.assertEqual(tracked.json()["status"], Order.Status.PREPARING)
        self.assertEqual(tracked.json()["status_label"], "Preparing")

    def test_order_status_is_editable_in_django_admin(self):
        created = self.post_json("/api/orders/", self.payload).json()
        order = Order.objects.get(reference=created["reference"])
        admin_user = get_user_model().objects.create_superuser(
            username="ordering-admin",
            email="ordering-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("admin:ordering_order_change", args=[order.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.context["adminform"].form.fields)

    def test_order_rejects_unavailable_topping(self):
        self.payload["items"][0]["extraToppings"] = ["Not on the menu"]

        response = self.post_json("/api/orders/", self.payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_rejects_invalid_size(self):
        self.payload["items"][0]["size"] = "XXL"

        response = self.post_json("/api/orders/", self.payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_page_sets_csrf_cookie(self):
        response = self.client.get("/checkout.html")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_order_endpoint_rejects_missing_csrf_token(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/api/orders/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_order_endpoint_accepts_checkout_csrf_token(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.get("/checkout.html")
        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            "/api/orders/",
            data=json.dumps(self.payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201)
