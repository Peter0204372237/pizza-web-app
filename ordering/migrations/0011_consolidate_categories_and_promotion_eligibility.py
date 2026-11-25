from django.db import migrations, models
from django.db.models import Q


MAIN_CATEGORIES = (
    ("Pizza", "pizza"),
    ("Loaded Fries", "loaded-fries"),
    ("Drinks", "drinks"),
    ("Weekend Promo", "weekend-promo"),
    ("Combo", "combo"),
)
LEGACY_CATEGORY_SLUGS = (
    "classic",
    "deep-dish",
    "meat-lovers",
    "plant-based",
    "signature",
)
LEGACY_CATEGORY_NAMES = (
    "Classic",
    "Deep dish",
    "Meat lovers",
    "Plant-based",
    "Signature",
)


def consolidate_categories(apps, schema_editor):
    Category = apps.get_model("ordering", "Category")
    Deal = apps.get_model("ordering", "Deal")
    MenuItem = apps.get_model("ordering", "MenuItem")
    Pizza = apps.get_model("ordering", "Pizza")
    database = schema_editor.connection.alias

    canonical = {}
    for name, slug in MAIN_CATEGORIES:
        category = Category.objects.using(database).filter(slug=slug).first()
        named_category = Category.objects.using(database).filter(name=name).first()
        if category and named_category and category.pk != named_category.pk:
            raise RuntimeError(
                f"Cannot consolidate categories: both {name!r} and slug "
                f"{slug!r} already exist on different records."
            )
        if category is None:
            category = named_category
        if category is None:
            category = Category.objects.using(database).create(name=name, slug=slug)
        elif category.slug != slug or category.name != name:
            category.slug = slug
            category.name = name
            category.save(using=database, update_fields=("name", "slug"))
        canonical[slug] = category

    canonical_ids = {category.pk for category in canonical.values()}
    pizza_category = canonical["pizza"]
    legacy_filter = Q(slug__in=LEGACY_CATEGORY_SLUGS) | Q(
        name__in=LEGACY_CATEGORY_NAMES
    )
    retired_ids = set(
        Category.objects.using(database)
        .filter(legacy_filter)
        .exclude(pk__in=canonical_ids)
        .values_list("pk", flat=True)
    )
    while True:
        child_ids = set(
            Category.objects.using(database)
            .filter(parent_id__in=retired_ids)
            .exclude(pk__in=retired_ids | canonical_ids)
            .values_list("pk", flat=True)
        )
        if not child_ids:
            break
        retired_ids.update(child_ids)

    unexpected_categories = list(
        Category.objects.using(database)
        .exclude(pk__in=canonical_ids | retired_ids)
        .order_by("name")
        .values_list("name", "slug")
    )
    if unexpected_categories:
        details = ", ".join(
            f"{name!r} ({slug})" for name, slug in unexpected_categories
        )
        raise RuntimeError(
            "Category consolidation stopped to preserve uncategorized data. "
            f"Review these non-canonical categories first: {details}"
        )

    affected_menu_items = list(
        MenuItem.objects.using(database)
        .filter(category_id__in=retired_ids)
        .select_related("category")
        .order_by("name", "pk")
    )
    if affected_menu_items:
        details = ", ".join(
            f"{item.name!r} ({item.slug}) in "
            f"{item.category.name!r} ({item.category.slug})"
            for item in affected_menu_items
        )
        raise RuntimeError(
            "Category consolidation stopped because menu items reference legacy "
            f"categories: {details}. Choose their destination categories before "
            "running this migration."
        )

    for deal in Deal.objects.using(database).filter(
        promotion_type="category_pair",
        eligible_category_id__isnull=False,
    ):
        category_ids = {deal.eligible_category_id}
        pending_category_ids = [deal.eligible_category_id]
        while pending_category_ids:
            child_ids = list(
                Category.objects.using(database)
                .filter(parent_id__in=pending_category_ids)
                .exclude(pk__in=category_ids)
                .values_list("pk", flat=True)
            )
            category_ids.update(child_ids)
            pending_category_ids = child_ids
        pizza_ids = list(
            Pizza.objects.using(database)
            .filter(category_id__in=category_ids)
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

    Pizza.objects.using(database).all().update(category_id=pizza_category.pk)
    Deal.objects.using(database).filter(
        eligible_category_id__isnull=False,
    ).update(eligible_category_id=None)
    Category.objects.using(database).filter(
        pk__in=canonical_ids,
    ).update(parent_id=None)
    Category.objects.using(database).filter(
        pk__in=retired_ids,
    ).update(parent_id=None)
    Category.objects.using(database).filter(pk__in=retired_ids).delete()

    Deal.objects.using(database).filter(
        button_url__in=(
            "menu.html#classic",
            "menu.html#deep-dish",
            "menu.html#meat-lovers",
            "menu.html#plant-based",
            "menu.html#signature",
        )
    ).update(button_url="menu.html#pizza")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("ordering", "0010_category_parent"),
    ]

    operations = [
        migrations.RunPython(consolidate_categories, atomic=True),
        migrations.RemoveField(
            model_name="deal",
            name="eligible_category",
        ),
        migrations.AlterField(
            model_name="deal",
            name="promotion_type",
            field=models.CharField(
                choices=[
                    ("none", "Informational only"),
                    ("bundle", "Fixed-price bundle"),
                    ("category_pair", "Fixed price for two eligible pizzas"),
                    ("pizza_price", "Fixed price for one pizza"),
                ],
                default="none",
                max_length=20,
            ),
        ),
    ]
