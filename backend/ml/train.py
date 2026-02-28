"""
Training script for the EliteJumpModel.
Uses triplet margin loss on (anchor_elite, positive_elite, negative_sub_elite) triplets.

Usage:
    cd backend
    python -m ml.train --poses-dir ../data/poses --epochs 100 --batch-size 16
"""

import argparse
import os
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.elite_jump_model import EliteJumpModel
from ml.dataset import PoseSequenceDataset

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


def train(poses_dir: str, epochs: int = 100, batch_size: int = 16, lr: float = 1e-4):
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    model = EliteJumpModel(embedding_dim=512).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    criterion = nn.TripletMarginLoss(margin=0.3, p=2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    train_ds = PoseSequenceDataset(poses_dir, split="train")
    val_ds = PoseSequenceDataset(poses_dir, split="val")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2)

    best_val_loss = float("inf")

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for anchor, positive, negative in train_loader:
            anchor = anchor.to(device)
            positive = positive.to(device)
            negative = negative.to(device)

            optimizer.zero_grad()
            emb_a = model(anchor)
            emb_p = model(positive)
            emb_n = model(negative)
            loss = criterion(emb_a, emb_p, emb_n)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        scheduler.step()
        avg_train_loss = total_loss / max(len(train_loader), 1)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for anchor, positive, negative in val_loader:
                anchor, positive, negative = anchor.to(device), positive.to(device), negative.to(device)
                loss = criterion(model(anchor), model(positive), model(negative))
                val_loss += loss.item()
        avg_val_loss = val_loss / max(len(val_loader), 1)

        print(f"Epoch {epoch:3d}/{epochs}  train_loss={avg_train_loss:.4f}  val_loss={avg_val_loss:.4f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            ckpt_path = CHECKPOINT_DIR / "elite_model_best.pt"
            torch.save(model.state_dict(), ckpt_path)
            print(f"  ✓ Saved best checkpoint → {ckpt_path}")

    # Always save final
    torch.save(model.state_dict(), CHECKPOINT_DIR / "elite_model_v1.pt")
    print("Training complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train EliteJumpModel")
    parser.add_argument("--poses-dir", default="../data/poses")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    train(args.poses_dir, args.epochs, args.batch_size, args.lr)
