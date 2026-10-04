# EV ChargeOps — Sprint 02

**Enterprise Challenge 2026 — GoodWe + FIAP**  
**Grupo 22** · Marcelo Bastianello Baldin · RM568746  
**Fase 6 — Comunicação Interplanetária**  
**Prazo:** 13/10/2026

Protótipo funcional da plataforma de gestão compartilhada de recarga de veículos elétricos em condomínios. Implementa a arquitetura, o rateio e o Motor de IA definidos na Sprint 01.

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
| Preditividade | Média diária, tendência e previsão de 30 dias; alerta de expansão |
| Precificação | Calcula a tarifa de cada sessão no momento do encerramento |
| Conversação | Síndico Virtual via **OpenAI** (`OPENAI_API_KEY`); Gemini e regras locais só como fallback |

---

## Como executar

Requisitos: Python 3.10+ (testado com Anaconda). Dependências em `prototipo/requirements.txt`.

```bash
cd prototipo
pip install -r requirements.txt
python app_ev_chargeops.py
```

Abrir http://localhost:5050

| Usuário | Senha | Perfil |
|---|---|---|
| `morador` | `senha` | Ana Silva, unidade 101-A |
| `sindico` | `senha` | Painel operacional + Síndico Virtual |
| `administrador` | `senha` | Faturas, rateio e exportação CSV |

O servidor sobe com o condomínio demo (8 unidades, 4 carregadores) e carrega `dados/consumo_sessoes_6meses.csv` (abr–set/2026 + 1–4/out, semente 42). Cada sessão aponta para um veículo cadastrado naquele dia (marca, modelo, bateria, autonomia, placa). A frota muda com compra e venda; apto sem carro no dia não recarrega. Para regenerar a série:

```bash
cd prototipo
python gerar_consumo_6meses.py
```

Para regenerar as evidências em lote (JSON, CSV e gráfico), sem abrir o navegador:

```bash
cd prototipo
python gerar_evidencias.py
```

Saídas em `evidencias/`.

O Síndico Virtual usa a API da OpenAI (padrão: `gpt-4o-mini`). Crie `prototipo/.env` (não versionado) com:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Sem a chave, tenta Gemini (`GEMINI_API_KEY`) e, por último, o fallback local por regras — o módulo de IA continua estrutural.

---

## Organização do repositório

```
README.md                          ← este arquivo
link_repositorio.txt               ← entregável oficial FIAP ON
roteiro_video.md                   ← pitch presencial de 3 minutos
sprint01_pesquisa_documentacao.md  ← base da Sprint 01 (reaproveitada)
prototipo/
  ev_chargeops.py                  ← núcleo (sessões, Modbus, IA, rateio)
  app_ev_chargeops.py              ← Flask na porta 5050
  gerar_consumo_6meses.py          ← gera a série de 6 meses (semente 42)
  gerar_evidencias.py
  requirements.txt
  templates/login.html
  templates/dashboard.html
dados/
  consumo_diario_6meses.csv        ← 8 aptos × todos os dias (kWh pode ser 0)
  consumo_sessoes_6meses.csv       ← sessões + veículo (placa, marca, bateria)
  consumo_mensal_6meses.csv        ← agregado mensal por unidade
  frota_cadastro_6meses.csv        ← períodos de posse (0 a 3 carros/apto)
  frota_eventos_6meses.csv         ← cadastro inicial, compra e venda
  frota_diaria_6meses.csv          ← snapshot diário da frota
evidencias/
  saida_prototipo.json
  rateio_unidades.csv
  rateio_por_unidade.png
  tela_login.png
  tela_sindico_dashboard.png
  tela_sindico_ranking.png
  tela_sindico_ia.png
  tela_sindico_virtual.png
  tela_admin_rateio.png
  tela_admin_faturas.png
```

---

## Evidências de funcionamento (execução de 04/10/2026)

Condomínio Residencial Parque Verde, série 2026-04-01 a 2026-10-04:

- **952 sessões**, **28.501,4 kWh** no semestre (semente 42), com veículo (placa, marca, bateria, autonomia) em cada linha.
- Frota: 15 períodos de posse, teto de 3 carros/apto; 11 ativos em 04/10; 60 dias-apto sem carro (venda sem reposição imediata).
- Rateio do mês corrente (outubro/2026, energia + 5%): ver `evidencias/rateio_unidades.csv`.
- Previsão IA (média móvel): tendência crescente, ~4.572 kWh no horizonte de 30 dias.
- Síndico Virtual (OpenAI) recebe tabelas mensais, 14 dias, frota ativa, compra/venda e kWh por placa.

Arquivos em `evidencias/` e `dados/`.

---

## Decisões técnicas e desvios em relação à Sprint 01

A Sprint 02 implementa o que foi planejado: Python, in-memory, tarifa dinâmica, RFID, Modbus do HCA G2, IA híbrida e dashboard. Os desvios abaixo são conscientes e cabem no README exigido pelo edital.

| Planejado na Sprint 01 | Neste protótipo | Justificativa |
|---|---|---|
| OCPP 1.6J real (WebSocket) | Ciclo de sessão + mapa Modbus simulado | Sem hardware HCA G2 no ambiente do aluno; o mapa de registradores (10000–30015) está modelado no simulador |
| PostgreSQL em produção | Estruturas em memória | Decisão Q5 da Sprint 01: in-memory no MVP |
| EWMA / Prophet / scikit-learn | Média móvel + tendência por metades da série | Suficiente para o papel estrutural de predição no Sprint 02; Prophet fica no roadmap |
| Tarifa com fator de demanda e bandeira | Ponta / intermediária / fora ponta | Os fatores 1,5 e 1,2 já diferenciam o kWh; bandeira e ocupação simultânea entram na evolução |
| Roadmap: IA em mar/2027 e dashboard em jun/2027 | IA 4D + Flask já nesta sprint | O edital da Sprint 02 exige protótipo com lógica, IA estrutural e evidência; o dashboard foi antecipado |
| Integração Superlógica / Condomob | Exportação CSV | Formato que a administradora já consome; API fica para v1.0 |
| Gemini obrigatório | OpenAI no Síndico Virtual; Gemini e regras locais como fallback | A chave fica em `prototipo/.env` (fora do Git); o restante da IA 4D continua local |

O que **não** desviou: linguagem Python, autenticação RFID, tarifa alinhada à RN ANEEL 1.000/2021, fórmula `Σ(kWh × tarifa) + 5%`, Síndico Virtual com dados reais do condomínio, e o HCA G2 como hardware de referência.

---

## Uso de IA no desenvolvimento

Ferramentas de IA apoiaram organização do repositório, geração das evidências e o roteiro do pitch. A lógica de negócio (sessão, Modbus, tarifa, rateio, as quatro dimensões do MotorIA) é a da Sprint 01, reaproveitada da Fase III e compreendida pela equipe. Trechos gerados foram lidos, adaptados e testados.

---

## Rubrica (autoavaliação)

| Critério | Onde está |
|---|---|
| Lógica central (sessões, consumo, rateio) | `ev_chargeops.py` (`GerenciadorSessoes`, `MotorFaturamento`) + tela de rateio |
| IA estrutural | `MotorIA` (interpretação, previsão, tarifa no encerramento da sessão, Síndico Virtual) |
| Evidência | `evidencias/` (JSON, CSV, PNG, capturas da interface) |
| Autoria | Código da Sprint 01 evoluído; taxa de 5% alinhada ao documento; README com desvios |
| README e organização | Esta pasta, `prototipo/` separado de `evidencias/` |
