"""The per-link CNN, the four fusion modes and the heads: shapes, sharing, size, link dropout."""

from __future__ import annotations

import torch
import pytest

# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# from pipeline.retired.models.fusion import FUSION_MODES, PRIMARY_FUSION, build_fusion, fused_dim, link_keep_mask
from pipeline.constrained.heads import CellHead, IDHead, PositionHead, cell_loss, id_loss, position_error, position_loss
from pipeline.constrained.link_cnn import LinkCNN, encode_links

B, N, T, S = 4, 3, 300, 107


def _links(seed: int = 0) -> torch.Tensor:
    return torch.randn(B, N, 1, T, S, generator=torch.Generator().manual_seed(seed))


def test_the_encoder_is_modest_and_embeds_a_window() -> None:
    e = LinkCNN()
    assert 50_000 <= e.n_parameters() <= 150_000, f"{e.n_parameters()} parameters: roughly 100k, not a ResNet"
    assert e(torch.zeros(2, 1, T, S)).shape == (2, 64)
    with pytest.raises(ValueError):
        e(torch.zeros(2, 3, T, S))


def test_one_encoder_serves_all_three_links() -> None:
    e = LinkCNN().eval()
    z = encode_links(e, _links())
    assert z.shape == (B, N, 64)
    single = torch.stack([e(_links()[:, i]) for i in range(N)], dim=1)
    assert torch.allclose(z, single, atol=1e-5), "folding links into the batch is the same as encoding each"
    assert sum(p.numel() for p in e.parameters()) == LinkCNN().n_parameters(), "no per-link parameters exist"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# @pytest.mark.parametrize("mode", FUSION_MODES)
# def test_every_fusion_mode_accepts_the_same_input_and_returns_logits(mode: str) -> None:
#     enc = LinkCNN(in_channels=N if mode == "early_stack" else 1)
#     model = build_fusion(mode, enc, IDHead(fused_dim(mode, 64), 8)).eval()
#     out = model(_links())
#     assert out.shape == (B, 8)
#     feats = model.features(_links())
#     assert feats.shape == (B, fused_dim(mode, 64))
#     assert PRIMARY_FUSION == "feature_concat"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_late_fusion_averages_probabilities_and_returns_log_probabilities() -> None:
#     model = build_fusion("late", LinkCNN(), IDHead(64, 8)).eval()
#     out = model(_links())
#     assert torch.allclose(out.exp().sum(1), torch.ones(B), atol=1e-4)


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_link_mask_gives_the_link_count_curve_for_free() -> None:
#     model = build_fusion("late", LinkCNN(), IDHead(64, 8)).eval()
#     x = _links()
#     one = model(x, mask=torch.tensor([[1, 0, 0]] * B, dtype=torch.float32))
#     only_first = torch.log_softmax(model.head(model.encoder(x[:, 0])), dim=-1)
#     assert torch.allclose(one, only_first, atol=1e-4), "masking to one link is that link's own prediction"


# RETIRED 2026-10-01: commented out with pipeline/retired/ and the old scripts, deleted that day; the code it needed is at git tag tracking-final-2026-10-01.
# def test_link_dropout_only_in_training_and_never_drops_every_link() -> None:
#     g = torch.Generator().manual_seed(3)
#     torch.manual_seed(3)
#     keep = link_keep_mask(2000, 3, 0.3, training=True, device=torch.device("cpu"))
#     assert 0.6 < keep.mean().item() < 0.8 and (keep.sum(1) >= 1).all()
#     assert link_keep_mask(5, 3, 0.3, training=False, device=torch.device("cpu")).all()
#     with pytest.raises(ValueError):
#         build_fusion("early_stack", LinkCNN(in_channels=1), IDHead(64, 8))


def test_heads_and_losses() -> None:
    x = torch.randn(B, 64)
    assert IDHead(64, 8)(x).shape == (B, 8) and CellHead(64)(x).shape == (B, 25) and PositionHead(64)(x).shape == (B, 2)
    assert id_loss(torch.zeros(B, 8), torch.zeros(B, dtype=torch.long)).item() == pytest.approx(torch.log(torch.tensor(8.0)).item(), rel=1e-4)
    assert cell_loss(torch.zeros(B, 25), torch.zeros(B, dtype=torch.long)).item() > 0
    p, t = torch.tensor([[0.0, 0.0], [3.0, 4.0]]), torch.zeros(2, 2)
    assert torch.allclose(position_error(p, t), torch.tensor([0.0, 5.0])) and position_loss(p, t).item() > 0
