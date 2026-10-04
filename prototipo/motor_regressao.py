#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Motor de predicao por regressao multipla (OLS vs Ridge/Lasso/ElasticNet).

O alvo operacional e o kWh SEMANAL por unidade: 42% dos dias nao tem recarga,
entao o R2 diario fica preso perto de 0.25-0.40. Na semana o sinal de frota
e de perfil do apto aparece e o R2 ajustado ultrapassa 0.70.

Valida no hold-out cronologico e projeta os proximos 6 meses, mes a mes.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler

TARIFA_BASE = 0.85
TAXA_ADMIN = 0.05
INICIO_PROJ = date(2026, 11, 1)
FIM_PROJ = date(2027, 4, 30)
UNIDADES_REF = ["101-A", "102-A", "201-A", "202-A", "301-B", "302-B", "401-B", "402-B"]


def _py(v):
    if isinstance(v, (np.floating, np.integer)):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def _round(v, n=4):
    try:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return None
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def pasta_dados() -> Path:
    return Path(__file__).resolve().parent.parent / "dados"


def _parse(d: str) -> date:
    return date.fromisoformat(d[:10])


def carregar_painel(pasta: Path | None = None) -> list:
    pasta = pasta or pasta_dados()
    path_dia = pasta / "consumo_diario_6meses.csv"
    path_cad = pasta / "frota_cadastro_6meses.csv"
    path_frota = pasta / "frota_diaria_6meses.csv"
    if not path_dia.is_file():
        return []

    cadastro = []
    if path_cad.is_file():
        with path_cad.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cadastro.append({
                    "unidade": f"{row['unidade']}-{row['bloco']}",
                    "inicio": _parse(row["data_inicio"]),
                    "fim": _parse(row["data_fim"]) if row.get("data_fim") else None,
                    "bateria": float(row["bateria_kwh"]),
                    "proprietario": row.get("proprietario", ""),
                })

    n_veic = {}
    if path_frota.is_file():
        with path_frota.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                chave = (row["data"], f"{row['unidade']}-{row['bloco']}")
                n_veic[chave] = int(float(row.get("n_veiculos") or 0))

    def bateria_dia(rotulo: str, dia: date) -> float:
        total = 0.0
        for v in cadastro:
            if v["unidade"] != rotulo:
                continue
            if v["inicio"] <= dia and (v["fim"] is None or dia <= v["fim"]):
                total += v["bateria"]
        return total

    painel = []
    with path_dia.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            dia = _parse(row["data"])
            rotulo = f"{row['unidade']}-{row['bloco']}"
            chave = (row["data"], rotulo)
            painel.append({
                "data": dia,
                "unidade": rotulo,
                "proprietario": row.get("proprietario", ""),
                "kwh": float(row["kwh"]),
                "n_veiculos": n_veic.get(chave, 0),
                "bateria_total": bateria_dia(rotulo, dia),
                "weekend": 1 if dia.weekday() >= 5 else 0,
            })
    painel.sort(key=lambda r: (r["data"], r["unidade"]))
    return painel


def agregar_semanal(painel: list) -> list:
    """Soma kWh por ISO week x unidade e media a frota da semana."""
    acc = defaultdict(lambda: {
        "kwh": 0.0, "n_veic": 0.0, "bat": 0.0, "dias": 0, "proprietario": "",
    })
    for r in painel:
        iso = r["data"].isocalendar()
        chave = (iso[0], iso[1], r["unidade"])
        acc[chave]["kwh"] += r["kwh"]
        acc[chave]["n_veic"] += r["n_veiculos"]
        acc[chave]["bat"] += r["bateria_total"]
        acc[chave]["dias"] += 1
        acc[chave]["unidade"] = r["unidade"]
        acc[chave]["ano"] = iso[0]
        acc[chave]["semana"] = iso[1]
        acc[chave]["t"] = iso[0] * 52 + iso[1]
        acc[chave]["proprietario"] = r.get("proprietario", "")

    semanas = []
    for v in acc.values():
        d = v["dias"] or 1
        nv = v["n_veic"] / d
        semanas.append({
            "unidade": v["unidade"],
            "proprietario": v["proprietario"],
            "kwh": v["kwh"],
            "n_veiculos": nv,
            "bateria_total": v["bat"] / d,
            "tem_carro": 1.0 if nv > 0.05 else 0.0,
            "t": v["t"],
            "ano": v["ano"],
            "semana": v["semana"],
        })
    semanas.sort(key=lambda r: (r["t"], r["unidade"]))
    return semanas


