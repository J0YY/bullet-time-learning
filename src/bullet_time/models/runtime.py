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


def runtime_provenance(device):
    """Bind the executing consumer, not merely its older pretrained checkpoint."""
    import importlib.metadata
    import platform
    from bullet_time.training.runner import code_identity

    device = torch.device(device)
    return {
        "source_sha256": code_identity(),
        "python_version": platform.python_version(),
        "torch_version": str(torch.__version__),
        "numpy_version": importlib.metadata.version("numpy"),
        "pillow_version": importlib.metadata.version("Pillow"),
        "timm_version": importlib.metadata.version("timm"),
        "device": str(device),
        "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu",
        "threads": torch.get_num_threads(),
        "system": platform.system(),
        "machine": platform.machine(),
        "precision": "float32",
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
    }
