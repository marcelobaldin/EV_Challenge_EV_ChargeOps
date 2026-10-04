#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera consumo diario de 6 meses (abr-set/2026 + out/01-04) para as 8 unidades.

Cada unidade pode ter 0 a 3 veiculos cadastrados. A frota muda com compras e
vendas; so recarrega quem tem carro ativo naquele dia. kWh da sessao e fração
da bateria do veiculo usado.

Saidas em ../dados/ (semente 42, reproduzivel):
  consumo_diario_6meses.csv
  consumo_sessoes_6meses.csv
  consumo_mensal_6meses.csv
  frota_cadastro_6meses.csv     — um periodo de posse por placa
  frota_eventos_6meses.csv      — cadastro inicial, compra e venda
  frota_diaria_6meses.csv       — snapshot diario (n carros e placas)
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from ev_chargeops import MotorIA

SEED = 42
TARIFA_BASE = 0.85
INICIO = date(2026, 4, 1)
FIM = date(2026, 10, 4)

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

PERFIS = {
    "101": {"p_util": 0.88, "p_fim": 0.22, "kwh": (10, 20), "horas": (22, 5),
            "crescimento": 0.06, "carregador": 0},
    "102": {"p_util": 0.95, "p_fim": 0.70, "kwh": (16, 34), "horas": (18, 22),
            "crescimento": 0.18, "carregador": 3, "segunda_sessao": 0.32},
    "201": {"p_util": 0.55, "p_fim": 0.45, "kwh": (12, 24), "horas": (9, 16),
            "crescimento": 0.22, "carregador": 1},
    "202": {"p_util": 0.35, "p_fim": 0.80, "kwh": (14, 28), "horas": (17, 21),
            "crescimento": 0.04, "carregador": 2},
    "301": {"p_util": 0.90, "p_fim": 0.55, "kwh": (18, 32), "horas": (21, 2),
            "crescimento": 0.12, "carregador": 3},
    "302": {"p_util": 0.28, "p_fim": 0.18, "kwh": (8, 16), "horas": (23, 6),
            "crescimento": 0.00, "carregador": 0},
    "401": {"p_util": 0.60, "p_fim": 0.40, "kwh": (11, 22), "horas": (20, 23),
            "crescimento": 0.10, "carregador": 1},
    "402": {"p_util": 0.72, "p_fim": 0.50, "kwh": (12, 22), "horas": (0, 7),
            "crescimento": 0.08, "carregador": 2},
}

# Posse: ate 3 carros por apto. fim=None = ainda cadastrado em 2026-10-04.
# 302 vende o unico carro em setembro (fica com zero). 202 e 401 tem buraco
# entre venda e compra. 102 chega a 3 no inverno e volta a 2.
SPELLS = [
    ("101", "BYD", "Dolphin Mini", 38.0, 280, date(2026, 4, 1), None),
    ("102", "Tesla", "Model 3 RWD", 60.0, 450, date(2026, 4, 1), None),
    ("102", "Chevrolet", "Bolt EUV", 65.0, 400, date(2026, 4, 1), date(2026, 8, 18)),
    ("102", "BMW", "iX1", 66.5, 430, date(2026, 6, 8), None),
    ("201", "GWM", "Ora 03 Skin", 48.0, 310, date(2026, 4, 1), None),
    ("201", "Volvo", "EX30", 51.0, 340, date(2026, 6, 15), None),
    ("202", "Nissan", "Leaf", 40.0, 270, date(2026, 4, 1), date(2026, 7, 20)),
    ("202", "Fiat", "500e", 42.0, 300, date(2026, 8, 5), None),
    ("301", "BYD", "Seal", 82.5, 520, date(2026, 4, 1), None),
    ("301", "BYD", "Yuan Plus", 60.5, 430, date(2026, 5, 10), None),
    ("302", "Renault", "Kwid E-Tech", 26.8, 185, date(2026, 4, 1), date(2026, 9, 12)),
    ("401", "Caoa Chery", "iCar", 31.0, 250, date(2026, 4, 1), date(2026, 7, 8)),
    ("401", "Peugeot", "e-208", 51.0, 360, date(2026, 8, 1), None),
    ("402", "JAC", "e-JS1", 30.2, 300, date(2026, 4, 1), None),
    ("402", "Hyundai", "Ioniq 5", 77.4, 480, date(2026, 9, 1), None),
]


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
    return 1.10 if dia.month in (6, 7, 8) else 1.0


