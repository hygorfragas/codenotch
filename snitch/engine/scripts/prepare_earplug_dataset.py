#!/usr/bin/env python3
"""Monta a pasta do dataset de plug intra-auricular. Não baixa nada e não treina.

Formato YOLO, uma linha por objeto, coordenadas normalizadas:
    <classe> <centro_x> <centro_y> <largura> <altura>
A classe 0 é earplug. O abafador grande continua sendo ear-mufs do SH17.

Sementes públicas, para rotular depois junto com os clipes do Hygor:
    https://universe.roboflow.com/brage-drnsc/ear-plugs
    https://universe.roboflow.com/willy-alcantara/earplugs-c1kb1
    https://universe.roboflow.com/miniproject-k07dx/manufacturing-hvyyr
    https://universe.roboflow.com/diya-chacko/ppe-ydnu6
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "earplug"


def prepare(out: Path) -> None:
    for split in ("train", "val"):
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
    example = out / "labels" / "train" / "example.txt"
    if not example.exists():
        example.write_text("0 0.620000 0.410000 0.040000 0.050000\n", encoding="utf-8")
    sources = {
        "class": "earplug",
        "format": "yolo-normalized cx cy w h",
        "seeds": [
            "https://universe.roboflow.com/brage-drnsc/ear-plugs",
            "https://universe.roboflow.com/willy-alcantara/earplugs-c1kb1",
            "https://universe.roboflow.com/miniproject-k07dx/manufacturing-hvyyr",
            "https://universe.roboflow.com/diya-chacko/ppe-ydnu6",
        ],
        "note": "Não baixa os conjuntos. O treino espera os clipes locais e a aprovação.",
    }
    (out / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    print(f"Dataset preparado em {out}. Nenhum download e nenhum treino.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara a pasta do plug sem baixar nem treinar.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    prepare(parser.parse_args().out)


if __name__ == "__main__":
    main()
