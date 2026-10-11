"""
Unit tests for AI provider fallback.
Run with: python -m unittest discover tests
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_recommender import AIRecommender, choose_github_model, choose_groq_model  # noqa: E402


WEATHER = {
    'hourly_data': [
        {'temperature': 5.0, 'humidity': 80, 'wind_speed': 2.0,
         'precipitation': 1.0, 'rain': 1.0, 'snow': 0.0, 'condition': 'Rain'}
        for _ in range(10)
    ]
}


def failing(*args, **kwargs):
    raise Exception("service unavailable")


class ProviderFallbackTest(unittest.TestCase):
    def test_falls_back_to_groq_when_github_models_fails(self):
        rec = AIRecommender(groq_api_key='g', github_token='t')
        rec._generate_with_github_models = failing
        rec._generate_with_groq = lambda *args: "Wear a raincoat."
        self.assertEqual(rec.generate_recommendation(WEATHER), "Wear a raincoat.")

    def test_rule_based_when_all_providers_fail(self):
        rec = AIRecommender(groq_api_key='g', github_token='t')
        rec._generate_with_github_models = failing
        rec._generate_with_groq = failing
        result = rec.generate_recommendation(WEATHER)
        self.assertIn("jacket", result)
        self.assertIn("umbrella", result)

    def test_rule_based_when_only_provider_fails(self):
        rec = AIRecommender(groq_api_key='g')
        rec._generate_with_groq = failing
        self.assertTrue(rec.generate_recommendation(WEATHER))


class FakeGroqClient:
    """Mimics the groq SDK; rejects the retired model with Groq's real 404 error text."""
    calls = []

    def __init__(self, api_key):
        self.chat = self
        self.completions = self

    def create(self, messages, model, temperature, max_tokens):
        FakeGroqClient.calls.append(model)
        if model == 'llama-3.1-8b-instant':
            raise Exception("Error code: 404 - {'error': {'message': 'The model `llama-3.1-8b-instant` "
                            "does not exist or you do not have access to it.', 'code': 'model_not_found'}}")
        message = type('Message', (), {'content': f"Advice from {model}"})
        choice = type('Choice', (), {'message': message})
        return type('Completion', (), {'choices': [choice]})


class GroqModelFallbackTest(unittest.TestCase):
    def setUp(self):
        FakeGroqClient.calls = []
        self.groq_module = patch.dict(sys.modules, {'groq': type(sys)('groq')})
        self.groq_module.start()
        sys.modules['groq'].Groq = FakeGroqClient

    def tearDown(self):
        self.groq_module.stop()

    @patch.dict(os.environ, {}, clear=True)
    @patch('ai_recommender.fetch_api_data', return_value={'data': [
        {'id': 'whisper-large-v3', 'active': True},
        {'id': 'llama-3.3-70b-versatile', 'active': True},
        {'id': 'llama-4-instant', 'active': True},
    ]})
    def test_switches_to_available_model_when_retired(self, _):
        rec = AIRecommender(groq_api_key='g')
        self.assertEqual(rec.generate_recommendation(WEATHER), "Advice from llama-4-instant")
        self.assertEqual(FakeGroqClient.calls, ['llama-3.1-8b-instant', 'llama-4-instant'])
        self.assertEqual(rec.groq_model, 'llama-4-instant')

    @patch.dict(os.environ, {'GROQ_MODEL': 'my-model'})
    def test_groq_model_env_override(self):
        rec = AIRecommender(groq_api_key='g')
        self.assertEqual(rec.generate_recommendation(WEATHER), "Advice from my-model")


class FakeResponse:
    def __init__(self, status_code, body, content_type='application/json'):
        self.status_code = status_code
        self.ok = status_code < 400
        self.body = body
        self.text = str(body)
        self.headers = {'Content-Type': content_type}

    def json(self):
        if not isinstance(self.body, dict):
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self.body


def completion(text):
    return FakeResponse(200, {'choices': [{'message': {'content': text}}]})


