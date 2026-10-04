# EV ChargeOps — Sprint 02

**Enterprise Challenge 2026 — GoodWe + FIAP**  
**Grupo 22** · Marcelo Bastianello Baldin · RM568746  
**Fase 6 — Comunicação Interplanetária**  
**Prazo:** 13/10/2026

Protótipo funcional da plataforma de gestão compartilhada de recarga de veículos elétricos em condomínios. Implementa a arquitetura, o rateio e o Motor de IA definidos na Sprint 01 e evolui o MVP com série de 6 meses, frota por unidade, Síndico Virtual na OpenAI e previsão por regressão múltipla.

Repositório: https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps

---

## Problema

Infraestruturas de recarga compartilhadas (condomínios, edifícios corporativos, campus) não estruturam sessões por unidade, não calculam consumo individual com tarifa horária e não oferecem inteligência acionável para o síndico. O EV ChargeOps transforma sessões do carregador GoodWe HCA G2 em dados, rateio justo e decisão.

## Solução implementada

Três camadas, como na Sprint 01:

1. **Física (simulada):** 4 carregadores HCA G2 (7/11/22 kW) com mapa Modbus (status, tensão, corrente, potência, kWh, RFID).
2. **Conectividade:** simulador Modbus TCP / ciclo de sessão (autenticação RFID → início → medição → encerramento).
3. **Digital:** motor de sessões, Motor de IA 4D, faturamento com taxa administrativa de 5% e dashboard Flask (morador, síndico, administradora).

Fórmula de rateio (Sprint 01):

```
Custo_Unidade = Σ (kWh_sessão_i × Tarifa_sessão_i) + Taxa_Admin (5%)
```

Tarifa dinâmica (ANEEL, simplificada para o protótipo):

| Período | Horário (dia útil) | Fator |
|---|---|---|
| Fora ponta | 22h–17h e fins de semana | 1,0 × base |
| Intermediária | 17h–18h e 21h–22h | 1,2 × base |
| Ponta | 18h–21h | 1,5 × base |

O Motor de IA não é um chat decorativo. Ele entra no fluxo:

| Dimensão | Papel no protótipo |
|---|---|
| Interpretação | Classifica sessão (normal / prolongada / baixa eficiência) e gera alertas |
| Preditividade | Regressão múltipla (OLS vs Ridge/Lasso/ElasticNet) no **kWh semanal por apto**; KPIs MAE, RMSE, MAPE, R², R² ajustado, AIC, AICc, BIC; projeção mês a mês dos próximos 6 meses |
| Precificação | Calcula a tarifa de cada sessão no momento do encerramento |
| Conversação | Síndico Virtual via **OpenAI** (`OPENAI_API_KEY`); Gemini e regras locais só como fallback |

---

## O que esta versão entrega (além da Sprint 01)

### 1. Série de 6 meses (abr/2026 a 04/out/2026)

Gerador reproduzível (`gerar_consumo_6meses.py`, semente 42): 8 unidades, consumo diário (incluindo kWh = 0), sessões e agregado mensal. O Flask carrega `dados/consumo_sessoes_6meses.csv` na subida.

### 2. Frota por condômino

Cada apto pode ter **0 a 3 carros**. Há cadastro inicial, compra e venda no semestre. Sem carro no dia, não há sessão. Cada recarga grava placa, marca, modelo, bateria (kWh) e autonomia (km).

### 3. Síndico Virtual na OpenAI

O chat envia contexto RAG (não inventa número): totais do período, tabela mensal, últimos 14 dias, ranking do semestre, rateio só do mês corrente, frota ativa, eventos de compra/venda, kWh por placa, KPIs da regressão, projeção de 6 meses e recomendações derivadas.

### 4. Motor de regressão (seção no painel do síndico)

O kWh **diário** tem ~42% de zeros; o R² ajustado ficava ~0,25. O alvo passou a ser **kWh semanal por unidade** (tendência, nº de veículos, bateria, dummy de apto). Hold-out cronológico (corte ~semana 32/2026):

| Modelo | R² teste | R² ajustado teste | MAE (kWh/semana) | AIC | BIC |
|---|---|---|---|---|---|
| OLS (antes) | 0,80 | **0,76** | 37,7 | 587 | 615 |
| Ridge α = 8 (depois) | 0,81 | **0,77** | 36,1 | 585 | 612 |

A seção **Regressão** mostra coeficientes, KPIs antes/depois, gráfico e tabela da projeção nov/2026–abr/2027 e as recomendações (expansão, ponta, apto sem carro). Essas recomendações alimentam o Síndico Virtual.

---

## Como executar

Requisitos: Python 3.10+ (testado com Anaconda). Dependências em `prototipo/requirements.txt` (Flask, OpenAI, matplotlib, numpy, scikit-learn).

```bash
cd prototipo
pip install -r requirements.txt
python app_ev_chargeops.py
```

Abrir http://localhost:5050

| Usuário | Senha | Perfil |
|---|---|---|
| `morador` | `senha` | Ana Silva, unidade 101-A |
| `sindico` | `senha` | Dashboard, ranking, análise IA, **Regressão**, Síndico Virtual |
| `administrador` | `senha` | Faturas, rateio e exportação CSV |

O servidor sobe com o condomínio demo (8 unidades, 4 carregadores), carrega as 952 sessões dos 6 meses e treina a regressão na inicialização.

Para regenerar a série de consumo e a frota:

```bash
cd prototipo
python gerar_consumo_6meses.py
```

Para regenerar evidências em lote (JSON, CSV e gráfico):

```bash
cd prototipo
python gerar_evidencias.py
```

O Síndico Virtual usa a API da OpenAI (padrão: `gpt-4o-mini`). Crie `prototipo/.env` (não versionado) com:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Sem a chave, tenta Gemini (`GEMINI_API_KEY`) e, por último, o fallback local por regras.

