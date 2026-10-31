"""Shared deterministic FP32 runtime policy for training and readout processes."""

import os
import platform
import subprocess
import torch


def validate_device(device):
    device = torch.device(device)
    if device.type not in ("cpu", "cuda", "mps"):
        raise ValueError("device must be CPU, CUDA or MPS")
    if device.type == "mps" and device.index not in (None, 0):
        raise ValueError("MPS exposes only device zero")
    return device


def device_name(device):
    device = validate_device(device)
    if device.type == "cuda":
        return torch.cuda.get_device_name(device)
    if device.type == "mps":
        # MPS has no get_device_name API. Bind the actual Apple chip, not just arm64.
        return (
            "MPS: "
            + subprocess.check_output(
                ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=5
            ).strip()
        )
    return "cpu"


def mps_runtime():
    return {
        "macos": platform.mac_ver()[0],
        "fallback": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0"),
        "fast_math": os.environ.get("PYTORCH_MPS_FAST_MATH", "0"),
        "prefer_metal": os.environ.get("PYTORCH_MPS_PREFER_METAL", "0"),
    }


def configure_runtime(device):
    device = validate_device(device)
    if torch.get_default_dtype() != torch.float32:
        raise ValueError("supported runtime requires float32")
    if device.type == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS unavailable on this host")
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("this MPS integration supports Apple Silicon Macs only")
        options = mps_runtime()
        if options["fallback"] != "0" or options["fast_math"] != "0":
            raise ValueError(
                "MPS CPU fallback and fast math must be disabled before process startup"
            )
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
        "device_name": device_name(device),
        **({"mps_runtime": mps_runtime()} if device.type == "mps" else {}),
        "threads": torch.get_num_threads(),
        "system": platform.system(),
        "machine": platform.machine(),
        "precision": "float32",
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
    }
