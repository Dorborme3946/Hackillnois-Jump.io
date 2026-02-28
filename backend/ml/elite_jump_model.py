"""
Elite Jumper CV Model — skeleton sequence → form embedding.
Architecture: Spatial joint encoder (per-frame) + GRU temporal encoder → 512-d embedding.
Compared against elite gallery embeddings via cosine similarity.
"""

import torch
import torch.nn as nn
import numpy as np

from cv.pose_extractor import KEYPOINT_NAMES


class SpatialJointEncoder(nn.Module):
    """Per-frame spatial encoder — learns joint relationships from flattened keypoints."""

    def __init__(self, in_channels: int = 3, hidden: int = 64):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(17 * in_channels, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, hidden),
            nn.ReLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, 17, 3)
        B, T, J, C = x.shape
        x = x.view(B, T, J * C)
        return self.fc(x)  # (B, T, hidden)


class TemporalEncoder(nn.Module):
    """Bidirectional GRU over time to capture movement dynamics."""

    def __init__(self, input_size: int = 64, hidden_size: int = 256, num_layers: int = 2):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.3,
        )
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, input_size)
        out, _ = self.gru(x)              # (B, T, hidden*2)
        out = out.permute(0, 2, 1)        # (B, hidden*2, T)
        out = self.pool(out).squeeze(-1)  # (B, hidden*2)
        return out


class EliteJumpModel(nn.Module):
    """
    Full model: skeleton sequence → normalized form embedding.
    Compare to elite gallery using cosine similarity scaled to 0–99.
    """

    def __init__(self, embedding_dim: int = 512):
        super().__init__()
        self.spatial = SpatialJointEncoder(in_channels=3, hidden=64)
        self.temporal = TemporalEncoder(input_size=64, hidden_size=256)
        self.head = nn.Sequential(
            nn.Linear(512, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, 17, 3)
        spatial_feats = self.spatial(x)           # (B, T, 64)
        temporal_feats = self.temporal(spatial_feats)  # (B, 512)
        embedding = self.head(temporal_feats)     # (B, embedding_dim)
        return nn.functional.normalize(embedding, dim=-1)


class EliteGallery:
    """
    Pre-computed embeddings for elite jumpers.
    Loaded from a .pt file at inference time.
    """

    def __init__(self, model: EliteJumpModel, gallery_path: str):
        self.model = model
        # gallery_embeddings: dict[str, Tensor(1, 512)]
        self.gallery_embeddings: dict = torch.load(gallery_path, map_location="cpu")

    def compute_similarity(self, user_sequence: np.ndarray) -> dict:
        """
        Args:
            user_sequence: (T, 17, 3) normalized keypoint array
        Returns:
            dict mapping elite athlete name → similarity score (0–99)
        """
        self.model.eval()
        with torch.no_grad():
            x = torch.tensor(user_sequence, dtype=torch.float32).unsqueeze(0)
            user_emb = self.model(x)  # (1, 512)

        scores = {}
        for name, elite_emb in self.gallery_embeddings.items():
            sim = nn.functional.cosine_similarity(
                user_emb, elite_emb.unsqueeze(0)
            ).item()
            # Scale cosine sim [-1, 1] → [0, 99]
            scores[name] = round((sim + 1) / 2 * 99, 1)

        return scores

    def overall_elite_score(self, user_sequence: np.ndarray) -> float:
        """Return the best (max) similarity score across all elite embeddings."""
        if not self.gallery_embeddings:
            return 0.0
        scores = self.compute_similarity(user_sequence)
        return max(scores.values()) if scores else 0.0
