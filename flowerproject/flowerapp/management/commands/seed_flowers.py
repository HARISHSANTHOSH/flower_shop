from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from flowerapp.models import Category, Flower


class Command(BaseCommand):
    help = "Seed the database with sample categories and flowers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--categories",
            type=int,
            default=50,
            help="Number of categories to seed (default: 50)",
        )
        parser.add_argument(
            "--flowers",
            type=int,
            default=50,
            help="Number of flowers to seed (default: 50)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        category_target = max(1, options["categories"])
        flower_target = max(1, options["flowers"])

        categories = self._seed_categories(category_target)
        self._seed_flowers(flower_target, categories)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {category_target} categories and {flower_target} flowers."
            )
        )

    def _seed_categories(self, category_target):
        categories = []
        for idx in range(1, category_target + 1):
            category, _ = Category.objects.get_or_create(
                name=f"Category {idx}",
                defaults={
                    "descrition": f"Sample description for category {idx}.",
                },
            )
            categories.append(category)
        return categories

    def _seed_flowers(self, flower_target, categories):
        if not categories:
            raise ValueError("Cannot seed flowers without at least one category.")

        category_count = len(categories)
        for idx in range(1, flower_target + 1):
            category = categories[(idx - 1) % category_count]
            price = Decimal("10.00") + Decimal(idx) * Decimal("0.50")

            Flower.objects.update_or_create(
                name=f"Flower {idx}",
                defaults={
                    "description": f"Sample flower description {idx}.",
                    "price": price,
                    "category": category,
                },
            )

