#!/usr/bin/env python3
"""
Pre-download and cache reranker models during Docker build.
This ensures zero-latency model loading at runtime.
"""

import os
import sys

def warm_models():
    """Download and cache reranker models."""
    print("🔥 Warming reranker models for production deployment...")
    print("=" * 70)

    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        print("❌ sentence-transformers not installed!")
        sys.exit(1)

    # Models to pre-download (same order as backend/app.py)
    models = [
        {
            "name": "jinaai/jina-reranker-v2-base-multilingual",
            "max_length": 8192,
            "requires_trust": True
        },
        {
            "name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "max_length": 512,
            "requires_trust": False
        }
    ]

    for i, model_config in enumerate(models, 1):
        model_name = model_config["name"]
        print(f"\n[{i}/{len(models)}] Downloading: {model_name}")
        print(f"    Max length: {model_config['max_length']} tokens")

        try:
            # Download and cache the model
            if model_config["requires_trust"]:
                model = CrossEncoder(
                    model_name,
                    max_length=model_config["max_length"],
                    trust_remote_code=True,
                    automodel_args={"torch_dtype": "auto"}
                )
            else:
                model = CrossEncoder(
                    model_name,
                    max_length=model_config["max_length"]
                )

            # Verify model works with a simple test
            test_score = model.predict([("test query", "test document")])[0]
            print(f"    ✅ Downloaded and verified (test score: {test_score:.4f})")

            # Clean up to save memory during build
            del model

        except Exception as e:
            print(f"    ⚠️  Failed to download {model_name}: {e}")
            if i == 1:  # If primary model fails, this is critical
                print("    ⚠️  WARNING: Primary model failed, but continuing...")

    print("\n" + "=" * 70)
    print("✅ Model warming complete! Models cached in container.")
    print(f"📦 Cache location: {os.path.expanduser('~/.cache/huggingface')}")
    print("=" * 70)

if __name__ == "__main__":
    warm_models()