---

## Organização do repositório

```
README.md                          ← este arquivo
link_repositorio.txt               ← entregável oficial FIAP ON (.TXT)
relatorio_ev_chargeops_v6.pdf      ← relatório técnico da Sprint 02
apresentacao_ev_chargeops_v6.pptx  ← slides do pitch
relatorio_tecnico_sprint02.md      ← mesma narrativa em Markdown
instalacao_ev_chargeops.md         ← guia de instalação
roteiro_video.md                   ← pitch presencial de 3 minutos
sprint01_pesquisa_documentacao.md  ← base da Sprint 01 (reaproveitada)
prototipo/
  ev_chargeops.py                  ← núcleo (sessões, Modbus, IA, rateio)
  app_ev_chargeops.py              ← Flask na porta 5050
  gerar_consumo_6meses.py          ← série de 6 meses + frota (semente 42)
  motor_regressao.py               ← OLS vs Ridge/Lasso/ElasticNet + projeção
  gerar_evidencias.py
  requirements.txt
  templates/login.html
  templates/dashboard.html         ← inclui a seção Regressão do síndico
dados/
  consumo_diario_6meses.csv
  consumo_sessoes_6meses.csv
  consumo_mensal_6meses.csv
  frota_cadastro_6meses.csv
  frota_eventos_6meses.csv
  frota_diaria_6meses.csv
evidencias/
  saida_prototipo.json
  rateio_unidades.csv
  rateio_por_unidade.png
  consumo_mensal_6meses.png
  consumo_por_unidade.png
  distribuicao_horario.png
  kpis_regressao.png
  projecao_6meses.png
  tela_login.png
  tela_sindico_dashboard.png
  tela_sindico_ranking.png
  tela_sindico_ia.png
  tela_sindico_regressao.png
  tela_sindico_virtual.png
  tela_admin_rateio.png
  tela_admin_faturas.png
```

---

## Evidências de funcionamento (execução de 04/10/2026)

Condomínio Residencial Parque Verde, série 2026-04-01 a 2026-10-04:

- **952 sessões**, **28.501,4 kWh** no semestre (semente 42), cada linha com veículo.
- Frota: 15 períodos de posse, teto de 3 carros/apto; 11 ativos em 04/10; 60 dias-apto sem carro.
- Rateio do mês corrente (outubro/2026, energia + 5%): `evidencias/rateio_unidades.csv`.
- Regressão semanal: Ridge (α = 8), R² ajustado de teste **77%** (OLS 76%). Projeção nov/2026–abr/2027 na ordem de 5,3–6,0 mil kWh/mês.
- Síndico Virtual (OpenAI) recebe histórico, frota, KPIs e a projeção.

Arquivos em `evidencias/` e `dados/`.

---

## Decisões técnicas e desvios em relação à Sprint 01

A Sprint 02 implementa o que foi planejado: Python, in-memory, tarifa dinâmica, RFID, Modbus do HCA G2, IA híbrida e dashboard. Os desvios abaixo são conscientes e cabem no README exigido pelo edital.

| Planejado na Sprint 01 | Neste protótipo | Justificativa |
|---|---|---|
| OCPP 1.6J real (WebSocket) | Ciclo de sessão + mapa Modbus simulado | Sem hardware HCA G2 no ambiente do aluno; o mapa de registradores (10000–30015) está modelado no simulador |
| PostgreSQL em produção | Estruturas em memória | Decisão Q5 da Sprint 01: in-memory no MVP |
| EWMA / Prophet | OLS + Ridge/Lasso/ElasticNet no **kWh semanal** por apto | O diário tem ~42% de zeros e R² ~0,28; a semana atinge R² ajustado > 0,70 no hold-out |
| Tarifa com fator de demanda e bandeira | Ponta / intermediária / fora ponta | Os fatores 1,5 e 1,2 já diferenciam o kWh |
| Roadmap: IA em mar/2027 e dashboard em jun/2027 | IA 4D + Flask + seção de regressão já nesta sprint | O edital da Sprint 02 exige protótipo com lógica, IA estrutural e evidência |
| Integração Superlógica / Condomob | Exportação CSV | Formato que a administradora já consome |
| Gemini obrigatório | OpenAI no Síndico Virtual; Gemini e regras locais como fallback | A chave fica em `prototipo/.env` (fora do Git) |

O que **não** desviou: linguagem Python, autenticação RFID, tarifa alinhada à RN ANEEL 1.000/2021, fórmula `Σ(kWh × tarifa) + 5%`, Síndico Virtual com dados reais do condomínio, e o HCA G2 como hardware de referência.

---

## Uso de IA no desenvolvimento

Ferramentas de IA apoiaram organização do repositório, geração das evidências, o motor de regressão e o roteiro do pitch. A lógica de negócio (sessão, Modbus, tarifa, rateio, as quatro dimensões do MotorIA) é a da Sprint 01, reaproveitada da Fase III e compreendida pela equipe. Trechos gerados foram lidos, adaptados e testados.

---

## Rubrica (autoavaliação)

| Critério | Onde está |
|---|---|
| Lógica central (sessões, consumo, rateio) | `ev_chargeops.py` (`GerenciadorSessoes`, `MotorFaturamento`) + tela de rateio |
| IA estrutural | `MotorIA` + `motor_regressao.py` + Síndico Virtual (OpenAI) + seção Regressão |
| Evidência | `evidencias/` e `dados/` (série, frota, JSON, CSV, PNG) |
| Autoria | Código da Sprint 01 evoluído; taxa de 5% alinhada ao documento; README com desvios |
| README e organização | Esta pasta, `prototipo/` separado de `dados/` e `evidencias/` |
