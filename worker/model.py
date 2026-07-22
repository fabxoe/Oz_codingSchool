"""Serving implementation for the pneumonia ensemble artifact.

The bundle contains ten PyTorch state_dict checkpoints:
five ConvNeXt-Tiny folds and five EfficientNet-B0 folds. Their mean
probabilities are converted to the compact feature set used by the original
RidgeClassifier meta model. This is the reproducible model pipeline beneath
the final EXP-132 competition submission; EXP-132 itself is a CSV, not a
separately trained checkpoint.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import BinaryIO

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms


DEFAULT_BUNDLE_DIR = Path(__file__).resolve().parent / "models" / "pneumonia_ensemble_v1"


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_convnext_tiny() -> nn.Module:
    model = models.convnext_tiny(weights=None)
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, 2)
    return model


def build_efficientnet_b0() -> nn.Module:
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    return model


class PneumoniaEnsemble:
    """Load the ten-checkpoint ensemble once and serve repeatable predictions.

    RidgeClassifier has no calibrated probability output. The returned
    ``pneumonia_probability`` is therefore the mean class-1 probability of
    the two five-fold neural ensembles, while ``decision_score`` is the
    actual value used for the final class decision.
    """

    def __init__(
        self,
        bundle_dir: str | Path = DEFAULT_BUNDLE_DIR,
        device: str | torch.device | None = None,
    ) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.device = torch.device(device) if device is not None else select_device()
        self._lock = threading.Lock()

        self.manifest = json.loads(
            (self.bundle_dir / "manifest.json").read_text(encoding="utf-8")
        )
        rank_data = np.load(self.bundle_dir / self.manifest["meta_model"]["rank_reference"])
        self.rank_reference = {"cnx": rank_data["cnx"], "eff": rank_data["eff"]}

        meta = self.manifest["meta_model"]
        self.feature_names = list(meta["features"])
        self.coef = np.asarray(meta["coef"], dtype=np.float64)
        self.intercept = float(meta["intercept"])
        self.threshold = float(meta["decision_threshold"])

        input_config = self.manifest["input"]
        self.transform = transforms.Compose(
            [
                transforms.Resize(tuple(input_config["size"])),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=input_config["normalize_mean"],
                    std=input_config["normalize_std"],
                ),
            ]
        )
        self.models = {
            "cnx": self._load_family("convnext_tiny", build_convnext_tiny),
            "eff": self._load_family("efficientnet_b0", build_efficientnet_b0),
        }

    def _load_family(self, family: str, builder) -> list[nn.Module]:
        loaded = []
        for checkpoint in self.manifest["families"][family]:
            model = builder()
            state_dict = torch.load(
                self.bundle_dir / checkpoint["file"],
                map_location="cpu",
                weights_only=True,
            )
            model.load_state_dict(state_dict, strict=True)
            model.to(self.device)
            model.eval()
            loaded.append(model)
        return loaded

    @staticmethod
    def _open_image(source: str | Path | BinaryIO | Image.Image) -> Image.Image:
        if isinstance(source, Image.Image):
            return source.convert("RGB")
        return Image.open(source).convert("RGB")

    def _family_probabilities(self, family: str, tensor: torch.Tensor) -> np.ndarray:
        probabilities = []
        for model in self.models[family]:
            logits = model(tensor)
            probabilities.append(torch.softmax(logits, dim=1).cpu().numpy())
        return np.mean(probabilities, axis=0)

    def _reference_rank(self, family: str, probability: float) -> float:
        reference = self.rank_reference[family]
        return float(np.searchsorted(reference, probability, side="right") / len(reference))

    @staticmethod
    def _batch_rank(values: np.ndarray) -> np.ndarray:
        """Match pandas rank(pct=True) for a one-dimensional batch."""
        order = np.argsort(values, kind="mergesort")
        sorted_values = values[order]
        ranks = np.empty(len(values), dtype=np.float64)
        start = 0
        while start < len(values):
            end = start + 1
            while end < len(values) and sorted_values[end] == sorted_values[start]:
                end += 1
            average_rank = ((start + 1) + end) / 2.0
            ranks[order[start:end]] = average_rank / len(values)
            start = end
        return ranks

    def _meta_features(
        self,
        cnx: np.ndarray,
        eff: np.ndarray,
        cnx_rank: float | None = None,
        eff_rank: float | None = None,
    ) -> np.ndarray:
        values = {
            "cnx_prob1": float(cnx[1]),
            "eff_prob1": float(eff[1]),
            "cnx_rank": self._reference_rank("cnx", float(cnx[1])) if cnx_rank is None else cnx_rank,
            "eff_rank": self._reference_rank("eff", float(eff[1])) if eff_rank is None else eff_rank,
            "cnx_margin": float(cnx[1] - cnx[0]),
            "eff_margin": float(eff[1] - eff[0]),
            "cnx_uncertainty": float(1.0 - abs(cnx[1] - cnx[0])),
            "eff_uncertainty": float(1.0 - abs(eff[1] - eff[0])),
            "cnx_pred": float(np.argmax(cnx)),
            "eff_pred": float(np.argmax(eff)),
        }
        return np.asarray([values[name] for name in self.feature_names], dtype=np.float64)

    def _format_result(self, cnx: np.ndarray, eff: np.ndarray, features: np.ndarray) -> dict[str, object]:
        decision_score = float(features @ self.coef + self.intercept)
        label = int(decision_score >= self.threshold)
        pneumonia_probability = float((cnx[1] + eff[1]) / 2.0)
        confidence = pneumonia_probability if label == 1 else 1.0 - pneumonia_probability
        return {
            "label": label,
            "is_pneumonia": bool(label),
            "confidence": confidence,
            "pneumonia_probability": pneumonia_probability,
            "decision_score": decision_score,
            "decision_threshold": self.threshold,
            "model": self.manifest["artifact_id"],
            "family_probabilities": {
                "convnext_tiny": float(cnx[1]),
                "efficientnet_b0": float(eff[1]),
            },
        }

    def predict(self, source: str | Path | BinaryIO | Image.Image) -> dict[str, object]:
        """Predict one image.

        The lock prevents concurrent MPS/CUDA calls from competing for the
        same ten resident model instances in an async API process.
        """
        image = self._open_image(source)
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with self._lock, torch.inference_mode():
            cnx = self._family_probabilities("cnx", tensor)[0]
            eff = self._family_probabilities("eff", tensor)[0]

        features = self._meta_features(cnx, eff)
        return self._format_result(cnx, eff, features)

    def predict_batch(
        self,
        sources: list[str | Path | BinaryIO | Image.Image],
        rank_mode: str = "batch",
    ) -> list[dict[str, object]]:
        """Predict a batch using competition-style or service-style ranks.

        ``rank_mode='batch'`` reproduces the competition feature definition by
        ranking probabilities within the supplied batch. It is only meaningful
        for a stable cohort, not for one-image API requests. ``reference`` uses
        the saved OOF empirical distribution used by :meth:`predict`.
        """
        if not sources:
            return []
        if rank_mode not in {"batch", "reference"}:
            raise ValueError("rank_mode must be 'batch' or 'reference'")

        tensors = [self.transform(self._open_image(source)) for source in sources]
        batch = torch.stack(tensors).to(self.device)
        with self._lock, torch.inference_mode():
            cnx = self._family_probabilities("cnx", batch)
            eff = self._family_probabilities("eff", batch)

        if rank_mode == "batch":
            cnx_ranks = self._batch_rank(cnx[:, 1])
            eff_ranks = self._batch_rank(eff[:, 1])
        else:
            cnx_ranks = [None] * len(sources)
            eff_ranks = [None] * len(sources)

        results = []
        for index in range(len(sources)):
            features = self._meta_features(
                cnx[index],
                eff[index],
                cnx_rank=cnx_ranks[index],
                eff_rank=eff_ranks[index],
            )
            results.append(self._format_result(cnx[index], eff[index], features))
        return results