class GitHubModelsTest(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch('ai_recommender.requests.post', return_value=completion(" Wear a coat. "))
    def test_github_models_is_first_provider(self, post):
        rec = AIRecommender(groq_api_key='g', github_token='t')
        rec._generate_with_groq = failing
        self.assertEqual(rec.generate_recommendation(WEATHER), "Wear a coat.")
        body = post.call_args.kwargs['json']
        self.assertEqual(body['model'], 'openai/gpt-4.1-mini')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer t')

    @patch.dict(os.environ, {}, clear=True)
    @patch('ai_recommender.fetch_api_data', return_value=[
        {'id': 'openai/text-embedding-3-small', 'supported_output_modalities': ['embeddings']},
        {'id': 'meta/llama-4-scout', 'supported_output_modalities': ['text']},
        {'id': 'openai/gpt-5-mini', 'supported_output_modalities': ['text']},
    ])
    @patch('ai_recommender.requests.post', side_effect=[
        FakeResponse(400, {'error': {'code': 'unknown_model', 'message': 'Unknown model: openai/gpt-4.1-mini'}}),
        completion("Wear layers."),
    ])
    def test_switches_model_when_retired(self, post, _):
        rec = AIRecommender(github_token='t')
        self.assertEqual(rec.generate_recommendation(WEATHER), "Wear layers.")
        self.assertEqual(rec.github_model, 'openai/gpt-5-mini')

    @patch.dict(os.environ, {}, clear=True)
    @patch('ai_recommender.requests.post', return_value=FakeResponse(429, {'error': 'rate limited'}))
    def test_falls_back_to_groq_on_error(self, _):
        rec = AIRecommender(groq_api_key='g', github_token='t')
        rec._generate_with_groq = lambda *args: "Groq advice"
        self.assertEqual(rec.generate_recommendation(WEATHER), "Groq advice")

    @patch.dict(os.environ, {'GITHUB_MODELS_MODEL': 'openai/o3-mini'})
    @patch('ai_recommender.fetch_api_data')
    @patch('ai_recommender.requests.post', return_value=FakeResponse(400, {'error': {
        'code': 'unsupported_parameter',
        'message': "Unsupported parameter: 'max_tokens' is not supported with this model."}}))
    def test_other_model_errors_do_not_switch_model(self, _, catalog):
        rec = AIRecommender(groq_api_key='g', github_token='t')
        rec._generate_with_groq = lambda *args: "Groq advice"
        self.assertEqual(rec.generate_recommendation(WEATHER), "Groq advice")
        catalog.assert_not_called()
        self.assertEqual(rec.github_model, 'openai/o3-mini')

    @patch.dict(os.environ, {}, clear=True)
    @patch('ai_recommender.requests.post', return_value=FakeResponse(200, 'OK', 'text/plain'))
    def test_non_json_response_reports_what_came_back(self, _):
        # Seen in production: HTTP 200 with a plain-text "OK" body
        rec = AIRecommender(github_token='t')
        with self.assertRaisesRegex(Exception, "HTTP 200, text/plain.*'OK'"):
            rec._generate_with_github_models(WEATHER)

    def test_choose_github_model(self):
        self.assertEqual(choose_github_model(['meta/llama-4', 'openai/gpt-5-mini']), 'openai/gpt-5-mini')
        self.assertEqual(choose_github_model(['meta/llama-4']), 'meta/llama-4')


class ChooseGroqModelTest(unittest.TestCase):
    def test_preference_order(self):
        self.assertEqual(choose_groq_model(['qwen-3', 'llama-3.3-70b']), 'llama-3.3-70b')
        # Seen in production: with no Llama models left, alphabetical order picked allam-2-7b
        self.assertEqual(choose_groq_model(['allam-2-7b', 'openai/gpt-oss-20b', 'qwen/qwen3-32b']),
                         'openai/gpt-oss-20b')
        self.assertEqual(choose_groq_model(['qwen-3']), 'qwen-3')
        self.assertIsNone(choose_groq_model([]))


if __name__ == '__main__':
    unittest.main()
