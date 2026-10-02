import unittest,os,tempfile
from pathlib import Path
from unittest.mock import patch
from security.isolation import initialize_runtime
from adapters.storage.factory import StorageFactory
from adapters.supabase_client import SupabaseClientManager
from ai_engine.gemini_service import get_api_key_candidates,GeminiModelAdapter

class IndependenceTests(unittest.TestCase):
    def test_old_google_credentials_cannot_activate_storage(self):
        for provider in ['google_drive','cloud_storage','s3','saas']:
            with self.assertRaises(ValueError):StorageFactory.get_provider(provider)
    def test_old_gemini_key_is_not_reused(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'AIza_OLD_PROJECT','PROTOCOL_GEMINI_API_KEY':'','ENABLE_EXTERNAL_PROCESSING':'true'}):
            self.assertEqual(get_api_key_candidates(),[''])
    def test_new_gemini_key_requires_explicit_enable(self):
        with patch.dict(os.environ,{'PROTOCOL_GEMINI_API_KEY':'AIza_NEW_PROJECT','ENABLE_EXTERNAL_PROCESSING':'false'}):
            self.assertEqual(get_api_key_candidates(),[''])
    def test_supabase_does_not_reuse_previous_default(self):
        with patch.dict(os.environ,{'SUPABASE_URL':'','SUPABASE_KEY':'','SUPABASE_SERVICE_ROLE_KEY':'','SUPABASE_ANON_KEY':'','ENABLE_EXTERNAL_STORAGE':'false'}):
            manager=SupabaseClientManager();self.assertEqual(manager.url,'');self.assertFalse(manager.is_configured)
    def test_inherited_remote_storage_is_disabled(self):
        with patch.dict(os.environ,{'SUPABASE_URL':'https://example.invalid','SUPABASE_KEY':'old-key','ENABLE_EXTERNAL_STORAGE':'false'}):
            manager=SupabaseClientManager();self.assertIsNone(manager.client);self.assertFalse(manager.is_configured)
    def test_new_runtime_does_not_copy_old_data_or_settings(self):
        original=Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as folder:
                old=Path(folder)/'old';old.mkdir();(old/'.env').write_text('ISOLATION_OLD_MARKER=old\n');(old/'credentials.json').write_text('{}');(old/'institutions_catalog.json').write_text('{}')
                fresh=Path(folder)/'fresh'
                with patch.dict(os.environ,{'PROTOCOL_DATA_DIR':str(fresh),'PROTOCOL_ENV_FILE':''}):
                    os.chdir(old);initialize_runtime();self.assertEqual(Path.cwd(),fresh);self.assertFalse((fresh/'credentials.json').exists());self.assertFalse((fresh/'institutions_catalog.json').exists());self.assertNotIn('ISOLATION_OLD_MARKER',os.environ);self.assertTrue((fresh/'criteria.json').exists())
                os.chdir(original)
        finally:os.chdir(original)

    def test_inherited_vertex_configuration_cannot_select_old_cloud(self):
        with patch.dict(os.environ,{'GOOGLE_GENAI_USE_VERTEXAI':'true','GOOGLE_CLOUD_PROJECT':'OLD_PROJECT'}), patch('ai_engine.gemini_service.genai.Client') as client:
            GeminiModelAdapter('new-explicit-key','model').generate_content('test')
            self.assertIs(client.call_args.kwargs['vertexai'],False)
