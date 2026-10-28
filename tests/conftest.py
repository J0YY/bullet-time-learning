import pytest


@pytest.fixture(autouse=True)
def limit_torch_threads():
    import torch

    torch.set_num_threads(1)
