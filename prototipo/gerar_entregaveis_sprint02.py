#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera os entregaveis da Sprint 02 do EV ChargeOps (GoodWe + FIAP).

Saidas no diretorio do repositorio:
  - relatorio_ev_chargeops_v6.pdf
  - apresentacao_ev_chargeops_v6.pptx
  - relatorio_tecnico_sprint02.md
  - evidencias/ (JSON, CSV, graficos PNG)
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ev_chargeops import EVChargeOps, MotorIA
from motor_regressao import treinar

PROTO = Path(__file__).resolve().parent
REPO = PROTO.parent
EVID = REPO / "evidencias"
DADOS = REPO / "dados"
EVID.mkdir(exist_ok=True)

AZUL = (29, 53, 87)
AZUL_M = (69, 123, 157)
VERMELHO = (230, 57, 70)
VERDE = (42, 157, 143)
PRETO = (40, 40, 40)
CINZA = (100, 100, 100)

FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_I = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"


def _br(n, nd=2):
    s = f"{n:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

def carregar_plataforma():
    plat = EVChargeOps()
    plat.setup_demo()
    plat.carregar_ou_gerar_historico()
    return plat


def montar_contexto(plat, rel):
    sessoes = [s for s in plat.gerenciador.sessoes if s.status == "finalizada"]
    mes = datetime.now().strftime("%Y-%m")
    rateio = plat.faturamento.relatorio_rateio(plat.unidades, sessoes, mes)
    faturas = []
    for u in plat.unidades:
        f = plat.faturamento.gerar_fatura_mensal(u, sessoes, mes)
        faturas.append({
            "unidade": f"{u.numero}-{u.bloco}",
            "proprietario": u.proprietario,
            "sessoes": len(f.sessoes),
            "kwh": round(f.total_kwh, 2),
            "reais": round(f.total_reais, 2),
            "status": f.status,
        })
    mensal = defaultdict(lambda: {"kwh": 0.0, "sessoes": 0})
    path_m = DADOS / "consumo_mensal_6meses.csv"
    if path_m.is_file():
        with path_m.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                mensal[row["mes"]]["kwh"] += float(row["kwh"])
                mensal[row["mes"]]["sessoes"] += int(float(row["n_sessoes"]))
    previsao = (rel or {}).get("previsao_compat") or MotorIA.prever_demanda(sessoes, 30)
    return {
        "plat": plat,
        "sessoes": sessoes,
        "mes": mes,
        "rateio": rateio,
        "faturas": faturas,
        "rel": rel,
        "mensal": dict(mensal),
        "previsao": previsao,
        "kwh_total": round(sum(s.energia_kwh for s in sessoes), 1),
        "custo_total": round(sum(s.custo_total for s in sessoes), 2),
    }


# ---------------------------------------------------------------------------
# Graficos e JSON
# ---------------------------------------------------------------------------

def gerar_graficos(ctx):
    sessoes = ctx["sessoes"]
    cores = ["#1D3557", "#457B9D", "#E63946", "#2A9D8F",
             "#F4A261", "#264653", "#E9C46A", "#F77F00"]

    # 1. Rateio do mes corrente
    labels, valores = [], []
    for num, row in ctx["rateio"]["rateio_por_unidade"].items():
        labels.append(f"{num}-{row['bloco']}")
        valores.append(row["custo"])
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.bar(labels, valores, color="#1f6aa5")
    ax.set_ylabel("R$ (energia + 5% taxa admin)")
    ax.set_title(f"Rateio EV ChargeOps — {ctx['mes']}")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(EVID / "rateio_por_unidade.png", dpi=140)
    plt.close()

    # 2. Consumo mensal do semestre
    meses = sorted(ctx["mensal"])
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    ax.bar(meses, [ctx["mensal"][m]["kwh"] for m in meses], color="#E63946", alpha=0.9)
    ax.set_ylabel("kWh")
    ax.set_title("Consumo mensal do condominio (abr/2026 a out/2026)")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(EVID / "consumo_mensal_6meses.png", dpi=140)
    plt.close()

    # 3. Consumo por unidade no semestre
    unid = defaultdict(float)
    mapa = {u.id: f"{u.numero}-{u.bloco}" for u in ctx["plat"].unidades}
    for s in sessoes:
        unid[mapa.get(s.unidade_id, s.unidade_id[:6])] += s.energia_kwh
    labs = sorted(unid)
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.barh(labs, [unid[l] for l in labs], color=cores[:len(labs)])
    ax.set_xlabel("kWh no semestre")
    ax.set_title("Consumo por unidade — serie de 6 meses")
    fig.tight_layout()
    fig.savefig(EVID / "consumo_por_unidade.png", dpi=140)
    plt.close()

    # 4. Distribuicao horaria
    horas = defaultdict(int)
    for s in sessoes:
        if s.inicio:
            horas[s.inicio.hour] += 1
    fig, ax = plt.subplots(figsize=(10, 4.4))
    xs = list(range(24))
    cs = ["#E63946" if 18 <= h < 21 else "#F4A261" if h in (17, 21) else "#457B9D" for h in xs]
    ax.bar(xs, [horas.get(h, 0) for h in xs], color=cs)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{h:02d}h" for h in xs], rotation=45, fontsize=8)
    ax.set_title("Sessoes por horario (ponta em vermelho)")
    ax.set_ylabel("Sessoes")
    fig.tight_layout()
    fig.savefig(EVID / "distribuicao_horario.png", dpi=140)
    plt.close()

    # 5. Projecao
    rel = ctx["rel"]
    if rel and rel.get("ok"):
        meses_p = rel["projecao"]["meses"]
        fig, ax = plt.subplots(figsize=(9.5, 4.4))
        ax.plot([m["mes"] for m in meses_p], [m["total_kwh"] for m in meses_p],
                marker="o", color="#1D3557", lw=2)
        ax.set_ylabel("kWh projetado")
        ax.set_title(f"Projecao mensal — {rel['modelo_escolhido']}")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(EVID / "projecao_6meses.png", dpi=140)
        plt.close()

        # 6. KPIs antes/depois
        nomes = ["R2 teste", "R2 adj teste", "MAE"]
        ols = ctx["rel"]["antes"]["teste"]
        reg = ctx["rel"]["depois"]["teste"]
        a = [ols.get("R2") or 0, ols.get("R2_ajustado") or 0, (ols.get("MAE") or 0) / 100]
        b = [reg.get("R2") or 0, reg.get("R2_ajustado") or 0, (reg.get("MAE") or 0) / 100]
        x = np.arange(len(nomes))
        fig, ax = plt.subplots(figsize=(8.4, 4.4))
        ax.bar(x - 0.18, a, 0.36, label="OLS", color="#457B9D")
        ax.bar(x + 0.18, b, 0.36, label=rel["depois"]["familia"], color="#E63946")
        ax.set_xticks(x)
        ax.set_xticklabels(nomes)
        ax.set_title("Validacao hold-out: OLS vs modelo regularizado")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(EVID / "kpis_regressao.png", dpi=140)
        plt.close()


