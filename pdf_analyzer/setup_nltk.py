#!/usr/bin/env python3
"""
Run this script once to download required NLTK data
"""

import nltk
import os


def setup_nltk_data():
    """Download all required NLTK data"""
    try:
        # Set NLTK data path to a local directory
        nltk_data_dir = os.path.join(os.path.dirname(__file__), "nltk_data")
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.data.path.append(nltk_data_dir)

        # Download required data
        datasets = [
            "punkt",
            "stopwords",
            "averaged_perceptron_tagger",
            "maxent_ne_chunker",
            "words",
        ]

        for dataset in datasets:
            try:
                print(f"Downloading {dataset}...")
                nltk.download(dataset, download_dir=nltk_data_dir)
                print(f"✓ {dataset} downloaded successfully")
            except Exception as e:
                print(f"✗ Failed to download {dataset}: {e}")

        print("\nNLTK setup complete!")

    except Exception as e:
        print(f"Setup failed: {e}")


if __name__ == "__main__":
    setup_nltk_data()
