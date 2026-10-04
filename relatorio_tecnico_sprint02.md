# Relatorio tecnico — EV ChargeOps Sprint 02

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

- **952 sessoes**, **28.501,4 kWh** no semestre.
- Rateio de 2026-10: **R$ 634,12** (energia + 5%).
- Modelo escolhido: **Ridge (alpha=8)**.

## 3. Arquitetura

Tres camadas da Sprint 01, implementadas no prototipo:

| Camada | No prototipo |
|---|---|
| Fisica | 4 carregadores HCA G2 (7/11/22 kW), mapa Modbus 10000–30015 |
| Conectividade | Ciclo RFID → inicio → medicao → encerramento (Modbus simulado) |
| Digital | `GerenciadorSessoes`, `MotorFaturamento`, `MotorIA`, `motor_regressao.py`, Flask |

## 4. Rateio

Tarifa de sessao (dia util): fora ponta 1,0×; intermediaria 1,2×; ponta (18h–21h) 1,5×. Fim de semana fica na base.

Rateio de 2026-10:

| Unidade | Proprietario | Sessoes | kWh | R$ |
|---|---|---|---|---|
| 101-A | Ana Silva | 2 | 38,67 | 34,51 |
| 102-A | Bruno Costa | 4 | 106,46 | 105,89 |
| 201-A | Carla Mendes | 3 | 112,12 | 100,06 |
| 202-A | Daniel Oliveira | 2 | 64,51 | 57,57 |
| 301-B | Elena Souza | 4 | 158,61 | 141,55 |
| 302-B | Felipe Santos | 0 | 0,00 | 0,00 |
| 401-B | Gabriela Lima | 3 | 82,75 | 85,01 |
| 402-B | Henrique Rocha | 3 | 122,71 | 109,53 |

Quem nao recarrega nao subsidia. Felipe Santos (302-B) vendeu o Kwid em 12/09/2026 e fecha outubro em R$ 0,00.

## 5. Motor de IA

| Dimensao | Papel |
|---|---|
| Interpretacao | Classifica sessao (normal / prolongada / baixa eficiencia) |
| Precificacao | Calcula a tarifa no encerramento; sem isso o rateio nao existe |
| Preditividade | OLS vs Ridge/Lasso/ElasticNet no kWh **semanal** por apto |
| Conversacao | Sindico Virtual via OpenAI com contexto RAG (totais, frota, KPIs, projecao) |

O kWh diario tem ~42% de zeros; o R² ajustado diario ficava ~0,25. O alvo passou a ser semanal. Hold-out cronologico (corte 2026-S32):

| Modelo | R² teste | R² adj teste | MAE (kWh/semana) | AIC | BIC |
|---|---|---|---|---|---|
| OLS | 0,7998 | **0,7631** | 37,7 | 587,3 | 614,6 |
| Ridge (alpha=8) | 0,8064 | **0,7709** | 36,1 | 584,9 | 612,2 |

Alvo = kWh semanal por apto (nao diario: 42% dos dias tem kWh=0 e o R2 diario nao passa de ~0.40). Features: tendencia, n de veiculos, bateria e dummy de unidade. R2 ajustado de TESTE do modelo regularizado: 77.1% (OLS: 76.3%).

## 6. Projecao nov/2026–abr/2027

Frota congelada em 04/10/2026.

| Mes | kWh | R$ est. |
|---|---|---|
| 2026-11 | 5.314 | 4.742,57 |
| 2026-12 | 5.622 | 5.017,41 |
| 2027-01 | 5.726 | 5.110,47 |
| 2027-02 | 5.290 | 4.720,99 |
| 2027-03 | 6.001 | 5.356,27 |
| 2027-04 | 5.951 | 5.311,25 |

- ALERTA de expansao: o pico projetado e 6001 kWh/mes (media 5651). Com 4 carregadores (44 kW), recomendar assembleia para 5o ponto HCA G2.
- Unidades sem veiculo cadastrado no horizonte (302-B): projecao proxima de zero. Nao ratear ocioso; vaga fica para os demais ate novo cadastro.
- Maior carga projetada no ultimo mes: 301-B com 1421 kWh. Orientar recarga apos 22h (fora ponta) e, se houver 2+ carros, escalonar sessoes para nao coincidir na ponta 18-21h.
- Custo estimado do semestre projetado (energia + 5% admin, tarifa base): R$ 30258.97. Levar o quadro mes a mes para a proxima assembleia.

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