def nova_placa(rng: random.Random, usadas: set) -> str:
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    while True:
        placa = (
            "".join(rng.choice(letras) for _ in range(3))
            + str(rng.randint(0, 9))
            + rng.choice(letras)
            + f"{rng.randint(0, 99):02d}"
        )
        if placa not in usadas:
            usadas.add(placa)
            return placa


def montar_frota(rng: random.Random) -> list:
    usadas: set = set()
    frota = []
    por_unidade = defaultdict(list)
    for unidade, marca, modelo, bat, auto, inicio, fim in SPELLS:
        spell = {
            "unidade": unidade,
            "marca": marca,
            "modelo": modelo,
            "bateria_kwh": bat,
            "autonomia_km": auto,
            "inicio": inicio,
            "fim": fim,
            "placa": nova_placa(rng, usadas),
        }
        ativos = veiculos_no_intervalo(por_unidade[unidade], inicio, fim or FIM)
        if len(ativos) >= 3:
            raise RuntimeError(f"{unidade} excederia 3 veiculos em {inicio}")
        por_unidade[unidade].append(spell)
        frota.append(spell)
    return frota


def veiculos_no_intervalo(spells: list, inicio: date, fim: date) -> list:
    out = []
    for v in spells:
        v_fim = v["fim"] or FIM
        if v["inicio"] <= fim and v_fim >= inicio:
            out.append(v)
    return out


def veiculos_no_dia(frota: list, unidade: str, dia: date) -> list:
    out = []
    for v in frota:
        if v["unidade"] != unidade:
            continue
        if v["inicio"] <= dia and (v["fim"] is None or dia <= v["fim"]):
            out.append(v)
    return out


def kwh_da_sessao(veiculo: dict, perfil: dict, progresso: float,
                  dia: date, rng: random.Random) -> float:
    bat = float(veiculo["bateria_kwh"])
    lo_frac, hi_frac = 0.28, 0.78
    if perfil["kwh"][1] <= 16:
        lo_frac, hi_frac = 0.25, 0.58
    kwh = rng.uniform(lo_frac, hi_frac) * bat
    kwh *= 1.0 + perfil["crescimento"] * progresso
    kwh *= fator_sazonal(dia)
    kwh = min(kwh, bat * 0.92)
    return round(max(4.0, kwh), 2)


def montar_sessao(dia: date, unidade: str, bloco: str, prop: str,
                  perfil: dict, progresso: float, veiculo: dict,
                  rng: random.Random) -> dict:
    h0, h1 = perfil["horas"]
    hora = sortear_hora(h0, h1, rng)
    minuto = rng.randint(0, 59)
    inicio = datetime(dia.year, dia.month, dia.day, hora, minuto)
    kwh = kwh_da_sessao(veiculo, perfil, progresso, dia, rng)

    idx = perfil["carregador"] % len(CARREGADORES)
    modelo_chg, potencia = CARREGADORES[idx]
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
        "carregador_modelo": modelo_chg,
        "potencia_kw": potencia,
        "inicio_iso": inicio.isoformat(timespec="minutes"),
        "placa": veiculo["placa"],
        "marca": veiculo["marca"],
        "modelo_veiculo": veiculo["modelo"],
        "bateria_kwh": veiculo["bateria_kwh"],
        "autonomia_km": veiculo["autonomia_km"],
    }


def iso(d: Optional[date]) -> str:
    return d.isoformat() if d else ""


