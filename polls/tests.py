from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Question


class PollsTests(TestCase):
    def setUp(self):
        self.question = Question.objects.create(
            question_text="Which language?", pub_date=timezone.now() - timedelta(hours=1)
        )
        self.choice = self.question.choice_set.create(choice_text="Python")
        self.vote_url = reverse("polls:vote", args=[self.question.pk])

    def test_root_redirects_to_polls(self):
        self.assertRedirects(self.client.get("/"), reverse("polls:index"))

    def test_index_lists_published_questions(self):
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, self.question.question_text)
        self.assertContains(response, reverse("polls:detail", args=[self.question.pk]))

    def test_index_empty_message(self):
        Question.objects.all().delete()
        self.assertContains(self.client.get(reverse("polls:index")), "No polls are available.")

    def test_index_returns_five_newest_questions(self):
        questions = [Question.objects.create(
            question_text=f"Poll {i}", pub_date=timezone.now() - timedelta(days=i + 1)
        ) for i in range(6)]
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(list(response.context["latest_question_list"]), [self.question, *questions[:4]])

    def test_future_questions_are_not_public(self):
        future = Question.objects.create(
            question_text="Future poll", pub_date=timezone.now() + timedelta(days=1)
        )
        self.assertNotContains(self.client.get(reverse("polls:index")), future.question_text)
        for route in ("polls:detail", "polls:results"):
            self.assertEqual(self.client.get(reverse(route, args=[future.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("polls:vote", args=[future.pk])).status_code, 404)

    def test_detail_has_form_and_csrf_token(self):
        response = self.client.get(reverse("polls:detail", args=[self.question.pk]))
        self.assertContains(response, self.choice.choice_text)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'method="post"')

    def test_vote_increments_only_selected_choice_and_redirects(self):
        other = self.question.choice_set.create(choice_text="Java")
        response = self.client.post(self.vote_url, {"choice": self.choice.pk})
        self.assertRedirects(response, reverse("polls:results", args=[self.question.pk]))
        self.choice.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.choice.votes, 1)
        self.assertEqual(other.votes, 0)

    def test_repeat_votes_accumulate(self):
        self.client.post(self.vote_url, {"choice": self.choice.pk})
        self.client.post(self.vote_url, {"choice": self.choice.pk})
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 2)

    def test_invalid_votes_do_not_change_count(self):
        for value in (None, "", "invalid", 999999, "9" * 100):
            with self.subTest(value=value):
                data = {} if value is None else {"choice": value}
                response = self.client.post(self.vote_url, data)
                self.assertContains(response, "You didn&#x27;t select a valid choice.")
                self.choice.refresh_from_db()
                self.assertEqual(self.choice.votes, 0)

    def test_choice_from_another_poll_is_rejected(self):
        other_question = Question.objects.create(question_text="Another poll", pub_date=timezone.now())
        other_choice = other_question.choice_set.create(choice_text="Other choice")
        self.assertContains(
            self.client.post(self.vote_url, {"choice": other_choice.pk}),
            "You didn&#x27;t select a valid choice.",
        )
        other_choice.refresh_from_db()
        self.assertEqual(other_choice.votes, 0)

    def test_vote_rejects_get(self):
        self.assertEqual(self.client.get(self.vote_url, {"choice": self.choice.pk}).status_code, 405)
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 0)

    def test_vote_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.vote_url, {"choice": self.choice.pk}).status_code, 403)
        page = client.get(reverse("polls:detail", args=[self.question.pk]))
        token = page.cookies["csrftoken"].value
        self.assertEqual(client.post(self.vote_url, {
            "choice": self.choice.pk, "csrfmiddlewaretoken": token,
        }).status_code, 302)

    def test_results_pluralize_and_do_not_add_votes(self):
        self.choice.votes = 2
        self.choice.save()
        self.assertContains(self.client.get(reverse("polls:results", args=[self.question.pk])), "2 votes")
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 2)

    def test_unknown_poll_returns_404(self):
        for route in ("polls:detail", "polls:results"):
            self.assertEqual(self.client.get(reverse(route, args=[999999])).status_code, 404)
        self.assertEqual(self.client.post(reverse("polls:vote", args=[999999])).status_code, 404)

    def test_seed_is_idempotent_and_preserves_votes(self):
        call_command("seed_polls", stdout=StringIO())
        seeded = Choice.objects.exclude(question=self.question).first()
        seeded.votes = 7
        seeded.save()
        count = Question.objects.count(), Choice.objects.count()
        call_command("seed_polls", stdout=StringIO())
        self.assertEqual((Question.objects.count(), Choice.objects.count()), count)
        seeded.refresh_from_db()
        self.assertEqual(seeded.votes, 7)

    def test_recent_publication_excludes_old_and_future_dates(self):
        self.assertTrue(self.question.was_published_recently())
        for delta in (timedelta(days=-2), timedelta(days=1)):
            self.question.pub_date = timezone.now() + delta
            self.assertFalse(self.question.was_published_recently())

    def test_admin_login_and_model_pages(self):
        self.assertEqual(self.client.get(reverse("admin:login")).status_code, 200)
        user = get_user_model().objects.create_superuser(
            username="test-admin", email="admin@example.com", password="test-only-password"
        )
        self.client.force_login(user)
        for model in ("question", "choice"):
            self.assertEqual(self.client.get(reverse(f"admin:polls_{model}_changelist")).status_code, 200)
