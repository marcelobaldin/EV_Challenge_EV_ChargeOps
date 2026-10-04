#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera evidencias de funcionamento do prototipo EV ChargeOps (Sprint 02)."""

import csv
import json
import os
import random
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ev_chargeops import EVChargeOps, MotorIA

DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidencias")
os.makedirs(DEST, exist_ok=True)

random.seed(42)

print("Gerando evidencias EV ChargeOps...")
plat = EVChargeOps()
plat.setup_demo()
plat.gerar_historico_simulado(dias=30)

sessoes = [s for s in plat.gerenciador.sessoes if s.status == "finalizada"]
mes = datetime.now().strftime("%Y-%m")
rateio = plat.faturamento.relatorio_rateio(plat.unidades, sessoes, mes)

# Faturas
faturas = []
for u in plat.unidades:
    f = plat.faturamento.gerar_fatura_mensal(u, sessoes, mes)
    faturas.append({
        "unidade": f"{u.numero}-{u.bloco}",
        "proprietario": u.proprietario,
        "sessoes": len(f.sessoes),
        "kwh": f.total_kwh,
        "reais": f.total_reais,
        "status": f.status,
    })

# IA
ia_interp = []
for s in sessoes[:8]:
    ia_interp.append(MotorIA.interpretar_sessao(s))
previsao = MotorIA.prever_demanda(sessoes, dias_projecao=30)

dados_sindico = {
    "consumo_total_kwh": sum(s.energia_kwh for s in sessoes),
    "custo_total": sum(s.custo_total for s in sessoes),
    "num_unidades_ativas": len({s.unidade_id for s in sessoes}),
    "carregadores_disponiveis": sum(1 for c in plat.carregadores if c.status != "manutencao"),
    "total_carregadores": len(plat.carregadores),
    "faturas_abertas": len(faturas),
    "total_pendente": sum(f["reais"] for f in faturas),
    "tendencia": previsao.get("direcao_tendencia"),
    "previsao_mensal_kwh": previsao.get("previsao_mensal_kwh"),
}
perguntas = [
    "Quanto o condominio gastou em kWh?",
    "Como esta o rateio e as faturas?",
    "Precisamos de mais carregadores?",
]
respostas = {q: MotorIA.sindico_virtual(q, dados_sindico) for q in perguntas}

resumo = {
    "condominio": plat.condominio.nome,
    "carregadores": len(plat.carregadores),
    "unidades": len(plat.unidades),
    "sessoes_finalizadas": len(sessoes),
    "mes_referencia": mes,
    "rateio": rateio,
    "faturas": faturas,
    "ia_interpretacao_amostra": ia_interp,
    "ia_previsao": previsao,
    "sindico_virtual": respostas,
}

path_json = os.path.join(DEST, "saida_prototipo.json")
with open(path_json, "w", encoding="utf-8") as fh:
    json.dump(resumo, fh, ensure_ascii=False, indent=2, default=str)

path_csv = os.path.join(DEST, "rateio_unidades.csv")
with open(path_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["unidade", "bloco", "proprietario", "sessoes", "kwh",
                "energia_reais", "taxa_admin", "custo_com_admin"])
    for num, row in rateio["rateio_por_unidade"].items():
        w.writerow([num, row["bloco"], row["proprietario"], row["sessoes"],
                    row["kwh"], row["energia_reais"], row["taxa_admin"], row["custo"]])

# Grafico de rateio
labels = []
valores = []
for num, row in rateio["rateio_por_unidade"].items():
    labels.append(f"{num}-{row['bloco']}")
    valores.append(row["custo"])

fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.bar(labels, valores, color="#1f6aa5")
ax.set_ylabel("R$ (energia + 5% taxa admin)")
ax.set_title(f"Rateio EV ChargeOps — {mes}")
ax.tick_params(axis="x", rotation=30)
ax.grid(True, axis="y", alpha=0.3)
fig.tight_layout()
path_png = os.path.join(DEST, "rateio_por_unidade.png")
fig.savefig(path_png, dpi=140)
plt.close()

print(f"  Sessoes: {len(sessoes)}")
print(f"  Total condominio: R$ {rateio['total_condominio_reais']:.2f}")
print(f"  Previsao mensal IA: {previsao['previsao_mensal_kwh']} kWh ({previsao['direcao_tendencia']})")
print(f"  Arquivos: {path_json}")
print(f"            {path_csv}")
print(f"            {path_png}")
print("OK")