def main() -> None:
    rng = random.Random(SEED)
    dest = Path(__file__).resolve().parent.parent / "dados"
    dest.mkdir(parents=True, exist_ok=True)
    frota = montar_frota(rng)
    meta = {u: (b, p) for u, b, p in UNIDADES}

    cadastro = []
    eventos = []
    for v in frota:
        bloco, prop = meta[v["unidade"]]
        cadastro.append({
            "placa": v["placa"],
            "marca": v["marca"],
            "modelo": v["modelo"],
            "bateria_kwh": v["bateria_kwh"],
            "autonomia_km": v["autonomia_km"],
            "unidade": v["unidade"],
            "bloco": bloco,
            "proprietario": prop,
            "data_inicio": iso(v["inicio"]),
            "data_fim": iso(v["fim"]),
            "status": "vendido" if v["fim"] else "ativo",
        })
        if v["inicio"] <= INICIO:
            eventos.append({
                "data": iso(INICIO), "unidade": v["unidade"], "bloco": bloco,
                "proprietario": prop, "evento": "cadastro_inicial",
                "placa": v["placa"], "marca": v["marca"], "modelo": v["modelo"],
                "bateria_kwh": v["bateria_kwh"], "autonomia_km": v["autonomia_km"],
            })
        else:
            eventos.append({
                "data": iso(v["inicio"]), "unidade": v["unidade"], "bloco": bloco,
                "proprietario": prop, "evento": "compra",
                "placa": v["placa"], "marca": v["marca"], "modelo": v["modelo"],
                "bateria_kwh": v["bateria_kwh"], "autonomia_km": v["autonomia_km"],
            })
        if v["fim"] is not None:
            eventos.append({
                "data": iso(v["fim"]), "unidade": v["unidade"], "bloco": bloco,
                "proprietario": prop, "evento": "venda",
                "placa": v["placa"], "marca": v["marca"], "modelo": v["modelo"],
                "bateria_kwh": v["bateria_kwh"], "autonomia_km": v["autonomia_km"],
            })
    eventos.sort(key=lambda e: (e["data"], e["unidade"], e["evento"]))

    dias = list(daterange(INICIO, FIM))
    n_dias = len(dias)
    sessoes = []
    diario = []
    frota_diaria = []

    for i, dia in enumerate(dias):
        progresso = i / max(n_dias - 1, 1)
        util = dia.weekday() < 5
        for unidade, bloco, prop in UNIDADES:
            perfil = PERFIS[unidade]
            ativos = veiculos_no_dia(frota, unidade, dia)
            frota_diaria.append({
                "data": dia.isoformat(),
                "unidade": unidade,
                "bloco": bloco,
                "proprietario": prop,
                "n_veiculos": len(ativos),
                "placas": "|".join(v["placa"] for v in ativos),
                "veiculos": " | ".join(
                    f"{v['marca']} {v['modelo']} ({v['placa']}, {v['bateria_kwh']} kWh, {v['autonomia_km']} km)"
                    for v in ativos
                ),
            })

            kwh_dia = 0.0
            custo_dia = 0.0
            n_ses = 0
            ponta = inter = fora = 0.0

            if em_ferias(unidade, dia) or not ativos:
                p = 0.0
            else:
                p = perfil["p_util"] if util else perfil["p_fim"]

            n_hoje = 0
            if rng.random() < p:
                n_hoje = 1
                p2 = perfil.get("segunda_sessao", 0.0)
                if len(ativos) >= 2:
                    p2 = max(p2, 0.22)
                if rng.random() < p2:
                    n_hoje = 2

            usados = []
            disponiveis = list(ativos)
            for _ in range(n_hoje):
                if not disponiveis:
                    disponiveis = list(ativos)
                veiculo = rng.choice(disponiveis)
                disponiveis = [x for x in disponiveis if x["placa"] != veiculo["placa"]]
                usados.append(veiculo["placa"])
                s = montar_sessao(dia, unidade, bloco, prop, perfil, progresso, veiculo, rng)
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
                "n_veiculos": len(ativos),
                "placas": "|".join(v["placa"] for v in ativos),
            })

    path_ses = dest / "consumo_sessoes_6meses.csv"
    with path_ses.open("w", newline="", encoding="utf-8") as fh:
        campos = ["data", "hora", "duracao_h", "unidade", "bloco", "proprietario",
                  "kwh", "tarifa", "tipo_tarifa", "custo", "carregador_modelo",
                  "potencia_kw", "inicio_iso", "placa", "marca", "modelo_veiculo",
                  "bateria_kwh", "autonomia_km"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(sessoes)

    path_dia = dest / "consumo_diario_6meses.csv"
    with path_dia.open("w", newline="", encoding="utf-8") as fh:
        campos = ["data", "unidade", "bloco", "proprietario", "kwh", "n_sessoes",
                  "custo", "kwh_ponta", "kwh_intermediaria", "kwh_fora_ponta",
                  "n_veiculos", "placas"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(diario)

    mensal = defaultdict(lambda: {"kwh": 0.0, "custo": 0.0, "sessoes": 0, "dias": 0})
    for row in diario:
        mes = row["data"][:7]
        chave = (mes, row["unidade"])
        mensal[chave]["kwh"] += row["kwh"]
        mensal[chave]["custo"] += row["custo"]
        mensal[chave]["sessoes"] += row["n_sessoes"]
        if row["kwh"] > 0:
            mensal[chave]["dias"] += 1

    path_mes = dest / "consumo_mensal_6meses.csv"
    with path_mes.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mes", "unidade", "bloco", "proprietario", "kwh",
                    "n_sessoes", "custo", "dias_com_recarga"])
        for mes, unidade in sorted(mensal):
            bloco, prop = meta[unidade]
            m = mensal[(mes, unidade)]
            w.writerow([mes, unidade, bloco, prop, round(m["kwh"], 2),
                        m["sessoes"], round(m["custo"], 2), m["dias"]])

    path_cad = dest / "frota_cadastro_6meses.csv"
    with path_cad.open("w", newline="", encoding="utf-8") as fh:
        campos = ["placa", "marca", "modelo", "bateria_kwh", "autonomia_km",
                  "unidade", "bloco", "proprietario", "data_inicio", "data_fim",
                  "status"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(cadastro)

    path_evt = dest / "frota_eventos_6meses.csv"
    with path_evt.open("w", newline="", encoding="utf-8") as fh:
        campos = ["data", "unidade", "bloco", "proprietario", "evento", "placa",
                  "marca", "modelo", "bateria_kwh", "autonomia_km"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(eventos)

    path_fd = dest / "frota_diaria_6meses.csv"
    with path_fd.open("w", newline="", encoding="utf-8") as fh:
        campos = ["data", "unidade", "bloco", "proprietario", "n_veiculos",
                  "placas", "veiculos"]
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(frota_diaria)

    kwh_total = sum(s["kwh"] for s in sessoes)
    por_placa = defaultdict(float)
    for s in sessoes:
        por_placa[s["placa"]] += s["kwh"]
    n_zero = sum(1 for r in frota_diaria if r["n_veiculos"] == 0)
    ativos_fim = sum(1 for v in frota if v["fim"] is None)

    print(f"  Periodo: {INICIO} a {FIM} ({n_dias} dias, 8 unidades)")
    print(f"  Veiculos cadastrados (periodos de posse): {len(frota)}")
    print(f"  Ativos em {FIM}: {ativos_fim} | dias-apto sem carro: {n_zero}")
    print(f"  Eventos: {len(eventos)}")
    print(f"  Linhas diarias: {len(diario)}")
    print(f"  Sessoes: {len(sessoes)}")
    print(f"  Energia: {kwh_total:.1f} kWh")
    print(f"  {path_dia}")
    print(f"  {path_ses}")
    print(f"  {path_mes}")
    print(f"  {path_cad}")
    print(f"  {path_evt}")
    print(f"  {path_fd}")
    print("  Consumo por placa:")
    placa_meta = {v["placa"]: v for v in frota}
    for placa, kwh in sorted(por_placa.items(), key=lambda x: -x[1]):
        v = placa_meta[placa]
        print(f"    {placa} {v['marca']} {v['modelo']} ({v['unidade']}): {kwh:.1f} kWh")


if __name__ == "__main__":
    main()