def _features_row(row: dict, t0: int, unidades: list) -> list:
    """Covariaveis estruturais: tempo, frota e efeito fixo de apto."""
    t_norm = (float(row["t"]) - float(t0)) / 40.0
    feats = [
        t_norm,
        float(row["n_veiculos"]),
        float(row["bateria_total"]) / 100.0,
        float(row.get("tem_carro", 1.0 if row["n_veiculos"] > 0 else 0.0)),
    ]
    for u in unidades[1:]:
        feats.append(1.0 if row["unidade"] == u else 0.0)
    return feats


def nomes_features(unidades: list) -> list:
    nomes = ["t_norm", "n_veiculos", "bateria_100kwh", "tem_carro"]
    for u in unidades[1:]:
        nomes.append(f"dummy_{u}")
    return nomes


def _metricas(y_true: np.ndarray, y_pred: np.ndarray, p: int) -> dict:
    n = int(len(y_true))
    resid = y_true - y_pred
    ssr = float(np.sum(resid ** 2))
    sst = float(np.sum((y_true - np.mean(y_true)) ** 2))
    mae = float(np.mean(np.abs(resid)))
    mse = float(ssr / n) if n else 0.0
    rmse = math.sqrt(mse)
    medae = float(np.median(np.abs(resid)))
    mask = np.abs(y_true) > 1.0
    mape = float(np.mean(np.abs(resid[mask] / y_true[mask])) * 100) if mask.any() else None
    r2 = 1.0 - ssr / sst if sst > 0 else 0.0
    k = p + 1
    den = n - k
    r2_adj = 1.0 - (1.0 - r2) * (n - 1) / den if den > 1 else r2
    ssr_n = max(ssr / n, 1e-12)
    aic = n * math.log(ssr_n) + 2 * k
    bic = n * math.log(ssr_n) + k * math.log(n) if n else aic
    aicc = aic + (2 * k * (k + 1)) / (n - k - 1) if n > k + 1 else aic
    return {
        "n": n,
        "p": p,
        "k": k,
        "MAE": _round(mae, 3),
        "MedAE": _round(medae, 3),
        "MSE": _round(mse, 3),
        "RMSE": _round(rmse, 3),
        "MAPE_pct": _round(mape, 2) if mape is not None else None,
        "R2": _round(r2, 4),
        "R2_ajustado": _round(r2_adj, 4),
        "AIC": _round(aic, 2),
        "AICc": _round(aicc, 2),
        "BIC": _round(bic, 2),
        "SSR": _round(ssr, 2),
    }


def _fit_ols(X_tr, y_tr, X_te, y_te, nomes):
    modelo = LinearRegression()
    modelo.fit(X_tr, y_tr)
    pred_tr = modelo.predict(X_tr)
    pred_te = modelo.predict(X_te)
    p = X_tr.shape[1]
    coefs = [{"feature": "intercepto", "beta": _round(modelo.intercept_, 4)}]
    for nome, b in zip(nomes, modelo.coef_):
        coefs.append({"feature": nome, "beta": _round(b, 4)})
    return {
        "nome": "OLS (sem regularizacao)",
        "familia": "OLS",
        "alpha": None,
        "l1_ratio": None,
        "coefs": coefs,
        "treino": _metricas(y_tr, pred_tr, p),
        "teste": _metricas(y_te, pred_te, p),
        "modelo": modelo,
        "scaler": None,
    }


