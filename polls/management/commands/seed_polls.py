from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from polls.models import Question


class Command(BaseCommand):
    help = "Create demonstration polls without resetting existing votes."

    @transaction.atomic
    def handle(self, *args, **options):
        examples = [
            (
                "What's your favorite programming language?",
                ["Python", "JavaScript", "Java", "C++"],
            ),
            (
                "Which Django feature do you find most useful?",
                ["ORM", "Admin site", "Templates", "URL routing"],
            ),
            (
                "How do you prefer to learn a new framework?",
                [
                    "Official tutorials",
                    "Building projects",
                    "Videos",
                    "Pair programming",
                ],
            ),
        ]
        created_count = 0
        for offset, (text, choices) in enumerate(examples):
            question, created = Question.objects.get_or_create(
                question_text=text,
                defaults={"pub_date": timezone.now() - timedelta(minutes=offset + 1)},
            )
            created_count += created
            for choice_text in choices:
                question.choice_set.get_or_create(choice_text=choice_text)
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} polls; existing votes preserved."
            )
        )
