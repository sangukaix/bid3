from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase


@override_settings(BID3_PUBLIC_WEB=True, CACHES={
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "public-auth-tests"},
})
class PublicAuthTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_existing_short_password_can_still_log_in(self):
        get_user_model().objects.create_user(username="legacy", password="abcd")
        response = self.client.post("/api/auth/login/", {"username": "legacy", "password": "abcd"})
        self.assertEqual(response.status_code, 200)

    def test_login_limit_applies_without_trusting_forwarded_ip(self):
        for index in range(8):
            response = self.client.post("/api/auth/login/", {"username": "missing", "password": "wrong"},
                                        HTTP_X_FORWARDED_FOR=f"192.0.2.{index}")
            self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/auth/login/", {"username": "missing", "password": "wrong"})
        self.assertEqual(response.status_code, 429)

    def test_global_login_limit(self):
        for index in range(60):
            response = self.client.post("/api/auth/login/", {"username": f"missing{index}", "password": "wrong"})
            self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/auth/login/", {"username": "another", "password": "wrong"})
        self.assertEqual(response.status_code, 429)

    def test_public_signup_requires_strong_password(self):
        for password in ["abcd", "123456789", "password"]:
            response = self.client.post("/api/auth/signup/", {
                "username": "newuser", "email": "new@example.test", "password": password, "password_confirm": password,
            })
            self.assertEqual(response.status_code, 400)
            self.assertIn("password", response.data)
        self.assertFalse(get_user_model().objects.filter(username="newuser").exists())
        response = self.client.post("/api/auth/signup/", {
            "username": "newuser", "email": "new@example.test",
            "password": "demo-7K!safe-value", "password_confirm": "demo-7K!safe-value",
        })
        self.assertEqual(response.status_code, 201)

    def test_signup_limit(self):
        for _ in range(10):
            self.assertEqual(self.client.post("/api/auth/signup/", {}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/signup/", {}).status_code, 429)

    @override_settings(BID3_PUBLIC_WEB=False)
    def test_private_api_compatibility(self):
        for _ in range(11):
            self.assertEqual(self.client.post("/api/auth/login/", {}).status_code, 400)
        response = self.client.post("/api/auth/signup/", {
            "username": "localuser", "email": "local@example.test", "password": "abcd", "password_confirm": "abcd",
        })
        self.assertEqual(response.status_code, 201)

    def test_private_data_needs_normal_account_authentication(self):
        for path in ["/api/company-documents/", "/api/company-profile/", "/api/maintenance/routing/",
                     "/api/bids/R26BK01759488/proposal/", "/api/presentation-studio/projects/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
