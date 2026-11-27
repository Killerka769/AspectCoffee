from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.blog.models import ArticleComment, BlogPost
from apps.users.models import User


class MobileBlogDetailRegressionTests(TestCase):
    def setUp(self):
        self.post = BlogPost.objects.create(
            title="Мобильная статья",
            slug="mobile-article",
            content="Текст статьи",
            is_published=True,
        )

    def test_breadcrumb_ends_at_blog_and_metadata_share_one_row(self):
        response = self.client.get(self.post.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        breadcrumb = html[html.index("<nav"):html.index("</nav>")]
        self.assertNotIn(self.post.title, breadcrumb)
        self.assertContains(response, self.post.created_at.strftime("%d.%m.%Y"))
        self.assertContains(response, "asp-art__")
        self.assertNotContains(response, "Серия статей")
        self.assertNotContains(response, "asp-art__series")

        with_series = self.client.get(self.post.get_absolute_url() + "?series=missing")
        self.assertEqual(with_series.status_code, 200)

    def test_new_comment_is_hidden_until_approval(self):
        user = User.objects.create_user(email="reader@example.com", password="Strongpass1", first_name="Читатель")
        self.client.force_login(user)
        response = self.client.post(
            f"/blog/{self.post.slug}/comment/",
            {"text": "Комментарий до проверки"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["pending_moderation"])
        comment = ArticleComment.objects.get()
        self.assertFalse(comment.is_approved)
        page = self.client.get(self.post.get_absolute_url())
        self.assertNotContains(page, comment.text)

        comment.is_approved = True
        comment.save(update_fields=["is_approved"])
        page = self.client.get(self.post.get_absolute_url())
        self.assertContains(page, comment.text)

    def test_update_date_is_hidden_for_same_day_and_shown_for_later_day(self):
        response = self.client.get(self.post.get_absolute_url())
        self.assertNotContains(response, "Обновлено")

        BlogPost.objects.filter(pk=self.post.pk).update(
            updated_at=timezone.now() + timedelta(days=1)
        )
        response = self.client.get(self.post.get_absolute_url())
        self.assertContains(response, "Обновлено")

    def test_mobile_index_keeps_cards_inside_viewport_and_active_topic_light(self):
        response = self.client.get("/blog/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "asp-jrn__container")
        self.assertContains(response, "@media")
        self.assertContains(response, self.post.title)
        self.assertNotContains(response, "Серии статей")
        self.assertNotContains(response, "asp-jrn__series")
