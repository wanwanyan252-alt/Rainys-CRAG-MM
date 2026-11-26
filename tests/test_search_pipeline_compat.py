import unittest
from unittest.mock import MagicMock, patch

from utils.search_pipeline_compat import UnifiedSearchPipeline


class SearchPipelineCompatibilityTests(unittest.TestCase):
    @patch("utils.search_pipeline_compat.Pipeline.__init__", return_value=None)
    @patch("utils.search_pipeline_compat.CragMockWeb")
    @patch("utils.search_pipeline_compat.AutoTokenizer")
    @patch("utils.search_pipeline_compat.AutoModel")
    @patch("utils.search_pipeline_compat.CLIPModel")
    def test_web_only_does_not_load_clip(
        self,
        clip_model,
        auto_model,
        auto_tokenizer,
        crag_mock_web,
        pipeline_init,
    ):
        text_model = MagicMock()
        text_model.to.return_value = text_model
        auto_model.from_pretrained.return_value = text_model

        search = UnifiedSearchPipeline(
            image_model_name=None,
            image_hf_dataset_id=None,
            text_model_name="text-model",
            web_hf_dataset_id="web-index",
        )

        clip_model.from_pretrained.assert_not_called()
        self.assertTrue(search.web_search)
        self.assertFalse(search.image_search)
        self.assertIn("web_model_load_seconds", search.timings)
        self.assertIn("web_index_open_seconds", search.timings)
        self.assertIn("total_init_seconds", search.timings)
        pipeline_init.assert_called_once()
        self.assertIs(pipeline_init.call_args.kwargs["model"], text_model)

    @patch("utils.search_pipeline_compat.Pipeline.__init__", return_value=None)
    @patch("utils.search_pipeline_compat.CragImageKG")
    @patch("utils.search_pipeline_compat.CLIPProcessor")
    @patch("utils.search_pipeline_compat.CLIPModel")
    @patch("utils.search_pipeline_compat.AutoModel")
    def test_image_only_does_not_load_text_model(
        self,
        auto_model,
        clip_model,
        clip_processor,
        image_kg,
        pipeline_init,
    ):
        vision_model = MagicMock()
        vision_model.to.return_value = vision_model
        clip_model.from_pretrained.return_value = vision_model
        image_kg.return_value.vector_db = MagicMock()

        search = UnifiedSearchPipeline(
            image_model_name="image-model",
            image_hf_dataset_id="image-index",
            text_model_name=None,
            web_hf_dataset_id=None,
        )

        auto_model.from_pretrained.assert_not_called()
        self.assertFalse(search.web_search)
        self.assertTrue(search.image_search)
        self.assertIn("image_model_load_seconds", search.timings)
        self.assertIn("image_index_open_seconds", search.timings)
        self.assertIs(pipeline_init.call_args.kwargs["model"], vision_model)

    def test_rejects_disabled_search_modes(self):
        with self.assertRaisesRegex(ValueError, "At least one"):
            UnifiedSearchPipeline(
                image_model_name=None,
                image_hf_dataset_id=None,
                text_model_name=None,
                web_hf_dataset_id=None,
            )


if __name__ == "__main__":
    unittest.main()
