"""Shared deterministic FP32 runtime policy for training and readout processes."""

import os
import torch


def configure_runtime(device):
    device = torch.device(device)
    if device.type not in ("cpu", "cuda") or torch.get_default_dtype() != torch.float32:
        raise ValueError("validated runtime requires CPU/CUDA and float32")
    if device.type == "cuda" and os.environ.get("CUBLAS_WORKSPACE_CONFIG") not in (
        ":4096:8",
        ":16:8",
    ):
        raise ValueError("set CUBLAS_WORKSPACE_CONFIG=:4096:8 before CUDA initialization")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    return device
