"""Never read or overwrite an operator's runtime routing while running tests."""
import tempfile
from pathlib import Path
from django.test import override_settings
from django.test.runner import DiscoverRunner

class IsolatedRoutingRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.routing_directory = tempfile.TemporaryDirectory()
        self.routing_settings = override_settings(
            MAINTENANCE_ROUTING_PATH=Path(self.routing_directory.name)/"routing.json")
        self.routing_settings.enable()

    def teardown_test_environment(self, **kwargs):
        try:
            self.routing_settings.disable()
            self.routing_directory.cleanup()
        finally:
            super().teardown_test_environment(**kwargs)
