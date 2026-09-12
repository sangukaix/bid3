import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from maintenance.routing import defaults, save_config, read_config
from bids.services.llm import model_selection, cloud_options
class MaintenanceTests(APITestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.override=override_settings(MAINTENANCE_ROUTING_PATH=Path(self.temp.name)/"routing.json")
  self.override.enable()
  self.addCleanup(self.override.disable);self.addCleanup(self.temp.cleanup)
  self.user=get_user_model().objects.create_user(username="ordinary",password="testpass")
  self.admin=get_user_model().objects.create_user(username="operator",password="testpass",is_staff=True)
 def test_anonymous_and_ordinary_cannot_read_or_write(self):
  self.assertIn(self.client.get("/api/maintenance/routing/").status_code,[401,403])
  self.client.force_authenticate(self.user)
  for response in [self.client.get("/api/maintenance/routing/"),self.client.put("/api/maintenance/routing/",defaults(),format="json"),self.client.get("/api/maintenance/status/")]:
   self.assertEqual(response.status_code,403)
  self.assertIsNone(read_config())
 def test_local_save_routes_immediately_and_blocks_cloud(self):
  self.client.force_authenticate(self.admin)
  config=defaults();config["routes"]["ANALYSIS"]["model"]="gemma4:26b"
  response=self.client.put("/api/maintenance/routing/",config,format="json")
  self.assertEqual(response.status_code,200)
  self.assertEqual(model_selection("ANALYSIS","unused"),("ollama","gemma4:26b"))
  with self.assertRaises(ValueError):cloud_options()
  self.assertNotIn("OPENAI_API_KEY",response.content.decode())
 def test_local_rejects_cloud_without_overwriting(self):
  save_config(defaults(),"operator")
  config=defaults();config["routes"]["PROPOSAL"]={"provider":"openai","model":"gpt-4o-mini"}
  self.client.force_authenticate(self.admin)
  self.assertEqual(self.client.put("/api/maintenance/routing/",config,format="json").status_code,400)
  self.assertEqual(read_config()["mode"],"local")
 def test_hybrid_selects_only_chosen_role_and_preserves_keyword(self):
  config=defaults();config["mode"]="hybrid";config["routes"]["PROPOSAL"]={"provider":"openai","model":"test-model"}
  save_config(config,"operator")
  self.assertEqual(model_selection("PROPOSAL","unused"),("openai","test-model"))
  self.assertEqual(model_selection("CHAT","unused")[0],"ollama")
  from bids.services.rag.keyword_store import search_mode
  self.assertEqual(search_mode(),"keyword")
 def test_corrupt_config_fails_closed(self):
  from maintenance.routing import config_path
  config_path().write_text("{bad",encoding="utf-8")
  with self.assertRaises(ValueError):model_selection("CHAT","unused")
 @patch("maintenance.views.requests.get")
 def test_status_checks_ollama_without_inference(self,get):
  get.return_value.json.return_value={"models":[{"name":"qwen3:14b"}]}
  self.client.force_authenticate(self.admin)
  response=self.client.get("/api/maintenance/status/")
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.data["models"],["qwen3:14b"])
  self.assertTrue(get.call_args.args[0].endswith("/api/tags"))
