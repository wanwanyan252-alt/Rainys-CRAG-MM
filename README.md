# CRAG-MM: MULTI-MODAL MULTI-TURN COMPREHENSIVE RAG BENCHMARK
[![arXiv](https://img.shields.io/badge/arXiv-2510.26160-b31b1b.svg)](https://arxiv.org/abs/2510.26160)

> Local development note: this checkout includes project-owned compatibility
> fixes and regression tests for Windows retrieval/evaluation work. See
> [Current handoff](HANDOFF.md) and
> [Local development and recovery](docs/local_development.md) before rebuilding
> the environment. Use the separate [Cloud CUDA runtime](docs/cloud_runtime.md)
> guide for an open-source VLM run.

## Full validation result (2026-11-23)

This checkout now includes a reproducible evaluation of all 1,938 examples in the
official `v0.1.2` single-turn validation split using Llama 3.2 11B Vision Instruct,
the official image/web retrieval indexes, and a DeepSeek Flash comparison judge.

| Split | Count | Correct | Abstain | Wrong | Truthfulness | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| Development (`0–199`) | 200 | 81 | 83 | 36 | 0.2250 | 58.50% |
| Frozen blind (`200–1937`) | 1,738 | 536 | 683 | 519 | 0.0098 | 60.70% |
| Full validation | 1,938 | 617 | 766 | 555 | 0.0320 | 60.47% |

The first 200 examples were used during development; positions 200–1937 were run
once with the strategy frozen and are the primary generalization result. DeepSeek
is a comparison judge, not the benchmark's official `gpt-4o` judge. The complete
methodology, grouped metrics, limitations, artifact hashes, and failure analysis are
in [the full validation report](docs/full_validation_report_2026-11-23.md).

The final competition-oriented iteration adds a 4-bit LoRA adapter, a fast
contact-sheet path, structured visual analysis, deterministic multi-query retrieval,
entity/scope filtering, an independent 22.7M MiniLM cross-encoder, and a locally
calibrated refusal gate. On held-out positions 400–599 it reaches Truthfulness
`0.115` with P95 latency `5.381s` and no 10-second timeout. See the
[final completion report](docs/final_multiquery_reranker_completion_2026-11-25.md).

 [CRAG-MM](https://arxiv.org/abs/2510.26160) is a Comprehensive RAG benchmark for Multi-modal Multi-turn conversations. The benchmark contains a diverse set of (image, question, answer) triplets and visual-based multi-turn conversations across 13 domains, including 6.2K egocentric images designed to emulate wearable captures. The benchmark is designed to encapsulate real-world challenges in wearables AI applications, consisting of various image-quality issues, question types, entity popularity and information dynamism, as well as multi-turn dependencies.

# Table of Contents

- [Dataset Overview](#-dataset-overview)
- [Evaluation](#-evaluation)
- [How to run end-to-end evaluation?](#-how-to-run-end-to-end-evaluation)
- [Example Agents](#-example-agents)
- [Citation](#-citation)
- [License](#license)


# 📊 Dataset Overview

CRAG-MM contains three parts of data: the image set, the QA set, and the contents for retrieval.

The datasets can be accessed as follows:
- **CRAG-MM-2025:** [https://huggingface.co/crag-mm-2025](https://huggingface.co/crag-mm-2025)
- **Single-Turn VQA:** [https://huggingface.co/datasets/crag-mm-2025/crag-mm-single-turn-public](https://huggingface.co/datasets/crag-mm-2025/crag-mm-single-turn-public)
- **Multi-Turn VQA:** [https://huggingface.co/datasets/crag-mm-2025/crag-mm-multi-turn-public](https://huggingface.co/datasets/crag-mm-2025/crag-mm-multi-turn-public)

## 🖼️ Image set
CRAG-MM contains two types of images: egocentric images and normal images. The egocentric images were collected using RayBan Meta Smart Glasses 4 from first-person perspective. The normal images were collected from publicly available images on the web.

## 📝 Question Answer Pairs
CRAG-MM covers 14 domains: Book, Food, General object recognition, Math and science, Nature, Pets, Plants and Gardening, Shopping, Sightseeing, Sports and games, Style and fashion, Text understanding, Vehicles, and Others, representing popular use cases that wearable device users would like to engage with. It also includes 4 types of questions, ranging from simple questions that can be answered based on the image to complex questions that require retrieving multiple sources and synthesizing an answer.

## 📁 Retrieval Contents
To ensure consistent accessibility and fair comparison across methods, we provide all retrieval contents as part of CRAG-MM. These contents span two complementary sources: an image-based corpus and a text-based web corpus.

- Image-based corpus: each entry contains an image and its associated structured attributes (e.g., plant name and species). The corpus consists of 68K images covering 26K entities and captures 93% of all entities referenced in CRAG-MM questions.

- Text-based corpus: webpages are chunked into 512-token segments and embedded using BGE, yielding 2.7M chunks spanning 800K urls. The resulting corpus achieves an estimated 89% recall for CRAG-MM questions, offering broad but imperfect coverage typical of real-world web search.

## 📁 Mock Search APIs
CRAG-MM additionally provides optional search APIs that mirror retrieval interfaces used in practical MM-RAG pipelines. The APIs aim to provide rapid development and reproducible evaluation.

You can download the mock APIs with
```
pip install -U cragmm-search-pipeline
```

[docs/search_api.md](docs/search_api.md) contains the documentations to the mock APIs and the format of the retrieved content. Under [retriever.py](utils/retriever.py) the function `get_rag_context` provides details on how the retrieved content is augmented to the agent. The current implementation of `get_rag_context` serves only as a baseline guidence to how the retrieval content may be integrated.


# 📏 Evaluation

## Single-Turn VQA
For each question in the evaluation set, we score the answer with:
- Correct: Score 1
- Missing ("I don't know"): Score 0
- Hallucinated (wrong or irrelevant): Score -1

We then use Truthfulness as the average score from all examples in the evaluation set for a given MM-RAG system.

## Multi-Turn VQA
We adapt the method in [1], which is closest to the information-seeking flavor of conversations. In particular, we stop a conversation when the answers in two consecutive turns are wrong and consider answers to all remaining questions in the same conversation as missing–mimicking the behavior of real users when they lose trust or feel frustrated after repeated failures. We then take the average score of all multi-turn conversations.

[1] Bai et al., "MT-Bench-101: A Fine-Grained Benchmark for Evaluating Large Language Models in Multi-Turn Dialogues". Available at: https://aclanthology.org/2024.acl-long.401/

## Auto-evaluation
See [evaluation/README.md](evaluation/README.md) for detailed documentation on the evaluation framework, metrics, output formats, and usage examples.


# 💻 How to run end-to-end evaluation?

1. Install specific dependencies

```bash
pip install -r requirements.txt
```

2. Please follow the instructions in [example_agents/README.md](example_agents/README.md) for instructions and examples on how to write your own agents.

3. After writing your own agent(s), update `example_agents/user_config.py`.

   For example, in `example_agents/user_config.py`, specify `LlamaAgent` to call the Llama-3.2-11B-Vision-Instruct model:

```python
from agents.open_source_model_agents import LlamaAgent

MODEL_KEYWORD_TO_AGENT = {
    "llama": LlamaAgent,
}
```

4. Test your agent locally using `python local_evaluation.py`. This script will run answer generation and auto-evaluation.


# 🏁 Example Agents

We provide example multi-modal RAG agents for demonstration purposes. See details in [Available Agents](example_agents/README.md#available-agents).



# 📎 Citation
If you find this work useful in your research, please consider citing our paper:

```bibtex
@article{wang2025cragmm,
  title={CRAG-MM: Multi-modal Multi-turn Comprehensive RAG Benchmark}, 
  author={Jiaqi Wang and Xiao Yang and Kai Sun and Parth Suresh and Sanat Sharma and Adam Czyzewski and Derek Andersen and Surya Appini and Arkav Banerjee and Sajal Choudhary and Shervin Ghasemlou and Ziqiang Guan and Akil Iyer and Haidar Khan and Lingkun Kong and Roy Luo and Tiffany Ma and Zhen Qiao and David Tran and Wenfang Xu and Skyler Yeatman and Chen Zhou and Gunveer Gujral and Yinglong Xia and others},
  year={2025},
  journal={arXiv preprint arXiv:2510.26160},
  url={https://arxiv.org/abs/2510.26160}
}
```

# License
This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)](). This license permits sharing and adapting the work, provided it's not used for commercial purposes and appropriate credit is given. For a quick overview, visit [Creative Commons License](https://creativecommons.org/licenses/by-nc/4.0/).
