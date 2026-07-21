"""Command-line smoke test for the pneumonia ensemble."""

from __future__ import annotations

import argparse
import json

from worker.model import PneumoniaEnsemble


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Path to a chest X-ray image")
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"])
    args = parser.parse_args()

    predictor = PneumoniaEnsemble(device=args.device)
    print(json.dumps(predictor.predict(args.image), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
