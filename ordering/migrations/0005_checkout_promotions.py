from decimal import Decimal

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


def configure_initial_promotions(apps, schema_editor):
    Deal = apps.get_model("ordering", "Deal")
    Category = apps.get_model("ordering", "Category")
    Pizza = apps.get_model("ordering", "Pizza")
    database = schema_editor.connection.alias

    configurations = {
        "Family Feast": {
            "promotion_type": "bundle",
            "promotion_price": Decimal("50.00"),
            "pizza_slugs": ("meat-lovers", "four-cheese", "margherita"),
        },
        "Two Classics": {
            "promotion_type": "category_pair",
            "promotion_price": Decimal("35.00"),
            "category_slug": "classic",
        },
        "Veggie Tuesday": {
            "promotion_type": "pizza_price",
            "promotion_price": Decimal("15.00"),
            "promotion_schedule": "tuesday",
            "pizza_slugs": ("garden-veggie",),
        },
        "Cheese Weekend": {
            "promotion_type": "pizza_price",
            "promotion_price": Decimal("18.00"),
            "promotion_schedule": "weekend",
            "pizza_slugs": ("four-cheese",),
        },
    }

    for title, configuration in configurations.items():
        deal = Deal.objects.using(database).filter(title=title).first()
        if deal is None:
            continue
        deal.promotion_type = configuration["promotion_type"]
        deal.promotion_price = configuration["promotion_price"]
        deal.promotion_schedule = configuration.get("promotion_schedule", "any_day")
        category_slug = configuration.get("category_slug")
        if category_slug:
            deal.eligible_category_id = (
                Category.objects.using(database)
                .filter(slug=category_slug)
                .values_list("pk", flat=True)
                .first()
            )
        deal.save(
            using=database,
            update_fields=(
                "promotion_type",
                "promotion_price",
                "promotion_schedule",
                "eligible_category",
            ),
        )
        pizza_ids = list(
            Pizza.objects.using(database)
            .filter(slug__in=configuration.get("pizza_slugs", ()))
            .values_list("pk", flat=True)
        )
        through = Deal.eligible_pizzas.through
        through.objects.using(database).bulk_create(
            [
                through(deal_id=deal.pk, pizza_id=pizza_id)
                for pizza_id in pizza_ids
            ],
            ignore_conflicts=True,
        )


def preserve_existing_order_totals(apps, schema_editor):
    Order = apps.get_model("ordering", "Order")
    database = schema_editor.connection.alias
    for order in Order.objects.using(database).all().iterator():
        order.subtotal = order.total
        order.discount_total = Decimal("0.00")
        order.discounts = []
        order.save(
            using=database,
            update_fields=("subtotal", "discount_total", "discounts"),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ordering", "0004_deal"),
    ]

    operations = [
        migrations.AddField(
            model_name="deal",
            name="eligible_category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deals",
                to="ordering.category",
            ),
        ),
        migrations.AddField(
            model_name="deal",
            name="eligible_pizzas",
            field=models.ManyToManyField(
                blank=True,
                related_name="deals",
                to="ordering.pizza",
            ),
        ),
        migrations.AddField(
            model_name="deal",
            name="promotion_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=7,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="deal",
            name="promotion_schedule",
            field=models.CharField(
                choices=[
                    ("any_day", "Any day"),
                    ("tuesday", "Tuesday only"),
                    ("weekend", "Saturday and Sunday"),
                ],
                default="any_day",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="deal",
            name="promotion_type",
            field=models.CharField(
                choices=[
                    ("none", "Informational only"),
                    ("bundle", "Fixed-price bundle"),
                    ("category_pair", "Fixed price for two category pizzas"),
                    ("pizza_price", "Fixed price for one pizza"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="discount_total",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=9),
        ),
        migrations.AddField(
            model_name="order",
            name="discounts",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="order",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=9),
        ),
        migrations.RunPython(configure_initial_promotions, migrations.RunPython.noop),
        migrations.RunPython(preserve_existing_order_totals, migrations.RunPython.noop),
    ]
