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
from .models import Category, Deal, MenuItem, Order, Pizza


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

    def test_asset_is_served_when_finder_returns_multiple_paths(self):
        content = b"sample favicon"

        with tempfile.TemporaryDirectory() as directory:
            asset_path = Path(directory, "favicon.ico")
            asset_path.write_bytes(content)

            with patch("ordering.views.finders.find", return_value=[str(asset_path)]):
                response = self.client.get("/favicon.ico")

            self.assertEqual(response.status_code, 200)
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
        self.assertEqual(len(response.json()["pizzas"]), 17)
        api_categories = {
            (category["name"], category["slug"])
            for category in response.json()["categories"]
        }
        self.assertEqual(
            api_categories,
            {
                ("Pizza", "pizza"),
                ("Loaded Fries", "loaded-fries"),
                ("Drinks", "drinks"),
                ("Weekend Promo", "weekend-promo"),
                ("Combo", "combo"),
            },
        )
        self.assertEqual(
            set(Category.objects.values_list("slug", flat=True)),
            {"pizza", "loaded-fries", "drinks", "weekend-promo", "combo"},
        )
        self.assertEqual(
            Pizza.objects.filter(category__slug="pizza").count(),
            Pizza.objects.count(),
        )
        self.assertEqual(self.pizza.category.slug, "pizza")
        self.assertIsNone(self.pizza.category.parent_id)
        margherita = next(
            pizza
            for pizza in response.json()["pizzas"]
            if pizza["slug"] == "margherita"
        )
        self.assertEqual(
            margherita["prices"],
            {"S": "20.00", "M": "30.00", "L": "40.00", "XL": "50.00"},
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

    def test_catalog_api_exposes_only_the_five_main_categories(self):
        Category.objects.create(name="Limited Time", slug="limited-time")

        response = self.client.get("/api/pizzas/")

        self.assertEqual(
            {category["slug"] for category in response.json()["categories"]},
            {"pizza", "loaded-fries", "drinks", "weekend-promo", "combo"},
        )

    def test_active_admin_menu_items_are_listed_under_their_category(self):
        category = Category.objects.get(slug="loaded-fries")
        item = MenuItem.objects.create(
            slug="loaded-fries",
            name="Loaded Fries",
            category=category,
            description="Crispy fries with cheese.",
            image="loaded-fries.jpg",
            price=Decimal("18.50"),
        )

        response = self.client.get("/api/pizzas/")
        catalog_item = next(
            menu_item
            for menu_item in response.json()["menu_items"]
            if menu_item["slug"] == item.slug
        )

        self.assertEqual(
            catalog_item,
            {
                "slug": "loaded-fries",
                "name": "Loaded Fries",
                "category": "Loaded Fries",
                "category_slug": "loaded-fries",
                "description": "Crispy fries with cheese.",
                "image": "/static/loaded-fries.jpg",
                "price": "18.50",
            },
        )
        self.assertIn(
            {"name": "Loaded Fries", "slug": "loaded-fries"},
            response.json()["menu_item_categories"],
        )

    def test_single_price_menu_item_can_be_quoted_and_ordered(self):
        item = MenuItem.objects.create(
            slug="orange-drink",
            name="Orange Drink",
            category=Category.objects.get(slug="drinks"),
            description="Chilled orange drink.",
            image="orange-drink.jpg",
            price=Decimal("7.50"),
        )
        self.payload["items"] = [
            {
                "menuItemSlug": item.slug,
                "quantity": 2,
                "unitPrice": 0,
                "price": 0,
            }
        ]

        quote = self.post_json(
            "/api/orders/quote/",
            {"items": self.payload["items"]},
        )

        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["subtotal"], "15.00")
        self.assertEqual(quote.json()["discount_total"], "0.00")
        self.assertEqual(quote.json()["items"][0]["pizza"], "Orange Drink")
        self.assertNotIn("size", quote.json()["items"][0])

        created = self.post_json("/api/orders/", self.payload)

        self.assertEqual(created.status_code, 201)
        order = Order.objects.get(reference=created.json()["reference"])
        order_item = order.items.get()
        self.assertIsNone(order_item.pizza)
        self.assertEqual(order_item.menu_item, item)
        self.assertEqual(order_item.pizza_name, item.name)
        self.assertEqual(order_item.unit_price, Decimal("7.50"))
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order.total, Decimal("15.00"))

    def test_django_admin_can_create_a_loaded_fries_menu_item(self):
        category = Category.objects.get(slug="loaded-fries")
        admin_user = get_user_model().objects.create_superuser(
            username="menu-item-admin",
            email="menu-item-admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:ordering_menuitem_add"),
            {
                "name": "Admin Loaded Fries",
                "slug": "admin-loaded-fries",
                "category": str(category.pk),
                "description": "Crispy fries with cheese.",
                "image": "loaded-fries.jpg",
                "price": "18.50",
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        item = MenuItem.objects.get(slug="admin-loaded-fries")
        self.assertEqual(item.category, category)
        self.assertEqual(item.price, Decimal("18.50"))
        self.assertIn(
            item.slug,
            [
                menu_item["slug"]
                for menu_item in self.client.get("/api/pizzas/").json()["menu_items"]
            ],
        )

    def test_pizza_admin_form_rejects_negative_prices_and_invalid_ingredients(self):
        category_choices = PizzaAdminForm().fields["category"].queryset
        self.assertTrue(category_choices.filter(pk=self.pizza.category_id).exists())
        self.assertEqual(list(category_choices.values_list("slug", flat=True)), ["pizza"])
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
            button_url="menu.html#pizza",
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

    def test_half_price_pizzas_are_orderable_from_menu_and_removed_from_deals(self):
        menu_response = self.client.get("/api/pizzas/")
        self.assertEqual(menu_response.status_code, 200)
        pizzas = {
            pizza["slug"]: pizza
            for pizza in menu_response.json()["pizzas"]
        }
        expected_prices = {
            "shrimp-pizza": ("57.50", "79.00", "101.00", "122.50"),
            "ten-topping": ("55.00", "76.50", "98.50", "120.00"),
            "fruity-pizza": ("49.00", "67.50", "86.50", "105.00"),
            "four-cheese-margherita": ("49.00", "68.50", "88.00", "107.50"),
            "steak-house": ("49.00", "68.50", "88.00", "107.50"),
        }

        for slug, prices in expected_prices.items():
            with self.subTest(slug=slug):
                self.assertIn(slug, pizzas)
                self.assertEqual(pizzas[slug]["category"], "Pizza")
                self.assertEqual(
                    pizzas[slug]["prices"],
                    dict(zip(("S", "M", "L", "XL"), prices)),
                )
                self.assertNotIn("badge", pizzas[slug])

        deals_response = self.client.get("/api/deals/")
        self.assertEqual(deals_response.status_code, 200)
        deal_titles = {deal["title"] for deal in deals_response.json()["deals"]}
        self.assertTrue(
            {"Shrimp Pizza", "Ten-Topping", "Fruity Pizza",
             "4 Cheese Margherita", "Steak House"}.isdisjoint(deal_titles)
        )

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

    def test_two_classics_uses_its_explicit_eligible_pizzas(self):
        deal = Deal.objects.get(title="Two Classics")
        self.assertEqual(
            set(deal.eligible_pizzas.values_list("slug", flat=True)),
            {"margherita", "pepperoni-classic", "four-cheese"},
        )

        quote = self.post_json(
            "/api/orders/quote/",
            {
                "items": [
                    self.standard_item("margherita"),
                    self.standard_item("truffle-mushroom"),
                ]
            },
        )

        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json()["discount_total"], "0.00")
        self.assertEqual(quote.json()["discounts"], [])

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