def salvar_evidencias(ctx):
    rel = ctx["rel"]
    path_json = EVID / "saida_prototipo.json"
    with path_json.open("w", encoding="utf-8") as fh:
        json.dump({
            "condominio": ctx["plat"].condominio.nome,
            "carregadores": len(ctx["plat"].carregadores),
            "unidades": len(ctx["plat"].unidades),
            "sessoes_finalizadas": len(ctx["sessoes"]),
            "kwh_semestre": ctx["kwh_total"],
            "custo_semestre": ctx["custo_total"],
            "mes_referencia": ctx["mes"],
            "rateio": ctx["rateio"],
            "faturas": ctx["faturas"],
            "ia_previsao": ctx["previsao"],
            "regressao": {
                "ok": bool(rel and rel.get("ok")),
                "modelo": (rel or {}).get("modelo_escolhido"),
                "n_observacoes": (rel or {}).get("n_observacoes"),
                "data_corte": (rel or {}).get("data_corte"),
                "antes_teste": (rel or {}).get("antes", {}).get("teste"),
                "depois_teste": (rel or {}).get("depois", {}).get("teste"),
                "tabela_projecao": (rel or {}).get("tabela_projecao"),
                "recomendacoes": (rel or {}).get("recomendacoes"),
            },
        }, fh, ensure_ascii=False, indent=2, default=str)

    path_csv = EVID / "rateio_unidades.csv"
    with path_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["unidade", "bloco", "proprietario", "sessoes", "kwh",
                    "energia_reais", "taxa_admin", "custo_com_admin"])
        for num, row in ctx["rateio"]["rateio_por_unidade"].items():
            w.writerow([num, row["bloco"], row["proprietario"], row["sessoes"],
                        row["kwh"], row["energia_reais"], row["taxa_admin"], row["custo"]])


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def gerar_markdown(ctx):
    rel = ctx["rel"] or {}
    ols = rel.get("antes", {}).get("teste", {})
    reg = rel.get("depois", {}).get("teste", {})
    proj_linhas = []
    for m in (rel.get("projecao") or {}).get("meses") or []:
        proj_linhas.append(
            f"| {m['mes']} | {_br(m['total_kwh'], 0)} | {_br(m['custo_estimado'], 2)} |"
        )
    recs = "\n".join(f"- {r}" for r in rel.get("recomendacoes") or [])
    md = f"""# Relatorio tecnico — EV ChargeOps Sprint 02

**Enterprise Challenge 2026 — GoodWe + FIAP**  
**Grupo 22** · Marcelo Bastianello Baldin · RM568746  
**Fase 6 — Comunicacao Interplanetaria**  
**Prazo:** 13/10/2026  
**Repositorio:** https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps

## 1. Problema

Infraestruturas de recarga compartilhadas em condominios nao estruturam sessao por unidade, nao aplicam tarifa horaria e nao entregam inteligencia acionavel ao sindico. O EV ChargeOps transforma as sessoes do carregador GoodWe HCA G2 em dado, rateio justo e decisao.

## 2. O que a Sprint 02 entrega

Prototipo funcional em Python/Flask (porta 5050) com:

1. Logica central: sessao RFID, kWh, tarifa ANEEL simplificada e rateio `Custo = Σ(kWh × tarifa) + 5%`.
2. Motor de IA estrutural (4 dimensoes): interpretacao, preditividade por regressao multipla, precificacao e Sindico Virtual (OpenAI).
3. Evidencias: serie de 6 meses, frota 0–3 veiculos, JSON/CSV/PNG e telas do dashboard.

Nesta execucao (semente 42, 2026-04-01 a 2026-10-04):

- **{len(ctx['sessoes'])} sessoes**, **{_br(ctx['kwh_total'], 1)} kWh** no semestre.
- Rateio de {ctx['mes']}: **R$ {_br(ctx['rateio']['total_condominio_reais'])}** (energia + 5%).
- Modelo escolhido: **{rel.get('modelo_escolhido', '—')}**.

## 3. Arquitetura

Tres camadas da Sprint 01, implementadas no prototipo:

| Camada | No prototipo |
|---|---|
| Fisica | 4 carregadores HCA G2 (7/11/22 kW), mapa Modbus 10000–30015 |
| Conectividade | Ciclo RFID → inicio → medicao → encerramento (Modbus simulado) |
| Digital | `GerenciadorSessoes`, `MotorFaturamento`, `MotorIA`, `motor_regressao.py`, Flask |

## 4. Rateio

Tarifa de sessao (dia util): fora ponta 1,0×; intermediaria 1,2×; ponta (18h–21h) 1,5×. Fim de semana fica na base.

Rateio de {ctx['mes']}:

| Unidade | Proprietario | Sessoes | kWh | R$ |
|---|---|---|---|---|
"""
    for num, row in ctx["rateio"]["rateio_por_unidade"].items():
        md += (
            f"| {num}-{row['bloco']} | {row['proprietario']} | {row['sessoes']} | "
            f"{_br(row['kwh'])} | {_br(row['custo'])} |\n"
        )
    md += f"""
Quem nao recarrega nao subsidia. Felipe Santos (302-B) vendeu o Kwid em 12/09/2026 e fecha outubro em R$ 0,00.

## 5. Motor de IA

| Dimensao | Papel |
|---|---|
| Interpretacao | Classifica sessao (normal / prolongada / baixa eficiencia) |
| Precificacao | Calcula a tarifa no encerramento; sem isso o rateio nao existe |
| Preditividade | OLS vs Ridge/Lasso/ElasticNet no kWh **semanal** por apto |
| Conversacao | Sindico Virtual via OpenAI com contexto RAG (totais, frota, KPIs, projecao) |

O kWh diario tem ~42% de zeros; o R² ajustado diario ficava ~0,25. O alvo passou a ser semanal. Hold-out cronologico (corte {rel.get('data_corte', '—')}):

| Modelo | R² teste | R² adj teste | MAE (kWh/semana) | AIC | BIC |
|---|---|---|---|---|---|
| OLS | {_br(ols.get('R2') or 0, 4)} | **{_br(ols.get('R2_ajustado') or 0, 4)}** | {_br(ols.get('MAE') or 0, 1)} | {_br(ols.get('AIC') or 0, 1)} | {_br(ols.get('BIC') or 0, 1)} |
| {rel.get('depois', {}).get('nome', 'Regularizado')} | {_br(reg.get('R2') or 0, 4)} | **{_br(reg.get('R2_ajustado') or 0, 4)}** | {_br(reg.get('MAE') or 0, 1)} | {_br(reg.get('AIC') or 0, 1)} | {_br(reg.get('BIC') or 0, 1)} |

{rel.get('nota', '')}

## 6. Projecao nov/2026–abr/2027

Frota congelada em 04/10/2026.

| Mes | kWh | R$ est. |
|---|---|---|
{chr(10).join(proj_linhas)}

{recs}

## 7. Como executar

```bash
cd prototipo
pip install -r requirements.txt
python app_ev_chargeops.py
```

http://localhost:5050 — `morador` / `sindico` / `administrador`, senha `senha`.

Chave OpenAI em `prototipo/.env` (nao versionado). Sem chave: Gemini ou fallback local.

## 8. Desvios em relacao a Sprint 01

| Planejado | Neste prototipo | Justificativa |
|---|---|---|
| OCPP 1.6J real | Ciclo + mapa Modbus simulado | Sem hardware HCA G2 no ambiente do aluno |
| PostgreSQL | Memoria | Decisao Q5 da Sprint 01 para o MVP |
| EWMA / Prophet | OLS + Ridge/Lasso/ElasticNet semanal | R² ajustado de teste acima de 70% |
| Gemini obrigatorio | OpenAI no chat; Gemini/regras como fallback | Chave fora do Git |

## 9. Rubrica

| Criterio | Onde esta |
|---|---|
| Logica central (0–3,0) | `ev_chargeops.py` + tela de rateio |
| IA estrutural (0–3,0) | `MotorIA` + `motor_regressao.py` + Sindico Virtual |
| Evidencia (0–2,0) | `evidencias/` e `dados/` |
| Autoria (0–1,0) | Codigo da Sprint 01 evoluido e documentado |
| README (0–1,0) | README.md + este relatorio |

Arquivo oficial do FIAP ON: `link_repositorio.txt` (somente o URL do GitHub). A nota so entra no boletim apos o pitch presencial de 3 minutos.
"""
    (REPO / "relatorio_tecnico_sprint02.md").write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _pdf_fonts(pdf):
    pdf.add_font("ArialU", "", FONT)
    pdf.add_font("ArialU", "B", FONT_B if os.path.isfile(FONT_B) else FONT)
    pdf.add_font("ArialU", "I", FONT_I if os.path.isfile(FONT_I) else FONT)


