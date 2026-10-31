#!/usr/bin/env python3
"""Execute a bounded complete-pass/tail audit; never authorizes pilot training."""

import argparse
import json
import torch
from bullet_time.cli import read_config
from bullet_time.loading.manifest import Corpus
from bullet_time.models.video import ModelConfig
from bullet_time.training.runner import TrainConfig
from bullet_time.training.tail_audit import audit_tail_pass

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--manifest", required=True)
p.add_argument("--model-config", required=True)
p.add_argument("--training-config", required=True)
p.add_argument("--output", required=True)
p.add_argument("--threads", type=int, default=4)
a = p.parse_args()
if a.threads < 1:
    p.error("--threads must be positive")
torch.set_num_threads(a.threads)
model = read_config(a.model_config, ModelConfig)
result = audit_tail_pass(
    Corpus(a.manifest, image_size=model.image_size),
    model,
    read_config(a.training_config, TrainConfig),
    a.output,
)
print(json.dumps({k: v for k, v in result.items() if k != "conditions"}, indent=2))