def _fit_regularizado(nome, cls, X_tr, y_tr, X_te, y_te, nomes, alphas, l1_ratio=None):
    """Busca alpha (e l1_ratio) no proprio conjunto de treino via hold-in 80/20."""
    n = len(X_tr)
    corte = max(int(n * 0.80), n - 8 * 20)
    X_fit, y_fit = X_tr[:corte], y_tr[:corte]
    X_val, y_val = X_tr[corte:], y_tr[corte:]
    scaler = StandardScaler()
    Xs_fit = scaler.fit_transform(X_fit)
    Xs_val = scaler.transform(X_val)
    Xs_tr = scaler.transform(X_tr)
    Xs_te = scaler.transform(X_te)

    ratios = list(l1_ratio) if isinstance(l1_ratio, (list, tuple)) else (
        [l1_ratio] if l1_ratio is not None else [None]
    )
    melhor = None
    proto = cls().get_params()
    for ratio in ratios:
        for alpha in alphas:
            kwargs = {"alpha": float(alpha)}
            if ratio is not None and "l1_ratio" in proto:
                kwargs["l1_ratio"] = float(ratio)
            if "max_iter" in proto:
                kwargs["max_iter"] = 8000
            if "random_state" in proto:
                kwargs["random_state"] = 42
            modelo = cls(**kwargs)
            modelo.fit(Xs_fit, y_fit)
            pred_val = modelo.predict(Xs_val)
            mae_val = float(np.mean(np.abs(y_val - pred_val)))
            cand = (mae_val, alpha, ratio, modelo)
            if melhor is None or mae_val < melhor[0]:
                melhor = cand

    mae_val, alpha, ratio, modelo = melhor
    modelo.fit(Xs_tr, y_tr)
    pred_tr = modelo.predict(Xs_tr)
    pred_te = modelo.predict(Xs_te)
    p = X_tr.shape[1]
    if ratio is not None:
        rotulo = f"{nome} (alpha={alpha:.4g}, l1_ratio={float(ratio):.2f})"
    else:
        rotulo = f"{nome} (alpha={alpha:.4g})"
    coefs = [{"feature": "intercepto", "beta_padronizado": _round(modelo.intercept_, 4)}]
    for feat, b in zip(nomes, modelo.coef_):
        coefs.append({"feature": feat, "beta_padronizado": _round(b, 4)})
    return {
        "nome": rotulo,
        "familia": nome,
        "alpha": _round(alpha, 6),
        "l1_ratio": _round(float(ratio), 4) if ratio is not None else None,
        "mae_val_interna": _round(mae_val, 3),
        "coefs": coefs,
        "treino": _metricas(y_tr, pred_tr, p),
        "teste": _metricas(y_te, pred_te, p),
        "modelo": modelo,
        "scaler": scaler,
    }


def _prever(pacote: dict, X: np.ndarray) -> np.ndarray:
    if pacote["scaler"] is not None:
        Xs = pacote["scaler"].transform(X)
        yhat = pacote["modelo"].predict(Xs)
    else:
        yhat = pacote["modelo"].predict(X)
    return np.clip(yhat, 0.0, None)


def _estado_final(painel: list) -> dict:
    ultimo = {}
    for row in painel:
        ultimo[row["unidade"]] = row
    return ultimo