def gerar_pdf(ctx):
    from fpdf import FPDF

    rel = ctx["rel"] or {}
    ols = rel.get("antes", {}).get("teste", {})
    reg = rel.get("depois", {}).get("teste", {})

    class PDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            self.set_font("ArialU", "B", 9)
            self.set_text_color(*VERMELHO)
            self.cell(0, 8, "EV ChargeOps | Sprint 02 | FIAP + GoodWe 2026", align="L")
            self.cell(0, 8, "Marcelo B. Baldin — RM568746", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*VERMELHO)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font("ArialU", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")

        def h1(self, n, t):
            if self.get_y() > 250:
                self.add_page()
            self.ln(2)
            self.set_font("ArialU", "B", 14)
            self.set_text_color(*AZUL)
            self.cell(0, 9, f"{n}. {t}", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*VERMELHO)
            self.line(10, self.get_y(), 78, self.get_y())
            self.ln(3)

        def h2(self, t):
            self.set_font("ArialU", "B", 11)
            self.set_text_color(*AZUL_M)
            self.cell(0, 7, t, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*PRETO)

        def p(self, t):
            self.set_font("ArialU", "", 10)
            self.set_text_color(*PRETO)
            self.multi_cell(0, 5, t)
            self.ln(1)

        def bullet(self, t):
            if self.get_y() > 265:
                self.add_page()
            self.set_x(self.l_margin)
            self.set_font("ArialU", "", 10)
            self.set_text_color(*PRETO)
            self.multi_cell(0, 5, f"  - {t}")
            self.ln(0.5)

        def img(self, path, w=180):
            p = Path(path)
            if p.is_file():
                if self.get_y() > 165:
                    self.add_page()
                self.image(str(p), x=15, w=w)
                self.ln(4)
                self.set_x(self.l_margin)

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    _pdf_fonts(pdf)

    pdf.add_page()
    pdf.ln(38)
    pdf.set_font("ArialU", "B", 28)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 14, "EV ChargeOps", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ArialU", "", 13)
    pdf.set_text_color(*CINZA)
    pdf.cell(0, 8, "Prototipo funcional — Sprint 02", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Gestao compartilhada de recarga em condominios", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_draw_color(*VERMELHO)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("ArialU", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, "Enterprise Challenge 2026 — GoodWe + FIAP", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "Fase 6 — Comunicacao Interplanetaria | Grupo 22", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("ArialU", "B", 12)
    pdf.cell(0, 7, "Marcelo Bastianello Baldin", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ArialU", "", 11)
    pdf.cell(0, 7, "RM568746", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("ArialU", "I", 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 7, "Outubro de 2026  ·  Prazo 13/10/2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps",
             align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.h1(1, "Introducao")
    pdf.p(
        "O Enterprise Challenge 2026 pede, nesta sprint, um prototipo funcional da "
        "solucao definida na Sprint 01: registrar sessoes de recarga, calcular consumo "
        "individual, aplicar rateio justo e colocar inteligencia artificial no fluxo "
        "principal — nao como chat decorativo. Este relatorio documenta o que foi "
        "implementado, as evidencias numericas e os desvios conscientes em relacao ao plano."
    )
    pdf.p(
        "O problema permanece o do edital: em condominio, edificio corporativo ou campus, "
        "o carregador e compartilhado e a conta nao e. Sem sessao por unidade, sem tarifa "
        "horaria e sem previsao, ou todos pagam igual, ou ninguem audita o kWh."
    )
    pdf.h2("Entregavel oficial")
    pdf.p(
        "No FIAP ON a equipe envia um arquivo .TXT com o link do repositorio. O repositorio "
        "contem o codigo, o README, as evidencias e este relatorio. A nota so e lancada "
        "apos o pitch presencial de 3 minutos."
    )

    pdf.h1(2, "Solucao implementada")
    pdf.p(
        "Tres camadas, como na Sprint 01. Fisica: quatro carregadores GoodWe HCA G2 "
        "(7/11/22 kW) com mapa Modbus (status, tensao, corrente, potencia, kWh, RFID). "
        "Conectividade: ciclo autenticacao RFID, inicio, medicao e encerramento. "
        "Digital: motor de sessoes, Motor de IA 4D, faturamento com taxa de 5% e "
        "dashboard Flask para morador, sindico e administradora."
    )
    pdf.h2("Formula de rateio")
    pdf.p("Custo da unidade = soma (kWh da sessao × tarifa da sessao) + taxa administrativa de 5%.")
    pdf.p(
        "Tarifa (ANEEL, simplificada): fora ponta = base R$ 0,85/kWh; intermediaria = 1,2× "
        "(17h–18h e 21h–22h em dia util); ponta = 1,5× (18h–21h em dia util). "
        "Fim de semana permanece na base o dia todo."
    )
    pdf.h2("Numeros desta execucao (semente 42)")
    pdf.p(
        f"Condominio Residencial Parque Verde, 8 unidades, 4 carregadores. "
        f"Serie 01/04/2026 a 04/10/2026: {len(ctx['sessoes'])} sessoes e "
        f"{_br(ctx['kwh_total'], 1)} kWh. Rateio de {ctx['mes']}: "
        f"R$ {_br(ctx['rateio']['total_condominio_reais'])} (energia + 5%). "
        f"Quem nao recarrega nao subsidia: 302-B (Felipe) vendeu o Kwid em 12/09 e fecha "
        f"outubro em R$ 0,00."
    )

    pdf.h1(3, "Serie de 6 meses e frota")
    pdf.p(
        "O gerador gerar_consumo_6meses.py (semente 42) produz consumo diario (incluindo "
        "dias com kWh = 0), sessoes e agregado mensal. Cada apto pode ter 0 a 3 carros; "
        "ha cadastro, compra e venda no semestre. Sem carro no dia, nao ha sessao. "
        "Cada recarga grava placa Mercosul, marca, modelo, bateria (kWh) e autonomia."
    )
    pdf.img(EVID / "consumo_mensal_6meses.png")
    pdf.img(EVID / "consumo_por_unidade.png")

    pdf.add_page()
    pdf.h1(4, "Evidencia do rateio")
    pdf.p(
        f"Tabela do mes corrente ({ctx['mes']}), a mesma exportada em evidencias/rateio_unidades.csv. "
        "O administrador ve esse quadro no dashboard e exporta CSV para a administradora."
    )
    colunas = ["Unidade", "Proprietario", "Sess.", "kWh", "R$"]
    larg = [28, 48, 22, 42, 50]
    pdf.set_font("ArialU", "B", 8)
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(255, 255, 255)
    for t, w in zip(colunas, larg):
        pdf.cell(w, 7, t, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(*PRETO)
    fill = False
    for num, row in ctx["rateio"]["rateio_por_unidade"].items():
        pdf.set_font("ArialU", "", 8)
        pdf.set_fill_color(240, 245, 250)
        vals = [
            f"{num}-{row['bloco']}",
            row["proprietario"],
            str(row["sessoes"]),
            _br(row["kwh"]),
            _br(row["custo"]),
        ]
        for t, w in zip(vals, larg):
            pdf.cell(w, 6, t, border=1, fill=fill)
        pdf.ln()
        fill = not fill
    pdf.ln(2)
    pdf.img(EVID / "rateio_por_unidade.png")
    pdf.img(EVID / "distribuicao_horario.png")

    pdf.add_page()
    pdf.h1(5, "Motor de IA")
    pdf.p(
        "A IA entra em quatro pontos do fluxo. Interpretacao classifica a sessao "
        "(normal, prolongada, baixa eficiencia). Precificacao calcula a tarifa no "
        "encerramento — sem isso o rateio nao existe. Preditividade deixou a media "
        "movel da Sprint 01 e passou a regressao multipla no kWh semanal por apto. "
        "Conversacao: o Sindico Virtual chama a OpenAI (gpt-4o-mini) com contexto RAG "
        "(totais, tabela mensal, ranking, frota, KPIs e projecao). Sem chave, tenta "
        "Gemini e, por ultimo, regras locais."
    )
    pdf.h2("Por que a semana, e nao o dia")
    pdf.p(
        "Cerca de 42% dos dias-apto tem kWh = 0 (ninguem recarregou). Nesse alvo o "
        "R² ajustado diario ficava entre 0,25 e 0,37. Agregar por semana ISO preserva "
        "a regressao multipla e faz aparecer tendencia, numero de veiculos e perfil do apto."
    )
    pdf.h2("Validacao")
    pdf.p(
        f"Hold-out cronologico, corte {rel.get('data_corte', '—')}. "
        f"Features: tendencia temporal, n de veiculos, bateria total e dummy de unidade. "
        f"Comparados OLS, Ridge, Lasso e ElasticNet (grade de alpha 0,3 a 8)."
    )
    colunas = ["Modelo", "R2 teste", "R2 adj", "MAE", "AIC", "BIC"]
    larg = [48, 28, 28, 28, 28, 30]
    pdf.set_font("ArialU", "B", 8)
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(255, 255, 255)
    for t, w in zip(colunas, larg):
        pdf.cell(w, 7, t, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(*PRETO)
    linhas = [
        ["OLS (antes)", ols.get("R2"), ols.get("R2_ajustado"), ols.get("MAE"),
         ols.get("AIC"), ols.get("BIC")],
        [rel.get("depois", {}).get("nome", "Regularizado"),
         reg.get("R2"), reg.get("R2_ajustado"), reg.get("MAE"),
         reg.get("AIC"), reg.get("BIC")],
    ]
    fill = False
    for row in linhas:
        pdf.set_font("ArialU", "", 8)
        pdf.set_fill_color(240, 245, 250)
        vals = [row[0]] + [_br(v or 0, 4 if i < 2 else 1) for i, v in enumerate(row[1:])]
        for t, w in zip(vals, larg):
            pdf.cell(w, 6, t, border=1, fill=fill)
        pdf.ln()
        fill = not fill
    pdf.ln(2)
    pdf.p(rel.get("nota", ""))
    pdf.img(EVID / "kpis_regressao.png")

    pdf.add_page()
    pdf.h1(6, "Projecao e recomendacoes")
    pdf.p(
        "A projecao usa a frota congelada em 04/10/2026 e gera kWh mensal de "
        "novembro/2026 a abril/2027. Essas linhas alimentam a secao Regressao do "
        "sindico e o contexto do Sindico Virtual."
    )
    pdf.img(EVID / "projecao_6meses.png")
    for r in rel.get("recomendacoes") or []:
        pdf.bullet(r)

    pdf.h1(7, "Como executar")
    pdf.p("Python 3.10+ (testado com Anaconda). Dependencias em prototipo/requirements.txt.")
    pdf.set_font("ArialU", "", 9)
    pdf.set_fill_color(245, 245, 245)
    pdf.multi_cell(0, 5, "cd prototipo\npip install -r requirements.txt\npython app_ev_chargeops.py", fill=True)
    pdf.ln(2)
    pdf.p(
        "Abrir http://localhost:5050. Logins: morador, sindico e administrador, senha "
        "'senha'. O servidor carrega as 952 sessoes e treina a regressao na subida. "
        "Chave OpenAI em prototipo/.env (fora do Git)."
    )

    pdf.h1(8, "Desvios em relacao a Sprint 01")
    pdf.p("A Sprint 02 implementa o plano. Os desvios abaixo sao conscientes e constam no README, como exige o edital.")
    pdf.bullet("OCPP 1.6J real → ciclo de sessao + mapa Modbus simulado (sem HCA G2 no ambiente).")
    pdf.bullet("PostgreSQL → estruturas em memoria (decisao Q5 da Sprint 01 para o MVP).")
    pdf.bullet("EWMA/Prophet → OLS + Ridge/Lasso/ElasticNet no kWh semanal (R² adj de teste > 70%).")
    pdf.bullet("Gemini obrigatorio → OpenAI no Sindico Virtual; Gemini e regras locais como fallback.")
    pdf.p("Nao desviou: Python, RFID, tarifa alinhada a RN ANEEL 1.000/2021, formula Σ(kWh×tarifa)+5%, HCA G2 como hardware de referencia.")

    pdf.h1(9, "Rubrica")
    pdf.bullet("Logica central (0–3,0): GerenciadorSessoes, MotorFaturamento, tela de rateio.")
    pdf.bullet("IA estrutural (0–3,0): MotorIA 4D, motor_regressao.py, Sindico Virtual OpenAI.")
    pdf.bullet("Evidencia (0–2,0): evidencias/ e dados/ (JSON, CSV, PNG, telas).")
    pdf.bullet("Autoria (0–1,0): codigo da Sprint 01 evoluido; README com desvios.")
    pdf.bullet("README e organizacao (0–1,0): prototipo/, dados/ e evidencias/ separados.")

    dest = REPO / "relatorio_ev_chargeops_v6.pdf"
    pdf.output(str(dest))
    return dest


# ---------------------------------------------------------------------------
# PPTX
# ---------------------------------------------------------------------------

def gerar_pptx(ctx):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    rel = ctx["rel"] or {}
    ols = rel.get("antes", {}).get("teste", {})
    reg = rel.get("depois", {}).get("teste", {})

    V = RGBColor(230, 57, 70)
    AE = RGBColor(29, 53, 87)
    AM = RGBColor(69, 123, 157)
    C = RGBColor(100, 100, 100)
    B = RGBColor(255, 255, 255)
    P = RGBColor(40, 40, 40)
    VD = RGBColor(42, 157, 143)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def blank():
        return prs.slides.add_slide(prs.slide_layouts[6])

    def title(slide, txt, sub=None):
        box = slide.shapes.add_textbox(Inches(0.7), Inches(0.35), Inches(12), Inches(1.15))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = txt
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = AE
        if sub:
            p2 = tf.add_paragraph()
            p2.text = sub
            p2.font.size = Pt(15)
            p2.font.color.rgb = C
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.55), Inches(2.8), Pt(4))
        bar.fill.solid()
        bar.fill.fore_color.rgb = V
        bar.line.fill.background()

    def box(slide, txt, x, y, w, h, cor=AE, size=14):
        sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = cor
        sh.line.fill.background()
        tf = sh.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        p = tf.paragraphs[0]
        p.text = txt
        p.font.size = Pt(size)
        p.font.color.rgb = B
        p.font.bold = True
        return sh

    def pic(slide, path, x, y, w):
        p = Path(path)
        if p.is_file():
            slide.shapes.add_picture(str(p), Inches(x), Inches(y), width=Inches(w))

    # 1 capa
    s = blank()
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = AE
    bg.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.7), Inches(2.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "EV ChargeOps"
    p.font.size = Pt(52)
    p.font.bold = True
    p.font.color.rgb = B
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    p2.text = "Sprint 02 — prototipo funcional"
    p2.font.size = Pt(22)
    p2.font.color.rgb = RGBColor(200, 200, 200)
    p2.alignment = PP_ALIGN.CENTER
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(4.2), Inches(4.15), Inches(5), Pt(4))
    bar.fill.solid()
    bar.fill.fore_color.rgb = V
    bar.line.fill.background()
    tb2 = s.shapes.add_textbox(Inches(0.8), Inches(4.5), Inches(11.7), Inches(2.2))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    for line in (
        "Enterprise Challenge 2026 — GoodWe + FIAP",
        "Grupo 22  ·  Marcelo Bastianello Baldin  ·  RM568746",
        "Pitch presencial de 3 minutos  ·  prazo 13/10/2026",
    ):
        q = tf2.add_paragraph()
        q.text = line
        q.font.size = Pt(16)
        q.font.color.rgb = RGBColor(180, 180, 180)
        q.alignment = PP_ALIGN.CENTER

    # 2 problema
    s = blank()
    title(s, "O problema", "Carregador compartilhado, conta sem dono")
    for i, t in enumerate((
        "Sem sessao por unidade, ninguem audita o kWh.",
        "Sem tarifa horaria, ponta e fora ponta pagam igual.",
        "Sem rateio, ou todos subsidiam, ou a administradora nao cobra.",
        "Sem previsao, o sindico so reage quando a fila ja existe.",
    )):
        box(s, t, 0.7, 1.9 + i * 1.2, 12.0, 1.05, AE if i % 2 == 0 else AM, 16)

    # 3 solucao
    s = blank()
    title(s, "A solucao", "Tres camadas da Sprint 01, agora no prototipo")
    box(s, "DIGITAL\nSessoes · Rateio + 5% · Motor IA 4D · Flask", 1.5, 2.0, 10.3, 1.35, AE, 16)
    box(s, "CONECTIVIDADE\nRFID → inicio → Modbus → encerramento", 1.5, 3.55, 10.3, 1.35, AM, 16)
    box(s, "FISICA (simulada)\nGoodWe HCA G2  7 / 11 / 22 kW   mapa 10000–30015", 1.5, 5.1, 10.3, 1.35, RGBColor(80, 80, 80), 16)

    # 4 rateio
    s = blank()
    title(s, "Logica central: o rateio", "Custo = Σ (kWh × tarifa da sessao) + 5%")
    box(s, "Fora ponta\n1,0 × base", 0.7, 2.0, 3.8, 2.0, AM, 18)
    box(s, "Intermediaria\n1,2 × base", 4.75, 2.0, 3.8, 2.0, RGBColor(244, 162, 97), 18)
    box(s, "Ponta 18h–21h\n1,5 × base", 8.8, 2.0, 3.8, 2.0, V, 18)
    box(s, f"Outubro/2026 neste lote: R$ {_br(ctx['rateio']['total_condominio_reais'])}\n"
        "302-B (Felipe) vendeu o carro → R$ 0,00. Quem nao usa, nao subsidia.",
        0.7, 4.3, 11.9, 2.3, AE, 16)

    # 5 numeros
    s = blank()
    title(s, "O prototipo em numeros", "Serie reproducivel, semente 42, abr–out/2026")
    box(s, f"{len(ctx['sessoes'])}\nsessoes", 0.7, 2.1, 3.8, 2.2, AE, 22)
    box(s, f"{_br(ctx['kwh_total'], 1)}\nkWh no semestre", 4.75, 2.1, 3.8, 2.2, AM, 22)
    box(s, "8 unidades\n0 a 3 carros", 8.8, 2.1, 3.8, 2.2, VD, 22)
    box(s, "952 sessoes com placa, marca, bateria e autonomia.\n"
        "Flask na 5050 · logins morador / sindico / administrador.",
        0.7, 4.6, 11.9, 2.0, RGBColor(38, 70, 83), 16)

    # 6 grafico mensal
    s = blank()
    title(s, "Consumo do semestre", "O dashboard do sindico le esses mesmos dados")
    pic(s, EVID / "consumo_mensal_6meses.png", 0.9, 1.8, 11.5)

    # 7 IA
    s = blank()
    title(s, "IA no caminho critico", "Nao e chatbot pendurado")
    for i, (n, d, c) in enumerate((
        ("Interpretacao", "Normal, prolongada\nou baixa eficiencia", AE),
        ("Precificacao", "Tarifa no fim da\nsessao — senao nao ha rateio", AM),
        ("Preditividade", "Regressao multipla\nsemanal (Ridge)", V),
        ("Conversacao", "Sindico Virtual\nOpenAI + RAG", VD),
    )):
        box(s, f"{n}\n\n{d}", 0.55 + i * 3.2, 2.1, 3.0, 4.4, c, 16)

    # 8 regressao
    s = blank()
    title(s, "Regressao: OLS vs regularizacao",
          f"Alvo = kWh semanal · corte {rel.get('data_corte', '—')}")
    box(s, f"OLS\nR² adj teste {_br(ols.get('R2_ajustado') or 0, 2)}\n"
        f"MAE {_br(ols.get('MAE') or 0, 1)} kWh/sem", 0.7, 1.9, 6.0, 2.3, AM, 18)
    box(s, f"{rel.get('depois', {}).get('nome', 'Ridge')}\n"
        f"R² adj teste {_br(reg.get('R2_ajustado') or 0, 2)}\n"
        f"MAE {_br(reg.get('MAE') or 0, 1)} kWh/sem", 7.0, 1.9, 5.6, 2.3, V, 18)
    pic(s, EVID / "kpis_regressao.png", 1.6, 4.35, 10.0)

    # 9 projecao
    s = blank()
    title(s, "Projecao nov/2026 – abr/2027", "Frota congelada em 04/10/2026")
    pic(s, EVID / "projecao_6meses.png", 0.8, 1.75, 11.7)

    # 10 rateio chart
    s = blank()
    title(s, "Rateio do mes na tela do administrador", "Mesma formula da Sprint 01, agora com 6 meses atras")
    pic(s, EVID / "rateio_por_unidade.png", 0.8, 1.8, 11.7)

    # 11 desvios
    s = blank()
    title(s, "Desvios conscientes", "Exigencia do edital: justificar no README")
    for i, t in enumerate((
        "OCPP real → Modbus simulado (sem HCA G2 no notebook)",
        "PostgreSQL → memoria (MVP da Sprint 01)",
        "EWMA/Prophet → Ridge semanal (R² adj de teste > 70%)",
        "Gemini obrigatorio → OpenAI; Gemini e regras como fallback",
    )):
        box(s, t, 0.7, 1.9 + i * 1.2, 12.0, 1.05, AE if i % 2 == 0 else AM, 16)

    # 12 rubrica
    s = blank()
    title(s, "Rubrica e entrega", "O .TXT do FIAP ON so leva o link do GitHub")
    box(s, "Logica 0–3,0\nSessao + rateio", 0.5, 2.0, 3.0, 2.4, AE, 15)
    box(s, "IA 0–3,0\n4D + Ridge + OpenAI", 3.7, 2.0, 3.0, 2.4, AM, 15)
    box(s, "Evidencia 0–2,0\nJSON, CSV, PNG, telas", 6.9, 2.0, 3.0, 2.4, V, 15)
    box(s, "Autoria + README\n0–1,0 + 0–1,0", 10.1, 2.0, 2.7, 2.4, VD, 15)
    box(s, "github.com/marcelobaldin/EV_Challenge_EV_ChargeOps\n"
        "Pitch presencial obrigatorio. Falta na apresentacao zera o Challenge.",
        0.5, 4.7, 12.3, 2.0, AE, 16)

    # 13 fechamento
    s = blank()
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = AE
    bg.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.7), Inches(3.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Do RFID ate o item no boleto."
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = B
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    p2.text = "EV ChargeOps — Sprint 02  ·  obrigado."
    p2.font.size = Pt(20)
    p2.font.color.rgb = RGBColor(200, 200, 200)
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(16)

    dest = REPO / "apresentacao_ev_chargeops_v6.pptx"
    prs.save(str(dest))
    return dest


def main():
    os.chdir(PROTO)
    print("=== EV ChargeOps Sprint 02 — entregaveis ===")
    print("[1/6] Plataforma + historico de 6 meses...")
    plat = carregar_plataforma()
    print("[2/6] Treinando regressao...")
    rel = plat.relatorio_regressao or treinar()
    ctx = montar_contexto(plat, rel)
    print(f"      {len(ctx['sessoes'])} sessoes | {ctx['kwh_total']} kWh | "
          f"modelo {rel.get('modelo_escolhido')}")
    print("[3/6] Graficos e JSON...")
    gerar_graficos(ctx)
    salvar_evidencias(ctx)
    print("[4/6] Relatorio Markdown...")
    gerar_markdown(ctx)
    print("[5/6] PDF v6...")
    pdf = gerar_pdf(ctx)
    print(f"      {pdf}")
    print("[6/6] PPTX v6...")
    ppt = gerar_pptx(ctx)
    print(f"      {ppt}")
    print("OK")


if __name__ == "__main__":
    main()
