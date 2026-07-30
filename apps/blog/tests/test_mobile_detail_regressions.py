from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.blog.models import BlogPost


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
        self.assertContains(response, self.post.created_at.strftime("%d.%m.%y"))
        metadata = html[html.index('class="flex items-center gap-4'):html.index("</div>", html.index('class="flex items-center gap-4'))]
        self.assertIn("icons--viewing-stroke", metadata)
        self.assertIn("icons--time-light", metadata)

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
        self.assertContains(response, "grid-template-columns:minmax(0,1fr)")
        self.assertContains(
            response,
            ".aspect-journal-nav a.active{background:var(--white);border-color:var(--black);color:var(--black)}",
        )