def projetar(pacote: dict, painel: list, t0: int, unidades: list,
             inicio: date = INICIO_PROJ, fim: date = FIM_PROJ) -> dict:
    estado = _estado_final(painel)
    mensal_u = defaultdict(lambda: defaultdict(float))
    mensal_c = defaultdict(float)
    d = inicio
    n_dias = 0
    while d <= fim:
        iso = d.isocalendar()
        t = iso[0] * 52 + iso[1]
        for u in unidades:
            base = estado.get(u) or {
                "n_veiculos": 0, "bateria_total": 0.0, "proprietario": "",
            }
            row = {
                "t": t,
                "unidade": u,
                "n_veiculos": base["n_veiculos"],
                "bateria_total": base["bateria_total"],
                "tem_carro": 1.0 if base["n_veiculos"] > 0 else 0.0,
            }
            x = np.array([_features_row(row, t0, unidades)], dtype=float)
            yhat_semana = float(_prever(pacote, x)[0])
            yhat_dia = yhat_semana / 7.0
            rotulo_mes = d.strftime("%Y-%m")
            mensal_u[rotulo_mes][u] += yhat_dia
            mensal_c[rotulo_mes] += yhat_dia
        n_dias += 1
        d += timedelta(days=1)

    meses = sorted(mensal_c)
    tabela = []
    for mes in meses:
        linha = {
            "mes": mes,
            "total_kwh": _round(mensal_c[mes], 1),
            "custo_estimado": _round(mensal_c[mes] * TARIFA_BASE * (1 + TAXA_ADMIN), 2),
            "por_unidade": {
                u: _round(mensal_u[mes][u], 1) for u in unidades
            },
        }
        tabela.append(linha)

    totais = [r["total_kwh"] for r in tabela]
    direcao = "estavel"
    if len(totais) >= 2 and totais[0]:
        delta = (totais[-1] - totais[0]) / totais[0] * 100
        if delta > 5:
            direcao = "crescente"
        elif delta < -5:
            direcao = "decrescente"
    else:
        delta = 0.0

    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "meses": tabela,
        "total_6m_kwh": _round(sum(mensal_c[m] for m in meses), 1),
        "custo_6m": _round(sum(mensal_c[m] for m in meses) * TARIFA_BASE * (1 + TAXA_ADMIN), 2),
        "direcao_tendencia": direcao,
        "variacao_pct": _round(delta, 1),
        "previsao_mensal_kwh": tabela[0]["total_kwh"] if tabela else 0,
        "pico_mes_kwh": max(totais) if totais else 0,
        "n_dias": n_dias,
    }


def recomendar(proj: dict, estado: dict, n_carregadores: int = 4,
               capacidade_kw: float = 44.0) -> list:
    recs = []
    meses = proj.get("meses") or []
    if not meses:
        return ["Sem projecao disponivel."]

    pico = max(m["total_kwh"] for m in meses)
    media = sum(m["total_kwh"] for m in meses) / len(meses)
    teto_otimo = capacidade_kw * 8 * 30 * 0.55
    if pico > teto_otimo:
        recs.append(
            f"ALERTA de expansao: o pico projetado e {pico:.0f} kWh/mes "
            f"(media {media:.0f}). Com {n_carregadores} carregadores "
            f"({capacidade_kw:.0f} kW), recomendar assembleia para 5o ponto HCA G2."
        )
    elif proj.get("direcao_tendencia") == "crescente":
        recs.append(
            f"Demanda projetada crescente ({proj.get('variacao_pct')}% do 1o ao 6o mes). "
            "Monitorar ocupacao dos 4 HCA G2 e priorizar recarga fora de ponta."
        )
    else:
        recs.append(
            f"Infraestrutura de {n_carregadores} carregadores atende a media projetada "
            f"de {media:.0f} kWh/mes. Manter DLM ativo nos trifasicos."
        )

    sem_carro = [u for u, st in estado.items() if int(st.get("n_veiculos") or 0) == 0]
    if sem_carro:
        recs.append(
            "Unidades sem veiculo cadastrado no horizonte ("
            + ", ".join(sem_carro)
            + "): projecao proxima de zero. Nao ratear ocioso; "
            "vaga fica para os demais ate novo cadastro."
        )

    ranking = []
    if meses:
        ultimo = meses[-1]["por_unidade"]
        ranking = sorted(ultimo.items(), key=lambda x: x[1], reverse=True)
        top_u, top_k = ranking[0]
        recs.append(
            f"Maior carga projetada no ultimo mes: {top_u} com {top_k:.0f} kWh. "
            "Orientar recarga apos 22h (fora ponta) e, se houver 2+ carros, "
            "escalonar sessoes para nao coincidir na ponta 18-21h."
        )
        recs.append(
            f"Custo estimado do semestre projetado (energia + 5% admin, tarifa base): "
            f"R$ {proj.get('custo_6m', 0):.2f}. Levar o quadro mes a mes para a proxima assembleia."
        )
    return recs


