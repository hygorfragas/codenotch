#!/usr/bin/env python3
"""Plano de treino do plug. Não chama o treinador sem a aprovação explícita."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "earplug" / "data.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Treino do earplug, bloqueado até a aprovação.")
    parser.add_argument("--i-approve-training", action="store_true")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--device", default="0")
    args = parser.parse_args()
    if not args.i_approve_training:
        print("Treino não iniciado. Ele espera os clipes do Hygor e a flag --i-approve-training.")
        print(f"Quando aprovado: python scripts/train_earplug.py --i-approve-training --epochs {args.epochs}")
        print("Base: YOLOv8m do SH17, classe nova earplug, imgsz 640. Não usa o Colab daqui.")
        return 0
    images = list((ROOT / "earplug" / "images" / "train").glob("*"))
    if not images:
        print("Sem imagens de treino em earplug/images/train. Nada foi enviado para a GPU.", file=sys.stderr)
        return 2
    print(f"Aprovado, mas este ambiente não dispara o treino automaticamente. data={DATA}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
