#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera consumo diario de 6 meses (abr-set/2026 + out/01-04) para as 8 unidades.

Saidas em ../dados/ (semente 42, reproduzivel):
  consumo_diario_6meses.csv   — 1 linha por apto por dia (inclui kWh = 0)
  consumo_sessoes_6meses.csv  — 1 linha por sessao de recarga
  consumo_mensal_6meses.csv   — agregado mensal por unidade
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from ev_chargeops import MotorIA

SEED = 42
TARIFA_BASE = 0.85
INICIO = date(2026, 4, 1)
FIM = date(2026, 10, 4)  # 6 meses fechados + dias correntes de outubro

UNIDADES = [
    ("101", "A", "Ana Silva"),
    ("102", "A", "Bruno Costa"),
    ("201", "A", "Carla Mendes"),
    ("202", "A", "Daniel Oliveira"),
    ("301", "B", "Elena Souza"),
    ("302", "B", "Felipe Santos"),
    ("401", "B", "Gabriela Lima"),
    ("402", "B", "Henrique Rocha"),
]

CARREGADORES = [
    ("GW7K-HCA-20", 7.0),
    ("GW11K-HCA-20", 11.0),
    ("GW11K-HCA-20", 11.0),
    ("GW22K-HCA-20", 22.0),
]

# Perfil de uso: probabilidade em dia util / fim de semana, faixa de kWh,
# janela de horario (pode cruzar meia-noite) e crescimento no semestre.
PERFIS = {
    "101": {"p_util": 0.88, "p_fim": 0.22, "kwh": (10, 20), "horas": (22, 5),
            "crescimento": 0.06, "carregador": 0},   # commuter noturno
    "102": {"p_util": 0.95, "p_fim": 0.70, "kwh": (16, 34), "horas": (18, 22),
            "crescimento": 0.18, "carregador": 3, "segunda_sessao": 0.32},  # heavy + ponta
    "201": {"p_util": 0.55, "p_fim": 0.45, "kwh": (12, 24), "horas": (9, 16),
            "crescimento": 0.22, "carregador": 1},   # flex, demanda crescente
    "202": {"p_util": 0.35, "p_fim": 0.80, "kwh": (14, 28), "horas": (17, 21),
            "crescimento": 0.04, "carregador": 2},   # fim de semana / intermediaria
    "301": {"p_util": 0.90, "p_fim": 0.55, "kwh": (18, 32), "horas": (21, 2),
            "crescimento": 0.12, "carregador": 3},   # heavy user
    "302": {"p_util": 0.28, "p_fim": 0.18, "kwh": (8, 16), "horas": (23, 6),
            "crescimento": 0.00, "carregador": 0},   # light
    "401": {"p_util": 0.60, "p_fim": 0.40, "kwh": (11, 22), "horas": (20, 23),
            "crescimento": 0.10, "carregador": 1},   # ferias em julho
    "402": {"p_util": 0.72, "p_fim": 0.50, "kwh": (12, 22), "horas": (0, 7),
            "crescimento": 0.08, "carregador": 2},   # madrugada, fora ponta
}


def daterange(inicio: date, fim: date):
    d = inicio
    while d <= fim:
        yield d
        d += timedelta(days=1)


def sortear_hora(h0: int, h1: int, rng: random.Random) -> int:
    if h0 <= h1:
        return rng.randint(h0, h1)
    opcoes = list(range(h0, 24)) + list(range(0, h1 + 1))
    return rng.choice(opcoes)


def em_ferias(unidade: str, dia: date) -> bool:
    return unidade == "401" and date(2026, 7, 12) <= dia <= date(2026, 7, 26)


def fator_sazonal(dia: date) -> float:
    # Jun-ago: mais recarga residencial
    return 1.10 if dia.month in (6, 7, 8) else 1.0


def montar_sessao(dia: date, unidade: str, bloco: str, prop: str,
                  perfil: dict, progresso: float, rng: random.Random) -> dict:
    h0, h1 = perfil["horas"]
    hora = sortear_hora(h0, h1, rng)
    minuto = rng.randint(0, 59)
    inicio = datetime(dia.year, dia.month, dia.day, hora, minuto)
    lo, hi = perfil["kwh"]
    kwh = rng.uniform(lo, hi) * (1.0 + perfil["crescimento"] * progresso)
    kwh *= fator_sazonal(dia)
    kwh = round(kwh, 2)

    idx = perfil["carregador"] % len(CARREGADORES)
    modelo, potencia = CARREGADORES[idx]
    duracao_h = round(max(0.5, min(6.5, kwh / (potencia * rng.uniform(0.70, 0.92)))), 2)
    tarifa, tipo = MotorIA.calcular_tarifa(inicio, TARIFA_BASE)
    custo = round(kwh * tarifa, 2)
    return {
        "data": dia.isoformat(),
        "hora": f"{hora:02d}:{minuto:02d}",
        "duracao_h": duracao_h,
        "unidade": unidade,
        "bloco": bloco,
        "proprietario": prop,
        "kwh": kwh,
        "tarifa": tarifa,
        "tipo_tarifa": tipo,
        "custo": custo,
        "carregador_modelo": modelo,
        "potencia_kw": potencia,
        "inicio_iso": inicio.isoformat(timespec="minutes"),
    }