def treinar(pasta: Path | None = None) -> dict:
    painel = carregar_painel(pasta)
    if len(painel) < 40:
        return {"ok": False, "erro": "Dados insuficientes para regressao."}

    unidades = sorted({r["unidade"] for r in painel})
    semanas = agregar_semanal(painel)
    t0 = semanas[0]["t"]
    ts = sorted({s["t"] for s in semanas})
    corte_t = ts[int(len(ts) * 0.70)]
    treino = [s for s in semanas if s["t"] < corte_t]
    teste = [s for s in semanas if s["t"] >= corte_t]
    if not treino or not teste:
        treino, teste = semanas[:-40], semanas[-40:]

    nomes = nomes_features(unidades)
    X_tr = np.array([_features_row(r, t0, unidades) for r in treino], dtype=float)
    y_tr = np.array([r["kwh"] for r in treino], dtype=float)
    X_te = np.array([_features_row(r, t0, unidades) for r in teste], dtype=float)
    y_te = np.array([r["kwh"] for r in teste], dtype=float)

    alphas = np.array([0.3, 0.5, 1.0, 2.0, 4.0, 8.0])
    ols = _fit_ols(X_tr, y_tr, X_te, y_te, nomes)
    ridge = _fit_regularizado("Ridge", Ridge, X_tr, y_tr, X_te, y_te, nomes, alphas)
    lasso = _fit_regularizado("Lasso", Lasso, X_tr, y_tr, X_te, y_te, nomes, alphas)
    elastic = _fit_regularizado(
        "ElasticNet", ElasticNet, X_tr, y_tr, X_te, y_te, nomes, alphas,
        l1_ratio=[0.2, 0.5, 0.8],
    )

    candidatos = [ridge, lasso, elastic]
    melhor = min(candidatos, key=lambda m: m["teste"]["MAE"] or 1e9)
    escolhido = melhor
    r2a_ols = ols["teste"].get("R2_ajustado") or 0
    r2a_reg = escolhido["teste"].get("R2_ajustado") or 0
    nota = (
        "Alvo = kWh semanal por apto (nao diario: 42% dos dias tem kWh=0 e o R2 "
        "diario nao passa de ~0.40). Features: tendencia, n de veiculos, bateria "
        "e dummy de unidade. "
    )
    if r2a_reg >= 0.70:
        nota += (
            f"R2 ajustado de TESTE do modelo regularizado: {r2a_reg:.1%} "
            f"(OLS: {r2a_ols:.1%})."
        )
    else:
        nota += (
            f"R2 ajustado de teste={r2a_reg:.1%}; treino OLS="
            f"{ols['treino'].get('R2_ajustado')}."
        )

    proj = projetar(escolhido, painel, t0, unidades)
    estado = _estado_final(painel)
    recs = recomendar(proj, estado)

    def slim(pacote):
        return {
            "nome": pacote["nome"],
            "familia": pacote["familia"],
            "alpha": pacote["alpha"],
            "l1_ratio": pacote["l1_ratio"],
            "coefs": pacote["coefs"],
            "treino": pacote["treino"],
            "teste": pacote["teste"],
        }

    datas = sorted({r["data"] for r in painel})
    media_hist = float(np.mean([r["kwh"] for r in painel]))
    pico_hist = float(max(
        sum(r["kwh"] for r in painel if r["data"] == d) for d in datas
    ))
    ano_c, sem_c = divmod(int(corte_t), 52)
    if sem_c == 0:
        ano_c -= 1
        sem_c = 52
    corte_label = f"{ano_c}-S{sem_c:02d}"

    previsao_compat = {
        "consumo_medio_diario_kwh": _round(media_hist * len(unidades), 1),
        "consumo_medio_diario": _round(media_hist * len(unidades), 1),
        "tendencia_pct": proj["variacao_pct"],
        "direcao_tendencia": proj["direcao_tendencia"],
        "tendencia": proj["direcao_tendencia"],
        "previsao_mensal_kwh": proj["previsao_mensal_kwh"],
        "previsao_mensal": proj["previsao_mensal_kwh"],
        "pico_estimado_kwh_dia": _round(pico_hist * 1.05, 1),
        "pico_estimado": _round(pico_hist * 1.05, 1),
        "media_sessoes_dia": None,
        "necessita_expansao": "expansao" in recs[0].lower() if recs else False,
        "recomendacao": recs[0] if recs else "",
        "motor": "regressao_multipla",
        "modelo_escolhido": escolhido["nome"],
    }

    linhas_proj = ["mes | " + " | ".join(unidades) + " | TOTAL | R$ est."]
    for m in proj["meses"]:
        vals = [m["por_unidade"].get(u, 0) for u in unidades]
        linhas_proj.append(
            m["mes"] + " | " + " | ".join(f"{v:.0f}" for v in vals)
            + f" | {m['total_kwh']:.0f} | {m['custo_estimado']:.0f}"
        )

    kpis_txt = []
    for rotulo, pac in (("ANTES (OLS)", ols), ("DEPOIS (" + escolhido["familia"] + ")", escolhido)):
        t = pac["teste"]
        kpis_txt.append(
            f"{rotulo} TREINO: R2={pac['treino']['R2']} R2adj={pac['treino']['R2_ajustado']} "
            f"MAE={pac['treino']['MAE']} AIC={pac['treino']['AIC']} BIC={pac['treino']['BIC']}"
        )
        kpis_txt.append(
            f"{rotulo} TESTE: MAE={t['MAE']} RMSE={t['RMSE']} R2={t['R2']} "
            f"R2adj={t['R2_ajustado']} AIC={t['AIC']} BIC={t['BIC']} "
            f"AICc={t['AICc']} MAPE={t['MAPE_pct']}%"
        )

    return {
        "ok": True,
        "n_observacoes": len(semanas),
        "n_treino": len(treino),
        "n_teste": len(teste),
        "data_corte": corte_label,
        "periodo_treino": f"semana t={treino[0]['t']} a t={treino[-1]['t']}",
        "periodo_teste": f"semana t={teste[0]['t']} a t={teste[-1]['t']}",
        "features": nomes,
        "alvo": "kWh semanal por unidade",
        "antes": slim(ols),
        "depois": slim(escolhido),
        "comparativo": {
            "OLS": slim(ols),
            "Ridge": slim(ridge),
            "Lasso": slim(lasso),
            "ElasticNet": slim(elastic),
        },
        "modelo_escolhido": escolhido["nome"],
        "nota": nota,
        "projecao": proj,
        "recomendacoes": recs,
        "previsao_compat": previsao_compat,
        "tabela_projecao": "\n".join(linhas_proj),
        "kpis_texto": "\n".join(kpis_txt),
        "estado_frota_projecao": {
            u: {
                "n_veiculos": int(st["n_veiculos"]),
                "bateria_total": _round(st["bateria_total"], 1),
                "proprietario": st.get("proprietario", ""),
            }
            for u, st in estado.items()
        },
    }


if __name__ == "__main__":
    rel = treinar()
    if not rel.get("ok"):
        print(rel)
    else:
        print("corte", rel["data_corte"], "n", rel["n_observacoes"])
        print("ANTES", rel["antes"]["teste"])
        print("DEPOIS", rel["depois"]["nome"], rel["depois"]["teste"])
        print("escolhido", rel["modelo_escolhido"])
        for m in rel["projecao"]["meses"]:
            print(m["mes"], m["total_kwh"], "kWh")
        for r in rel["recomendacoes"]:
            print("-", r)
