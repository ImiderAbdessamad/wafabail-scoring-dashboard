"""Construit le workspace d'analyse (charts, ratios, synthèse) pour le front."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.analyse import ScoringAnalysisResult
from app.schemas.create_dossier import StoredDossierRecord
from app.services.ratio_engine import RATIO_METADATA
from app.services.scoring_engine import (
    AXE1_PENALTY_NON_CONFORME,
    AXE1_PENALTY_SURVEILLER,
    AXE1_RATIO_KEYS,
)
from app.services.synthese_builder import build_synthese, empty_synthese

_STATUS_LABEL = {
    "pending": "Docs en attente",
    "analyzing": "En analyse",
    "ready": "Prêt",
    "review": "Revue",
    "approved": "Approuvé",
    "reserved": "Sous réserve",
    "rejected": "Rejeté",
}

_RATIO_UI_STATUS = {
    "Conforme": "GOOD",
    "À surveiller": "WARN",
    "Non conforme": "BAD",
    "Non calculable": "WARN",
}

def _file_kind(name: str) -> str:
    n = name.lower()
    if "proforma" in n or "facture" in n:
        return "proforma"
    if "liasse" in n or "bilan" in n or "cpc" in n:
        return "liasse"
    if "relev" in n or "bancaire" in n:
        return "releves"
    if "rc" in n or "commerce" in n or "kbis" in n:
        return "rc"
    if "cin" in n:
        return "cin"
    return "piece"


def _documents(record: StoredDossierRecord, result: ScoringAnalysisResult | None) -> dict[str, Any]:
    items = []
    extractions: dict[str, Any] = {}
    for index, file in enumerate(record.files):
        doc_id = f"doc-{index}-{file.name}"
        size_ko = max(1, round(file.size / 1024))
        kind = _file_kind(file.name)
        items.append({
            "id": doc_id,
            "name": file.name,
            "meta": f"{(file.contentType.split('/')[-1] or 'fichier').upper()} · {size_ko} Ko",
            "confidence": 0 if result is None else (92 if kind == "liasse" else 80),
            "uploadName": file.name,
        })

    identity_fields = []
    if result is not None:
        company = result.document.company
        exercise = result.document.exercise
        years = result.years
        identity_fields = [
            {"label": "Raison sociale", "value": company.raison_sociale or "—", "source": "p. 1 — Identification", "confidence": 95 if company.raison_sociale else 0},
            {"label": "ICE", "value": company.ice or "—", "source": "p. 1 — Identification", "confidence": 95 if company.ice else 0},
            {"label": "RC", "value": company.rc or "—", "source": "p. 1 — Identification", "confidence": 95 if company.rc else 0},
            {"label": "Identifiant fiscal", "value": company.identifiant_fiscal or "—", "source": "p. 1 — Identification", "confidence": 90 if company.identifiant_fiscal else 0},
            {"label": "Exercice", "value": exercise.label or " — ".join(years.labels), "source": "Page d'identification", "confidence": 90 if exercise.fin else 0},
        ]
        fields = list(identity_fields)
        for field in result.fields:
            if field.code == "TYPE_RESULTAT":
                value = field.note or "—"
            elif field.value is None:
                value = "—"
            else:
                value = _mad(field.value)
            evidence = field.evidence[0] if field.evidence else None
            source = (
                f"p. {evidence.page_number}" if evidence and evidence.page_number else field.source
            )
            if field.value_n1 is not None:
                source = f"{source} · N-1 {_mad(field.value_n1)}"
            fields.append({
                "label": field.label,
                "value": value,
                "source": source,
                "confidence": int(round(field.confidence * 100)),
            })
        liasse_item = next(
            (item for item in items if _file_kind(item["name"]) == "liasse"),
            items[0] if items else None,
        )
        if liasse_item is not None:
            extractions[liasse_item["id"]] = {
                "title": result.document.filename,
                "flag": f"OCR v10 · {result.completeness_pct:.0f} % · {years.available_count} exercice(s)",
                "fields": fields,
            }

    present = len(items)
    total = max(present, 1)
    default_id = ""
    if result is not None:
        default_id = next(
            (item["id"] for item in items if _file_kind(item["name"]) == "liasse"),
            items[0]["id"] if items else "",
        )
    elif items:
        default_id = items[0]["id"]
    return {
        "present": present,
        "total": present,
        "completenessPct": 100 if present else 0,
        "items": items,
        "missing": [],
        "extractions": extractions,
        "defaultDocId": default_id,
    }


def overlay_live_documents(record: StoredDossierRecord, workspace: dict[str, Any] | None) -> dict[str, Any]:
    """Met à jour la liste des fichiers sans perdre les extractions déjà calculées."""
    base = dict(workspace) if workspace else empty_workspace(record)
    fresh = _documents(record, None)
    old_docs = (workspace or {}).get("documents") or {}
    old_items = old_docs.get("items") or []
    old_ext = old_docs.get("extractions") or {}
    by_name: dict[str, Any] = {}
    for item in old_items:
        ext = old_ext.get(item.get("id"))
        if ext and item.get("name"):
            by_name[item["name"]] = ext
    for item in fresh["items"]:
        kept = by_name.get(item["name"])
        if kept:
            fresh["extractions"][item["id"]] = kept
            item["confidence"] = item.get("confidence") or 80
    if not fresh["defaultDocId"] and fresh["items"]:
        fresh["defaultDocId"] = fresh["items"][-1]["id"]
    base["documents"] = fresh
    base["header"] = _header(record)
    return base


def _mad(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}".replace(".", ",") + " M MAD"
    return f"{value:,.0f}".replace(",", " ") + " MAD"


def _short(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}".replace(".", ",") + " M"
    return f"{round(value / 1000)} K"


def _pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}".replace(".", ",") + " %"


def _fmt_ratio(key: str, value: float | None) -> str:
    meta = RATIO_METADATA.get(key, {})
    unit = meta.get("unit", "")
    if value is None:
        return "—"
    if unit == "%":
        return _pct(value)
    if unit == "x":
        return f"{value:.2f}".replace(".", ",") + "x"
    if unit in {"j", "ans"}:
        return f"{value:.0f} {unit}"
    return f"{value:.2f}".replace(".", ",")


def _bar_pct(key: str, value: float | None, status: str) -> int:
    if value is None:
        return 8
    if status == "Conforme":
        return 82
    if status == "À surveiller":
        return 48
    if status == "Non conforme":
        return 22
    return 12


def _ratios_block(result: ScoringAnalysisResult) -> dict[str, Any]:
    items = []
    conform = watch = 0
    for key, meta in RATIO_METADATA.items():
        raw = result.ratios.get(key)
        if raw is None:
            continue
        status_fr = raw.get("status") or "Non calculable"
        ui = _RATIO_UI_STATUS.get(status_fr, "WARN")
        if status_fr == "Conforme":
            conform += 1
        elif status_fr == "À surveiller":
            watch += 1
        value = raw.get("value")
        items.append({
            "label": meta["label"],
            "formula": f"{meta['formula']}  ·  {meta['threshold']}",
            "value": _fmt_ratio(key, value),
            "status": ui,
            "barPct": _bar_pct(key, value, status_fr),
            "interpretation": raw.get("reason")
            or f"Statut {status_fr.lower()} au regard du seuil {meta['threshold']}.",
        })

    inp = result.ratio_inputs
    years = result.years
    year_n = years.labels[2] if years.labels else "N"
    fiscal = [
        {"label": f"Chiffre d'affaires ({year_n})", "value": _mad(inp.get("chiffre_affaires")), "tone": "neutral"},
        {"label": "Résultat net", "value": _mad(inp.get("resultat_net")), "tone": "ok" if (inp.get("resultat_net") or 0) >= 0 else "warn"},
        {"label": "CAF", "value": _mad(inp.get("caf")), "tone": "ok" if (inp.get("caf") or 0) >= 0 else "warn"},
        {"label": "Total bilan", "value": _mad(inp.get("total_bilan")), "tone": "neutral"},
        {"label": "Fonds propres", "value": _mad(inp.get("fonds_propres")), "tone": "neutral"},
        {"label": "Endettement à terme", "value": _mad(inp.get("dettes_financement")), "tone": "warn" if (inp.get("dettes_financement") or 0) > (inp.get("fonds_propres") or 0) * 2 else "neutral"},
        {"label": "Trésorerie nette", "value": _mad(inp.get("tresorerie_nette")), "tone": "ok" if (inp.get("tresorerie_nette") or 0) >= 0 else "warn"},
    ]
    return {
        "calcTime": "< 1 s",
        "conformCount": conform,
        "watchCount": watch,
        "items": items,
        "fiscal": fiscal,
    }


def _scoring_block(record: StoredDossierRecord, result: ScoringAnalysisResult, ratios: dict[str, Any]) -> dict[str, Any]:
    decision = result.decision
    score = int(round(float(decision.get("score") or 0)))
    axe1 = result.axes.get("financier") or {}
    n_grid = max(int(axe1.get("ratios_expected") or len(AXE1_RATIO_KEYS)), 1)
    conforme_pct = round(100.0 / n_grid, 1)
    factors = []
    for key in axe1.get("ratios_conformes") or []:
        label = RATIO_METADATA.get(key, {}).get("label", key)
        factors.append({"label": label, "impact": conforme_pct})
    for key in axe1.get("ratios_a_surveiller") or []:
        label = RATIO_METADATA.get(key, {}).get("label", key)
        factors.append({"label": label, "impact": -AXE1_PENALTY_SURVEILLER})
    for key in axe1.get("ratios_non_conformes") or []:
        label = RATIO_METADATA.get(key, {}).get("label", key)
        factors.append({"label": label, "impact": -AXE1_PENALTY_NON_CONFORME})
    if not factors:
        completeness = float(result.completeness_pct or 0)
        factors = [{"label": "Complétude d'extraction", "impact": round(completeness - 50, 1)}]

    ca_series = (result.years.series or {}).get("chiffre_affaires") or [None, None, None]
    rn_series = (result.years.series or {}).get("resultat_net") or [None, None, None]
    labels = result.years.labels or ["—", "N-1", "N"]
    points = []
    cas = [v for v in ca_series if v]
    max_ca = max(cas) if cas else 1
    rns = [abs(v) for v in rn_series if v is not None]
    max_rn = max(rns) if rns else 1
    for year, ca_v, rn_v in zip(labels, ca_series, rn_series):
        if ca_v is None and rn_v is None and year in {"N-2", "—"}:
            continue
        points.append({
            "year": year,
            "caLabel": _short(ca_v),
            "caHeightPct": int(round(100 * (ca_v or 0) / max_ca)) if ca_v else 6,
            "rnHeightPct": int(round(100 * abs(rn_v or 0) / max_rn)) if rn_v is not None else 4,
        })
    if len(points) < 2:
        points = [
            {"year": labels[1], "caLabel": _short(ca_series[1]), "caHeightPct": int(round(100 * (ca_series[1] or 0) / max_ca)) if ca_series[1] else 6, "rnHeightPct": 4},
            {"year": labels[2], "caLabel": _short(ca_series[2]), "caHeightPct": int(round(100 * (ca_series[2] or 0) / max_ca)) if ca_series[2] else 6, "rnHeightPct": int(round(100 * abs(rn_series[2] or 0) / max_rn)) if rn_series[2] is not None else 4},
        ]

    growth = result.ratios.get("croissance_ca") or {}
    growth_v = growth.get("value")
    series_years = [lab for lab in labels if lab not in {"—", "N-2"}]
    series_txt = " / ".join(series_years) if series_years else ", ".join(labels)
    exercise = result.document.exercise
    period = exercise.label or (f"Du {exercise.debut} au {exercise.fin}" if exercise.debut and exercise.fin else "")
    period_suffix = f" · {period}" if period else ""
    caption = (
        f"Série {series_txt}{period_suffix} — CA "
        f"{('en hausse' if (growth_v or 0) > 0 else 'en repli')} ({_pct(growth_v)} vs N-1)."
        if growth_v is not None
        else f"Série {series_txt}{period_suffix} : {result.years.available_count} exercice(s) renseigné(s) sur la liasse."
    )

    calculable = int(axe1.get("ratios_calculables") or 0)
    if calculable <= 0:
        calculable = (
            len(axe1.get("ratios_conformes") or [])
            + len(axe1.get("ratios_a_surveiller") or [])
            + len(axe1.get("ratios_non_conformes") or [])
        )
    ratios_ok = len(axe1.get("ratios_conformes") or [])
    ratios_total = calculable or len(AXE1_RATIO_KEYS)

    return {
        "score": score,
        "classe": decision.get("classe") or "",
        "recommendation": decision.get("recommandation") or decision.get("decision") or "—",
        "riskLabel": decision.get("decision") or "—",
        "summary": (
            f"{record.name} — extraction {result.completeness_pct:.0f} % des postes financiers. "
            f"Score composite {score}/100, classe {decision.get('classe', '—')} « {decision.get('decision', '—')} ». "
            f"{decision.get('axe2_note') or 'Les ratios financiers sont calculés sur les 11 ratios de l’axe 1.'}"
        ),
        "ratiosOk": ratios_ok,
        "ratiosTotal": ratios_total,
        "dossierCompletenessPct": int(result.completeness_pct),
        "factors": factors[:8],
        "trend": points,
        "trendCaption": caption,
        "attention": build_synthese(result, nouveau_financement=float(record.amount or 0) or None),
    }


def _pipeline(result: ScoringAnalysisResult | None, score: int) -> dict[str, Any]:
    steps = [
        {"label": "Réception & indexation", "meta": "MinIO"},
        {"label": "OCR & extraction des documents", "meta": "moteur v10"},
        {"label": "Classification des pages", "meta": "GLM + Qwen"},
        {"label": "Lecture guidée par la grille", "meta": "ensemble OCR"},
        {"label": "Mapping sémantique", "meta": "Qwen / Gemma"},
        {"label": "Contrôles comptables", "meta": "arithmétique"},
        {"label": "Analyse financière & ratios", "meta": "11 ratios"},
        {"label": "Benchmark sectoriel", "meta": "médianes"},
        {"label": "Score composite & mémo", "meta": "75 / 15 / 10"},
    ]
    if result is None:
        return {
            "policyVersion": "Politique scoring Wafabail · moteur v10",
            "steps": steps,
            "fullTrace": [],
            "initialStep": 0,
            "initialScore": 0,
        }
    doc = result.document
    trace = [
        {"type": "in", "text": f"Liasse « {doc.filename} » — {doc.pages_total} page(s)", "step": 0},
        {"type": "ok", "text": f"{doc.pages_processed} page(s) financières extraites (v10 grid ensemble)", "step": 1},
        {"type": "ok", "text": f"Complétude {result.completeness_pct:.0f} % — {len(result.fields)} postes", "step": 4},
    ]
    failed = [c for c in result.controls if c.status == "failed"]
    if failed:
        trace.append({"type": "warn", "text": f"{len(failed)} contrôle(s) comptable(s) en écart", "step": 5})
    else:
        trace.append({"type": "ok", "text": "Contrôles comptables cohérents", "step": 5})
    for warning in result.warnings[:4]:
        trace.append({"type": "warn", "text": warning, "step": 6})
    trace.append({"type": "res", "text": f"Score composite {score}/100", "step": 8})
    return {
        "policyVersion": f"Politique scoring · {result.extraction.model}",
        "steps": steps,
        "fullTrace": trace,
        "initialStep": len(steps),
        "initialScore": score,
    }


def _bien(record: StoredDossierRecord) -> dict[str, Any]:
    apport_pct = record.apport
    financed = max(0, record.amount - round(record.amount * apport_pct / 100))
    residual = round(record.amount * 0.05)
    monthly = round(financed / max(record.duration, 1))
    return {
        "title": record.natureBien or record.nature,
        "subtitle": f"{record.sector} · {record.fournisseur}",
        "assetValueLabel": _mad(record.valeurBien or record.amount),
        "financedLabel": _mad(financed),
        "durationLabel": f"{record.duration} mois",
        "residualLabel": _mad(residual),
        "units": [{
            "qty": "1",
            "designation": record.natureBien or record.nature,
            "marque": "—",
            "modele": record.etat,
            "annee": "—",
            "valeur": _mad(record.valeurTtc or record.valeurBien),
        }],
        "totalTtcLabel": _mad(record.valeurTtc),
        "specs": [
            {"key": "Fournisseur", "value": record.fournisseur},
            {"key": "Réf. proforma", "value": record.proformaReference or "—"},
            {"key": "Nature", "value": record.nature},
            {"key": "État", "value": record.etat},
            {"key": "Durée du contrat", "value": f"{record.duration} mois"},
            {"key": "Apport", "value": f"{apport_pct:.0f} %"},
        ],
        "schedule": [
            {"label": "Loyers mensuels", "count": str(record.duration), "amount": _mad(monthly), "highlight": True},
        ],
        "totalCostLabel": _mad(financed),
        "creditCostLabel": "—",
        "guarantees": [
            {"ok": True, "title": "Bien identifié", "detail": record.natureBien or "Bien financé renseigné au dossier."},
        ],
    }


def _factorielle(result: ScoringAnalysisResult) -> list[dict[str, Any]]:
    series = result.years.series or {}
    labels = result.years.labels or ["—", "N-1", "N"]

    def row(label: str, key: str) -> dict[str, Any]:
        values = list(series.get(key) or [None, None, None])
        while len(values) < 3:
            values.insert(0, None)
        n2, n1, n = values[0], values[1], values[2]
        var = None
        if n is not None and n1 not in (None, 0):
            var = (n - n1) / abs(n1)
        tone = "flat"
        if var is not None:
            tone = "up" if var >= 0.02 else "down" if var <= -0.02 else "flat"
        return {
            "label": label,
            "y1": _short(n2),
            "y2": _short(n1),
            "y3": _short(n),
            "variation": _pct(var) if var is not None else "—",
            "variationTone": tone,
        }

    def ratio_items(keys: list[str]) -> list[dict[str, Any]]:
        out = []
        for key in keys:
            raw = result.ratios.get(key) or {}
            meta = RATIO_METADATA.get(key, {})
            status_fr = raw.get("status") or "Non calculable"
            out.append({
                "label": meta.get("label", key),
                "value": _fmt_ratio(key, raw.get("value")),
                "status": _RATIO_UI_STATUS.get(status_fr, "WARN"),
            })
        return out

    exercise = result.document.exercise
    period = exercise.label or (
        f"Du {exercise.debut} au {exercise.fin}" if exercise.debut and exercise.fin else ""
    )
    unit = f"MAD · {period}" if period else "MAD"

    axes = [
        {
            "num": "01",
            "title": "Structure financière",
            "unit": unit,
            "yearLabels": labels,
            "rows": [
                row("Total bilan", "total_bilan"),
                row("Fonds propres", "fonds_propres"),
                row("Endettement à terme", "endettement_terme"),
                row("Dettes financières", "dettes_financieres"),
            ],
            "ratios": ratio_items(["autonomie_financiere", "ratio_endettement", "capacite_remboursement"]),
        },
        {
            "num": "02",
            "title": "Activité et rentabilité",
            "unit": unit,
            "yearLabels": labels,
            "rows": [
                row("Chiffre d'affaires", "chiffre_affaires"),
                row("Résultat net", "resultat_net"),
                row("Résultat d'exploitation", "resultat_exploitation"),
                row("CAF", "caf"),
            ],
            "ratios": ratio_items(["rentabilite_commerciale", "rentabilite_financiere", "caf_sur_ca", "croissance_ca"]),
        },
        {
            "num": "03",
            "title": "Liquidité et cycle",
            "unit": unit,
            "yearLabels": labels,
            "rows": [
                row("Trésorerie nette", "tresorerie_nette"),
                row("FDR", "fdr"),
                row("Créances clients", "clients"),
                row("Dettes fournisseurs", "fournisseurs"),
                row("Stocks", "stocks"),
            ],
            "ratios": ratio_items(["fdr_sur_ca", "tresorerie_jours_ca", "delais_clients", "delais_fournisseurs", "delais_stocks"]),
        },
    ]
    return axes


def _comportement(result: ScoringAnalysisResult) -> dict[str, Any]:
    axe = result.axes.get("comportemental") or {}
    score = int(round(axe["score"])) if isinstance(axe.get("score"), (int, float)) else 0
    return {
        "score": score,
        "profileLabel": "Données bancaires non extraites",
        "summary": axe.get("note") or "Les relevés bancaires ne sont pas encore passés au moteur. L'axe comportemental (15 %) n'entre pas dans la note.",
        "metrics": [
            {"label": "Incidents", "value": "n/c", "tone": "neutral", "sub": "Non fourni"},
            {"label": "Domiciliation CA", "value": "n/c", "tone": "neutral", "sub": "Relevés requis"},
            {"label": "Jours débit", "value": "n/c", "tone": "neutral", "sub": "Relevés requis"},
            {"label": "Écart flux / CA", "value": "n/c", "tone": "neutral", "sub": "Relevés requis"},
        ],
        "months": [],
        "signals": [
            {"tone": "warn", "title": "Axe 2 non noté", "detail": axe.get("note") or "Joindre 6 mois de relevés pour activer le score comportemental."},
        ],
    }


def _benchmark(record: StoredDossierRecord, result: ScoringAnalysisResult) -> dict[str, Any]:
    axe = result.axes.get("sectoriel") or {}
    rows = []
    for item in axe.get("comparaisons") or []:
        key = item.get("indicateur")
        meta = RATIO_METADATA.get(key, {})
        client = item.get("valeur")
        median = item.get("mediane")
        tone = "ok" if item.get("statut") == "Conforme" else "bad"
        rows.append({
            "label": meta.get("label", key),
            "client": _fmt_ratio(key, client),
            "median": _fmt_ratio(key, median),
            "clientPct": min(100, int(round(abs(client or 0) * 100))) if client is not None else 8,
            "medianPct": min(100, int(round(abs(median or 0) * 100))) if median is not None else 8,
            "tone": tone,
            "percentile": item.get("statut") or "—",
        })
    above = sum(1 for r in rows if r["tone"] == "ok")
    return {
        "sectorLabel": record.sector,
            "sampleSize": len(rows),
        "caption": "Comparaison aux médianes du panel sectoriel (axe 3, poids 10 %).",
        "rows": rows,
        "aboveMedianLabel": f"{above}/{len(rows)} indicateur(s) au-dessus de la médiane" if rows else "Aucun indicateur comparable",
        "comparables": [],
    }


def _memo(record: StoredDossierRecord, result: ScoringAnalysisResult, scoring: dict[str, Any], ratios: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    return {
        "title": "Mémo d'analyse crédit-bail",
        "subtitle": record.name,
        "refLine": f"{record.id} · {record.sector}",
        "recommendation": scoring["recommendation"],
        "scoreLine": f"Score {scoring['score']}/100 — {result.decision.get('classe', '')}",
        "clientGrid": [
            {"label": "ICE", "value": result.document.company.ice or record.ice or "—"},
            {"label": "RC", "value": result.document.company.rc or record.rc or "—"},
            {"label": "Montant", "value": _mad(record.amount)},
            {"label": "Durée", "value": f"{record.duration} mois"},
        ],
        "sections": [
            {
                "title": "Faits",
                "paragraphs": [scoring["summary"]],
            },
            {
                "title": "Ratios",
                "chips": [
                    {"ok": ratios["conformCount"] >= max(1, len(ratios["items"]) // 2), "label": "Ratios conformes", "value": f"{ratios['conformCount']}/{len(ratios['items'])}"},
                    {"ok": result.completeness_pct >= 70, "label": "Complétude OCR", "value": f"{result.completeness_pct:.0f} %"},
                ],
            },
            {
                "title": "Conclusion",
                "conclusionBanner": f"{scoring['recommendation']} — Score {scoring['score']}/100",
            },
        ],
        "signerName": record.analyst,
        "signerRole": "Analyste crédit-bail",
        "signedAt": now,
    }


def _copilot(record: StoredDossierRecord, scoring: dict[str, Any], result: ScoringAnalysisResult) -> dict[str, Any]:
    return {
        "welcomeMessage": (
            f"Bonjour, je suis le copilote Qwen pour {record.name} "
            f"(score {scoring['score']}/100). Posez une question sur les ratios, les risques ou la synthèse."
        ),
        "chips": [
            {"label": "Pourquoi ce score ?", "intent": "pourquoi"},
            {"label": "Risques", "intent": "risque"},
            {"label": "Complétude", "intent": "complet"},
            {"label": "Secteur", "intent": "secteur"},
        ],
        "qa": {
            "pourquoi": scoring["summary"],
            "risque": " ".join(result.warnings[:3]) or "Aucun signal bloquant remonté par les contrôles.",
            "complet": f"Complétude d'extraction {result.completeness_pct:.0f} % sur les postes financiers.",
            "secteur": f"Benchmark {record.sector} — {result.axes.get('sectoriel', {}).get('score', 'n/c')}/100.",
            "fallback": "Je m'appuie sur l'extraction v10, les 11 ratios et Qwen 3.5.",
        },
    }


def _header(record: StoredDossierRecord, result: ScoringAnalysisResult | None = None) -> dict[str, Any]:
    company = result.document.company if result else None
    ice = (company.ice if company else None) or record.ice or "—"
    rc = (company.rc if company else None) or record.rc or "—"
    name = (company.raison_sociale if company and company.raison_sociale else None) or record.name
    ville = (company.ville if company else None) or (company.adresse if company else None)
    bits = [record.sector]
    if ice and ice != "—":
        bits.append(f"ICE {ice}")
    if rc and rc != "—":
        bits.append(f"RC {rc}")
    if record.source == "pvc" and record.noDemande:
        bits.append(f"PVC {record.noDemande}")
    return {
        "id": record.id,
        "shortCode": record.id.split("-")[-1],
        "companyName": name,
        "subtitle": " · ".join(bits),
        "status": record.status,
        "statusLabel": _STATUS_LABEL.get(record.status, record.status),
        "analyst": record.analyst,
        "amountFinanced": record.amount,
        "assetValue": record.valeurBien or record.amount,
        "durationMonths": record.duration,
        "apportPct": record.apport,
        "location": ville or "Maroc",
        "source": record.source,
        "noDemande": record.noDemande,
        "noPv": record.noPv,
    }


def empty_workspace(record: StoredDossierRecord) -> dict[str, Any]:
    documents = _documents(record, None)
    bien = _bien(record)
    return {
        "header": _header(record),
        "pipeline": _pipeline(None, 0),
        "documents": documents,
        "scoring": {
            "score": record.score,
            "classe": "",
            "recommendation": "Lancez l'analyse pour extraire la liasse et calculer le score.",
            "riskLabel": "En attente d'extraction",
            "summary": "Aucune extraction v10 n'a encore été exécutée sur ce dossier. Le bouton Relancer lance le moteur (grille + ensemble OCR), identique au projet RCC.",
            "ratiosOk": 0,
            "ratiosTotal": 11,
            "dossierCompletenessPct": 0,
            "factors": [],
            "trend": [],
            "trendCaption": "Les graphiques s'afficheront après l'extraction de la liasse.",
            "attention": empty_synthese(),
        },
        "ratios": {"calcTime": "—", "conformCount": 0, "watchCount": 0, "items": [], "fiscal": []},
        "bien": bien,
        "factorielle": [],
        "yearLabels": ["—", "N-1", "N"],
        "comportement": {
            "score": 0,
            "profileLabel": "Non calculé",
            "summary": "Disponible après extraction.",
            "metrics": [],
            "months": [],
            "signals": [],
        },
        "benchmark": {
            "sectorLabel": record.sector,
            "sampleSize": 0,
            "caption": "Disponible après extraction.",
            "rows": [],
            "aboveMedianLabel": "—",
            "comparables": [],
        },
        "memo": {
            "title": "Mémo d'analyse",
            "subtitle": record.name,
            "refLine": record.id,
            "recommendation": "Analyse non lancée",
            "scoreLine": "—",
            "clientGrid": [],
            "sections": [],
            "signerName": record.analyst,
            "signerRole": "Analyste crédit-bail",
            "signedAt": "",
        },
        "copilot": {
            "welcomeMessage": "Je suis le copilote Qwen. Posez une question sur ce dossier : dès que l'analyse est prête, je m'appuie sur le score et les ratios.",
            "chips": [
                {"label": "Pourquoi ce score ?", "intent": "pourquoi"},
                {"label": "Risques", "intent": "risque"},
                {"label": "Complétude", "intent": "complet"},
                {"label": "Secteur", "intent": "secteur"},
            ],
            "qa": {"pourquoi": "", "risque": "", "complet": "", "secteur": "", "fallback": "Analyse non disponible."},
        },
    }


def build_workspace(record: StoredDossierRecord, result: ScoringAnalysisResult) -> dict[str, Any]:
    documents = _documents(record, result)
    ratios = _ratios_block(result)
    scoring = _scoring_block(record, result, ratios)
    return {
        "header": _header(record, result),
        "pipeline": _pipeline(result, scoring["score"]),
        "documents": documents,
        "scoring": scoring,
        "ratios": ratios,
        "bien": _bien(record),
        "factorielle": _factorielle(result),
        "yearLabels": result.years.labels,
        "comportement": _comportement(result),
        "benchmark": _benchmark(record, result),
        "memo": _memo(record, result, scoring, ratios),
        "copilot": _copilot(record, scoring, result),
    }