def main() -> None:
    rng = random.Random(SEED)
    dest = Path(__file__).resolve().parent.parent / "dados"
    dest.mkdir(parents=True, exist_ok=True)

    dias = list(daterange(INICIO, FIM))
    n_dias = len(dias)
    sessoes = []
    diario = []

    for i, dia in enumerate(dias):
        progresso = i / max(n_dias - 1, 1)
        util = dia.weekday() < 5
        for unidade, bloco, prop in UNIDADES:
            perfil = PERFIS[unidade]
            kwh_dia = 0.0
            custo_dia = 0.0
            n_ses = 0
            ponta = inter = fora = 0.0

            if em_ferias(unidade, dia):
                p = 0.0
            else:
                p = perfil["p_util"] if util else perfil["p_fim"]

            n_hoje = 0
            if rng.random() < p:
                n_hoje = 1
                if rng.random() < perfil.get("segunda_sessao", 0):
                    n_hoje = 2

            for _ in range(n_hoje):
                s = montar_sessao(dia, unidade, bloco, prop, perfil, progresso, rng)
                sessoes.append(s)
                n_ses += 1
                kwh_dia += s["kwh"]
                custo_dia += s["custo"]
                if s["tipo_tarifa"] == "ponta":
                    ponta += s["kwh"]
                elif s["tipo_tarifa"] == "intermediaria":
                    inter += s["kwh"]
                else:
                    fora += s["kwh"]

            diario.append({
                "data": dia.isoformat(),
                "unidade": unidade,
                "bloco": bloco,
                "proprietario": prop,
                "kwh": round(kwh_dia, 2),
                "n_sessoes": n_ses,
                "custo": round(custo_dia, 2),
                "kwh_ponta": round(ponta, 2),
                "kwh_intermediaria": round(inter, 2),
                "kwh_fora_ponta": round(fora, 2),
            })

    path_ses = dest / "consumo_sessoes_6meses.csv"
    with path_ses.open("w", newline="", encoding="utf-8") as fh:
        campos = ["data", "hora", "duracao_h", "unidade", "bloco", "proprietario",
                  "kwh", "tarifa", "tipo_tarifa", "custo", "carregador_modelo",
                  "potencia_kw", "inicio_iso"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(sessoes)

    path_dia = dest / "consumo_diario_6meses.csv"
    with path_dia.open("w", newline="", encoding="utf-8") as fh:
        campos = ["data", "unidade", "bloco", "proprietario", "kwh", "n_sessoes",
                  "custo", "kwh_ponta", "kwh_intermediaria", "kwh_fora_ponta"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(diario)

    mensal = defaultdict(lambda: {"kwh": 0.0, "custo": 0.0, "sessoes": 0, "dias": 0})
    meta = {}
    for row in diario:
        mes = row["data"][:7]
        chave = (mes, row["unidade"])
        mensal[chave]["kwh"] += row["kwh"]
        mensal[chave]["custo"] += row["custo"]
        mensal[chave]["sessoes"] += row["n_sessoes"]
        if row["kwh"] > 0:
            mensal[chave]["dias"] += 1
        meta[row["unidade"]] = (row["bloco"], row["proprietario"])

    path_mes = dest / "consumo_mensal_6meses.csv"
    with path_mes.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mes", "unidade", "bloco", "proprietario", "kwh",
                    "n_sessoes", "custo", "dias_com_recarga"])
        for (mes, unidade) in sorted(mensal):
            bloco, prop = meta[unidade]
            m = mensal[(mes, unidade)]
            w.writerow([mes, unidade, bloco, prop, round(m["kwh"], 2),
                        m["sessoes"], round(m["custo"], 2), m["dias"]])

    kwh_total = sum(s["kwh"] for s in sessoes)
    print(f"  Periodo: {INICIO} a {FIM} ({n_dias} dias, 8 unidades)")
    print(f"  Linhas diarias: {len(diario)} (todas as unidades, todos os dias)")
    print(f"  Sessoes: {len(sessoes)}")
    print(f"  Energia: {kwh_total:.1f} kWh")
    print(f"  {path_dia}")
    print(f"  {path_ses}")
    print(f"  {path_mes}")


if __name__ == "__main__":
    main()
