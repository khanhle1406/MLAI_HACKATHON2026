"""Dempster-Shafer evidential fusion for DataGuard.

Adapted from AutoCSV-LED research implementation (src/evidence/fusion.py).
Frame: Omega = {ERROR, CLEAN}

Key concepts:
  - m(ERROR): mass supporting error
  - m(CLEAN): mass supporting validity
  - m(Omega): unresolved ignorance (neither error nor clean)
  - K: conflict between evidence sources

Combination rules:
  - Dempster (sum weights): for distinct/independent sources
  - Cautious (max weights): for non-distinct sources within same family
  - Family rule: cautious within family, Dempster across families

INVARIANT: D-S fusion quantifies uncertainty — it does NOT make decisions.
The Autonomy Gate consumes fusion output.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPS = 1e-6
W_MAX = -np.log(EPS)


def weight(s: np.ndarray | float) -> np.ndarray:
    """Convert support strength s in [0, 1) to weight-of-evidence w = -ln(1-s)."""
    s = np.clip(np.asarray(s, dtype=float), 0.0, 1.0 - EPS)
    return -np.log1p(-s)


@dataclass
class Masses:
    """D-S mass function on frame {ERROR, CLEAN}."""
    m_err: np.ndarray      # mass supporting ERROR
    m_clean: np.ndarray    # mass supporting CLEAN
    m_omega: np.ndarray    # ignorance (uncertainty)
    K: np.ndarray          # conflict between sources
    score: np.ndarray      # sigmoid(W+ - W-), normalized plausibility of ERROR

    def to_dict_single(self, idx: int = 0) -> dict:
        """Extract single-row masses as a dictionary."""
        return {
            "belief_error": float(self.m_err[idx]) if self.m_err.ndim > 0 else float(self.m_err),
            "belief_clean": float(self.m_clean[idx]) if self.m_clean.ndim > 0 else float(self.m_clean),
            "ignorance": float(self.m_omega[idx]) if self.m_omega.ndim > 0 else float(self.m_omega),
            "conflict": float(self.K[idx]) if self.K.ndim > 0 else float(self.K),
            "score": float(self.score[idx]) if self.score.ndim > 0 else float(self.score),
        }


def compute_masses(w_pos: np.ndarray, w_neg: np.ndarray) -> Masses:
    """Compute D-S masses from positive (error) and negative (clean) weights.

    With total support W+ for error and W- for clean:
        S = 1 - exp(-W+)
        T = 1 - exp(-W-)
        K = S * T
        m(err)   = S(1-T) / (1-K)
        m(clean) = T(1-S) / (1-K)
        m(Omega) = (1-S)(1-T) / (1-K)
    """
    S = 1.0 - np.exp(-w_pos)
    T = 1.0 - np.exp(-w_neg)
    K = S * T
    d = np.maximum(1.0 - K, EPS)
    return Masses(
        m_err=S * (1.0 - T) / d,
        m_clean=T * (1.0 - S) / d,
        m_omega=(1.0 - S) * (1.0 - T) / d,
        K=K,
        score=1.0 / (1.0 + np.exp(-(w_pos - w_neg))),
    )


def combine_weights(
    weights: list[np.ndarray],
    families: list[str],
    rule: str = "family",
) -> np.ndarray:
    """Combine evidence weights according to the specified rule.

    Args:
        weights: List of weight arrays from different sources.
        families: Family label for each weight (used in 'family' rule).
        rule: 'dempster' (sum all), 'cautious' (max all), or 'family'
              (max within family, sum across families).

    Returns:
        Combined weight array.
    """
    if not weights:
        return np.zeros(1)

    if rule == "dempster":
        return np.sum(weights, axis=0)
    elif rule == "cautious":
        return np.max(weights, axis=0)
    elif rule == "family":
        # Cautious within family, Dempster across families
        result = np.zeros_like(weights[0], dtype=float)
        unique_families = set(families)
        for fam in unique_families:
            fam_weights = [w for w, f in zip(weights, families) if f == fam]
            result = result + np.max(fam_weights, axis=0)
        return result
    else:
        raise ValueError(f"Unknown combination rule: {rule}")


def fuse_evidence(
    profiler_evidence: dict[str, np.ndarray],
    family_of: dict[str, str],
    llm_evidence: dict | None = None,
    rule: str = "family",
) -> dict[str, Masses]:
    """Fuse profiler and LLM evidence into cell-level and row-level masses.

    This is the main fusion entry point for DataGuard.

    Args:
        profiler_evidence: {profiler_name: evidence_matrix(n, m)} from detectors.
        family_of: {profiler_name: family_name} mapping.
        llm_evidence: Optional LLM evidence dict with row/cell weights.
        rule: Combination rule ('family', 'dempster', 'cautious').

    Returns:
        Dict with 'cell' and 'row' Masses objects.
    """
    names = list(profiler_evidence)
    if not names:
        n, m = 1, 1
        zero = np.zeros((n, m))
        return {
            "cell": compute_masses(zero, zero),
            "row": compute_masses(np.zeros(n), np.zeros(n)),
        }

    n, m = next(iter(profiler_evidence.values())).shape
    W = {k: weight(profiler_evidence[k]) for k in names}

    # Cell-level fusion
    cell_ws = [W[k] for k in names]
    cell_fams = [family_of[k] for k in names]
    row_neg = np.zeros(n)

    if llm_evidence is not None:
        for agent_name, cell_w in llm_evidence.get("cell_pos", {}).items():
            cell_ws.append(cell_w)
            cell_fams.append("llm")

        # Row-level negative evidence (LLM says "clean")
        row_neg_list = list(llm_evidence.get("row_neg", {}).values())
        if row_neg_list:
            row_neg = np.max(row_neg_list, axis=0) if rule != "dempster" else np.sum(row_neg_list, axis=0)

    w_cell_pos = combine_weights(cell_ws, cell_fams, rule)
    cell_masses = compute_masses(w_cell_pos, np.repeat(row_neg[:, None], m, axis=1))

    # Row-level fusion: strongest cell symptom + LLM row verdicts
    prof_only = combine_weights([W[k] for k in names], [family_of[k] for k in names], rule)
    w_row_pos = prof_only.max(axis=1)

    if llm_evidence is not None:
        row_pos_list = list(llm_evidence.get("row_pos", {}).values())
        if row_pos_list:
            llm_row = np.sum(row_pos_list, axis=0) if rule == "dempster" else np.max(row_pos_list, axis=0)
            if rule == "cautious":
                w_row_pos = np.maximum(w_row_pos, llm_row)
            else:
                w_row_pos = w_row_pos + llm_row

    row_masses = compute_masses(w_row_pos, row_neg)

    return {"cell": cell_masses, "row": row_masses}


def fuse_single_cell(evidence_scores: list[tuple[float, str]]) -> dict:
    """Convenience: fuse evidence for a single cell.

    Args:
        evidence_scores: List of (score, family) tuples.
            score > 0 means evidence of error.
            score < 0 means evidence of clean.
            Magnitude is strength [0, 1].

    Returns:
        Dict with belief_error, belief_clean, ignorance, conflict, score.
    """
    pos_weights = []
    neg_weights = []
    pos_fams = []
    neg_fams = []

    for score, family in evidence_scores:
        w = weight(abs(score))
        if score > 0:
            pos_weights.append(np.array([w]))
            pos_fams.append(family)
        elif score < 0:
            neg_weights.append(np.array([w]))
            neg_fams.append(family)

    w_pos = combine_weights(pos_weights, pos_fams, "family") if pos_weights else np.array([0.0])
    w_neg = combine_weights(neg_weights, neg_fams, "family") if neg_weights else np.array([0.0])

    m = compute_masses(w_pos, w_neg)
    return m.to_dict_single(0)
