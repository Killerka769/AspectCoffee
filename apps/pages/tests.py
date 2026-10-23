from django.test import TestCase

from apps.catalog.models import Product, Review, SiteSettings
from apps.pages.models import CommunityPost, CommunityPostComment
from apps.users.models import User


class CommunityCommentModerationTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="Strongpass1",
        )
        self.commenter = User.objects.create_user(
            email="commenter@example.com",
            password="Strongpass1",
        )
        self.post = CommunityPost.objects.create(
            user=self.author,
            title="Тестовая статья",
            text="Текст статьи",
            is_published=True,
        )
        self.client.force_login(self.commenter)

    def test_new_comment_is_hidden_until_admin_approval(self):
        response = self.client.post(
            f"/community/post/{self.post.pk}/comment/",
            {"text": "Комментарий ожидает модерацию"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["pending_moderation"])
        comment = CommunityPostComment.objects.get()
        self.assertFalse(comment.is_approved)

        page = self.client.get("/community/")
        self.assertNotContains(page, comment.text)

        comment.is_approved = True
        comment.save(update_fields=["is_approved"])
        page = self.client.get("/community/")
        self.assertContains(page, comment.text)


class ContentLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="content-lifecycle@example.com",
            password="Strongpass1",
            first_name="Покупатель",
        )
        self.product = Product.objects.create(
            name="Товар для проверки жизненного цикла",
            slug="content-lifecycle-product",
        )
        self.client.force_login(self.user)

    def test_review_is_hidden_until_published_then_appears_on_front(self):
        response = self.client.post(
            "/reviews/create/",
            {"rating": "5", "text": "Отзыв проходит модерацию"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        review = Review.objects.get(pk=response.json()["review_id"])
        self.assertEqual(review.status, Review.STATUS_NEW)
        self.assertFalse(review.is_approved)
        self.assertNotContains(self.client.get("/reviews/"), review.text)

        review.status = Review.STATUS_PUBLISHED
        review.save()
        review.refresh_from_db()
        self.assertTrue(review.is_approved)
        self.assertContains(self.client.get("/reviews/"), review.text)

    def test_retired_recipe_submission_is_not_reintroduced(self):
        response = self.client.post(f"/product/{self.product.slug}/recipe/add/", {"name": "Retired feature"})
        self.assertEqual(response.status_code, 404)

    def test_community_post_visibility_is_controlled_from_admin_flag(self):
        response = self.client.post(
            "/community/",
            {"title": "Публикация жизненного цикла", "text": "Текст публикации"},
        )
        self.assertEqual(response.status_code, 302)
        post = CommunityPost.objects.get(title="Публикация жизненного цикла")
        self.assertTrue(post.is_published)
        self.assertContains(self.client.get("/community/"), post.title)

        post.is_published = False
        post.save(update_fields=["is_published"])
        self.assertNotContains(self.client.get("/community/"), post.title)

        post.is_published = True
        post.save(update_fields=["is_published"])
        self.assertContains(self.client.get("/community/"), post.title)
