import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import vision_shoe_test as vision


class ApiIdentityTests(unittest.TestCase):
    def test_api_result_is_validated_and_applied(self) -> None:
        catalog, references = vision.load_shoe_catalog(
            vision.Path("shoe_assets.json"), vision.Path("shoe_references")
        )
        candidates = [
            {
                "center_px": [100.0, 100.0],
                "bbox_px": [50, 50, 100, 100],
                "shoe_id": None,
                "pair_id": None,
                "side": "unknown",
                "identity_confidence": None,
            }
        ]
        response_json = json.dumps(
            {
                "results": [
                    {
                        "candidate_index": 1,
                        "shoe_id": "white_pair_object1",
                        "confidence": 0.91,
                        "reason": "visual match",
                    }
                ]
            }
        )
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response_json))]
        )
        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-key"}), patch("openai.OpenAI") as client_class:
            client_class.return_value.chat.completions.create.return_value = fake_response
            vision.identify_candidates_with_api(
                np.zeros((200, 200, 3), dtype=np.uint8),
                candidates,
                catalog,
                references,
                "kimi-k3",
                "https://api.moonshot.ai/v1",
                0.60,
                4,
            )

        self.assertEqual(candidates[0]["shoe_id"], "white_pair_object1")
        self.assertEqual(candidates[0]["pair_id"], "white_converse_pair")
        self.assertEqual(candidates[0]["side"], "right")
        self.assertEqual(candidates[0]["identity_confidence"], 0.91)
        client_class.assert_called_once_with(api_key="test-key", base_url="https://api.moonshot.ai/v1")
        request = client_class.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], "kimi-k3")
        self.assertEqual(request["response_format"]["type"], "json_schema")


if __name__ == "__main__":
    unittest.main()
