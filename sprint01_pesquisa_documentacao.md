# EV ChargeOps - Sprint 01: Pesquisa e Documentacao

**Enterprise Challenge 2026 - FIAP + GoodWe**
**Aluno:** Marcelo Bastianello Baldin | RM568746
**Curso:** Ciencias da Computacao (Online) - FIAP
**Prazo Sprint 01:** 21/06/2026

---

## Pergunta Central

> Como transformar sessoes de recarga de veiculos eletricos em uma infraestrutura compartilhada em dados estruturados, rateio justo e inteligencia acionavel?

---

## 1. Investigacao do Problema

### 1.1 Contexto
- Mercado global: 14M EVs vendidos em 2023 (IEA), projecao 40M/ano ate 2030
- Brasil: 93 mil EVs/hibridos vendidos em 2023 (+91%), projecao 4M ate 2030 (EPE)
- Cada sessao de recarga produz dados uteis: duracao, kWh, horario, frequencia, picos
- **Parceria GoodWe + FIAP**: GoodWe (>100 GW instalados, presente em +100 paises) disponibiliza o Energy Innovation Lab na Unidade 2 Aclimacao da FIAP, com carregador EV Charger FIAP (HCA G2) instalado no estacionamento L1 para desenvolvimento e teste

### 1.2 Problema Central
Infraestruturas de recarga compartilhadas em condominios nao dispoem de mecanismos integrados para:
- Estruturar sessoes por usuario/unidade
- Calcular consumo individual com rateio justo
- Oferecer experiencia digital clara
- Prever picos e otimizar uso da rede
- Gerar inteligencia acionavel dos dados

### 1.3 Pesquisa de Mercado

#### Brasil
| Empresa | Foco | Protocolo | IA | Destaque |
|---------|------|-----------|-----|----------|
| Voltbras | B2B/Hubs | OCPP 1.6 | Nao | Maior plataforma BR, +10 fabricantes |
| WEG WEMOB | Hardware | OCPP 1.6 | Nao | Fabricacao nacional, inversores solares |
| Zletric | Condominios | OCPP 1.6 | Nao | Rateio condominial, sem IA |
| EDP/Tupinamba | Residencial/Publico | Variado | Nao | +500 eletropostos, app |

#### Internacional
| Empresa | Pais | Foco | IA | V2G | Destaque |
|---------|------|------|-----|-----|----------|
| ChargePoint | EUA | Rede aberta | Sim | Nao | 200k+ pontos, plataforma cloud |
| Wallbox | Espanha | Residencial | Nao | Sim | Quasar 2 V2G bidirecional |
| EVBox/Virta | EU | Enterprise | Nao | Nao | White-label, roaming europeu |
| Tesla | EUA | Rede propria | Sim | Nao | 50k+ pontos, NACS padrao |

### 1.4 Diferenciais EV ChargeOps
- **Motor de IA 4D**: unica plataforma com 4 dimensoes integradas
- **Sindico Virtual**: agente RAG conversacional com dados reais
- **Precificacao dinamica**: multi-fator alinhado com ANEEL
- **Foco condominial**: rateio justo como proposito central

---

## 2. Contexto Tecnico e Regulatorio

### 2.1 Regulamentacao Brasileira
- **ANEEL RN 1.000/2021**: recarga como atividade nao regulada, precificacao livre
- **Lei 14.300/2022**: marco da geracao distribuida, prosumidores, solar + EVs
- **ABNT NBR IEC 61851**: requisitos de seguranca para recarga condutiva
- **INMETRO Portaria 111/2023**: certificacao compulsoria de carregadores
- **PNE 2050 (EPE)**: 4M EVs ate 2030, 33M ate 2050, +24 TWh/ano

### 2.2 Regulacao Internacional
- **EU AFIR (2023)**: postos a cada 60 km, 150-350 kW, pagamento por cartao
- **EUA NEVI**: US$ 7,5 bi, 500k chargers, OCPP + CCS obrigatorio
- **UK Smart Charge (2021)**: demand response, V2G, off-peak default

### 2.3 Protocolos
- **OCPP 1.6J**: protocolo aberto da Open Charge Alliance, exigido pela ANEEL
- **MODBUS TCP**: protocolo nativo do HCA G2 (9600 baud, 8N1), ~80 registradores (enderecos 10000-30015) para telemetria (V, A, W, kWh), controle (liga/desliga, modos, DLM), gerenciamento RFID e firmware OTA

### 2.4 Registradores Modbus HCA G2

O carregador HCA G2 expoe ~80 registradores via Modbus TCP. Faixas principais (ref: Mapa MODBUS_HCA G2.pdf V1.0.15):

| Faixa | Funcao | Exemplos |
|-------|--------|----------|
| 10000-10007 | Controle e falhas | EMS dispatch, fault bytes (bitmaps) |
| 10009-10016 | Medicao eletrica | Tensao A/B/C (V), corrente A/B/C (A), potencia (kW), capacidade (kWh) |
| 10017-10019 | Status operacional | Status estacao (11 estados), comunicacao (bitmap), plug-and-charge |
| 10020-10022 | Reserva/agendamento | Status reserva, hora inicio, duracao |
| 10023-10029 | Configuracao | Alternancia fase, DLM, disjuntor, potencia max/min |
| 10030-10038 | Modo avancado | SOC bateria, modo carregamento (rapido/PV/PV+bat), reserva |
| 10040-10108 | Identificacao e fonte | SN, firmware, tipo, energia acumulada, conexao veiculo, fonte energia |
| 10500-10521 | Gerenciamento RFID | Consultar/adicionar/remover cartoes (ate 10) |
| 20000-20098 | Firmware OTA | URL download, trigger, status, percentual |
| 30000-30015 | Alarmes IoT | Informacoes de alarme para plataforma IoT |

Tipos de dados: U16 (2 bytes), S16, U32 (4 bytes), S32, STR (string ASCII).
Acesso: RO (somente leitura), WO (somente escrita), RW (leitura e escrita).

### 2.5 V2G e ISO 15118
- Vehicle-to-Grid: bateria EV como armazenamento distribuido
- ANEEL CP 020/2024 em analise
- EV ChargeOps: V2G no roadmap via ISO 15118
- EV ChargeOps: modos PV e PV+Bateria ja implementados como preparacao

---

## 3. Arquitetura da Solucao

### 3.1 Tres Camadas

```
CAMADA DIGITAL
  Motor de Sessoes | Motor de IA (4D) | Faturamento | Integracoes | Dashboard
       ^                    ^                ^
       |                    |                |
  CAMADA DE CONECTIVIDADE
  OCPP 1.6J (WebSocket) | Modbus TCP (9600, 8N1) | Wi-Fi + LAN + RS-485 (x2)
       ^                    ^                ^
       |                    |                |
  CAMADA FISICA
  GoodWe HCA G2: 7kW | 11kW | 22kW | RFID ISO 14443A | IP66 | DPS III
```

### 3.2 Hardware GoodWe HCA G2

| Modelo | Potencia | Fase | Conector | IP |
|--------|----------|------|----------|-----|
| GW7K-HCA-20 | 7 kW | Monofasico | AC Tipo 2 | IP66 |
| GW11K-HCA-20 | 11 kW | Trifasico | AC Tipo 2 | IP66 |
| GW22K-HCA-20 | 22 kW | Trifasico | AC Tipo 2 | IP66 |

Caracteristicas: RFID ISO 14443A (10 cartoes), RS-485 (x2) + LAN + Wi-Fi + Bluetooth, Modbus TCP (9600 baud, 8N1), DPS Tipo III, protecao IP66/IP55 (plugue), protecoes RCD/OVP/UVP/OCP/OTP/DPS. Certificacao ANATEL (06795-24-02673).

### 3.3 Fluxo de Dados

```
[Morador]--RFID-->[Carregador HCA G2]--Modbus TCP / OCPP 1.6J-->[Servidor EV ChargeOps]
                                                         |
                    +------------------------------------+--------------------+
                    |                |                   |                    |
              [Gerenciador]    [Motor IA]          [Faturamento]       [Integracoes]
                    |          /  |  |  \               |                    |
              [Sessoes]   Int Pred Prec Conv       [Faturas]          [OCM/Places]
                                  |
                          [Sindico Virtual]
                           /            \
                [Dashboard Sindico]  [App Morador]
```

### 3.4 Modos de Carregamento HCA G2

O hardware suporta 5 modos de operacao (registrador Modbus 10032):

| Modo | Descricao | Fonte de Energia |
|------|-----------|------------------|
| Rapido (0) | Potencia nominal, carregamento padrao | Rede + PV + Bateria |
| Prioridade Solar (1) | Usa apenas excedente fotovoltaico | Somente PV |
| PV + Bateria (2) | Combina energia solar e armazenamento | PV + Bateria |
| Agendamento | Recarga programada por horario (reg 10020-10022) | Configuravel |
| Controle Dinamico de Carga (DLM) | Ajusta potencia conforme corrente do disjuntor (reg 10025-10026) | Rede (limitada) |

### 3.5 Status da Estacao de Carregamento

O registrador 10017 define 11 estados operacionais:

| Codigo | Status | Descricao |
|--------|--------|-----------|
| 00 | Idle (plugado) | Conector plugado, sem carga |
| 01 | Idle (desplugado) | Disponivel para uso |
| 02 | Handshake | Comunicando com veiculo |
| 03 | Carregando | Sessao de carga ativa |
| 04 | Completo | Carga finalizada |
| 05 | Alarme | Falha detectada |
| 06 | Agendado | Aguardando horario programado |
| 07 | Manutencao | Em modo de manutencao |
| 08 | Falha ao iniciar | Erro ao iniciar sessao |
| 09 | Upgrade | Atualizacao de firmware em andamento |
| 10 | Interrompido | Carga interrompida (PV/bateria insuficiente) |

---

## 4. Opcao A - Estruturacao de Sessoes de Recarga

### Modelo de Dados
- **Condominio**: id, nome, endereco, capacidade (kW), tarifa base
- **UnidadeHabitacional**: id, numero, bloco, proprietario, cartoes RFID
- **Carregador**: id, modelo HCA G2, potencia, status, protocolo OCPP
- **SessaoRecarga**: id, unidade_id, carregador_id, inicio/fim, kWh, custo, tarifa
- **Fatura**: id, unidade_id, periodo, total sessoes/kWh/valor, status

### Ciclo de Vida da Sessao
1. **AUTENTICACAO**: RFID -> Authorize (OCPP) -> validacao
2. **INICIO**: StartTransaction -> registro com timestamp + IDs
3. **MONITORAMENTO**: MeterValues periodicos (kWh acumulado)
4. **FINALIZACAO**: StopTransaction -> energia total + custo
5. **CONTABILIZACAO**: vinculacao a fatura mensal

### Rastreabilidade
Todos os eventos registrados com timestamp UTC: RFID apresentado, sessao iniciada/finalizada, MeterValues, mudancas de status, alertas de anomalia.

---

## 5. Opcao B - Processamento de Consumo e IA Avancada

### Motor de IA - 4 Dimensoes

> "A IA estrutura a proposta. Nao e uma feature extra; e a camada que da sentido aos dados brutos gerados pela rede."

#### 5.1 Interpretacao
- **Classificacao de sessoes**: NORMAL, RAPIDA, LONGA, PONTA, FORA_PONTA
- **Perfis de consumo**: COMMUTER, FLEX, HEAVY_USER, LIGHT_USER
- **Parsing MODBUS**: leitura dos registradores reais (10009-10016) para tensao por fase (V), corrente por fase (A), potencia (kW), energia acumulada (kWh). Suporte a carregadores monofasicos (220V) e trifasicos (380V, 3 fases)
- **Deteccao de anomalias**: consumo 3+ sigma, sessao fantasma, RFID nao autorizado

#### 5.2 Preditividade
- **Previsao de demanda**: EWMA com janela de 30 dias, mapa de calor 24h x 7d
- **Capacity planning**: alerta quando ocupacao media >70% por 3 meses
- **Manutencao preditiva**: ciclos de carga, temperatura, MTBF, degradacao
- Evolucao planejada: Prophet/ARIMA com decomposicao tendencia + sazonalidade

#### 5.3 Precificacao
- **Formula**: Tarifa = Base x FatorHorario x FatorDemanda x FatorBandeira
  - Base: tarifa ANEEL (R$ 0,65/kWh)
  - FatorHorario: 1.5x pico (18-21h), 0.7x madrugada (23-05h)
  - FatorDemanda: 1.0-1.3x conforme ocupacao simultanea
  - FatorBandeira: verde=1.0, amarela=1.05, vermelha=1.15
- **Incentivos**: ate 30% desconto noturno, teto de preco configuravel
- **Conformidade**: RN ANEEL 1.000/2021, transparencia na composicao

#### 5.4 Conversacao - Sindico Virtual
- **Pipeline RAG**: Dados -> Embedding -> Retrieval -> Augmentation -> Generation (LLM)
- **Exemplo**: "Quanto a unidade 302 gastou?" -> "87,3 kWh em 12 sessoes (R$ 74,21). Consumo 15% acima da media. Sugestao: recarga noturna para economia de R$ 18,50/mes."
- **Alertas proativos**: consumo 3x acima da media, carregador >80% utilizacao, previsao de sobrecarga

### Load Balancing Inteligente
Redistribuicao de potencia priorizando: (1) SoC mais baixo, (2) horario de saida agendado, (3) tarifa vigente. Respeitando limite de demanda contratada.

---

## 6. Opcao C - Gerenciamento Inteligente e UX

### Interface Morador
- Dashboard pessoal: consumo (kWh, R$), sessoes, grafico diario
- Historico: data, hora, duracao, energia, custo, tarifa, carregador
- Recomendacoes IA: horarios otimos, economia estimada
- Notificacoes: sessao iniciada/finalizada, fatura, alertas

### Painel Sindico
- Visao consolidada: sessoes, consumo, receita, ocupacao
- Ranking de consumo por unidade
- Sindico Virtual conversacional
- Relatorios: PDF assembleia, CSV contabilidade, demonstrativo/unidade

### Jornadas do Usuario
1. **Morador carrega**: RFID -> carga -> notificacao ("32,4 kWh, R$ 21,06. Economia R$ 8,10.")
2. **Sindico consulta**: dashboard -> Sindico Virtual -> relatorio -> ajuste tarifario
3. **Administradora fecha mes**: faturas automaticas -> CSV -> boleto condominio

### Principios UX
- Simplicidade (tap-to-charge), transparencia (tarifa visivel), proatividade (IA sugere), acessibilidade (web responsivo), confianca (dados auditaveis)

---

## 7. Rateio e Faturamento

### Modelo
```
Custo_Unidade = SUM(kWh_sessao_i x Tarifa_sessao_i) + Taxa_Admin (5%)
```

### Processo
1. Motor de Faturamento gera faturas individuais ao final do periodo (mensal)
2. Fatura consolidada do condominio com total agregado
3. Exportacao CSV/API para administradoras (Superlogica, Condomob)
4. Item no boleto: "Recarga EV - Mes XX/XXXX"
5. Inadimplencia: desabilitacao RFID pelo sindico

---

## 8. Decisoes Tecnicas

| # | Questao | Decisao | Justificativa |
|---|---------|---------|---------------|
| Q1 | Linguagem | Python | Ecossistema IA + prototipagem rapida |
| Q2 | Protocolo | OCPP 1.6J | Aberto + exigencia ANEEL |
| Q3 | Tarifa | Dinamica | Incentivo fora-ponta + regulacao |
| Q4 | Autenticacao | RFID | Simples + incluso GoodWe |
| Q5 | Armazenamento | In-memory | MVP; -> PostgreSQL prod |
| Q6 | Infra | On-premise | LGPD + offline; -> cloud prod |
| Q7 | IA | Hibrida | Local (scikit) + API LLM (Sindico) |
| Q8 | Telemetria | Modbus TCP | Protocolo nativo HCA G2, ~80 regs |
| Q9 | Protecao | IP66/DPS III | Specs reais do datasheet GoodWe |

---

## 9. Modelo de Negocio

### Formato
- SaaS B2B: assinatura mensal por condominio gerenciado

### Precificacao
- Faixa: R$ 200-500/mes por condominio (ate 10 carregadores)
- Adicional por carregador extra: R$ 30/mes
- Setup: R$ 500 por condominio (instalacao + configuracao)
- Sindico Virtual Premium: R$ 100/mes (API LLM incluida)

### Publico-alvo
- Condominios residenciais com carregadores compartilhados
- Edificios corporativos com vagas de recarga para funcionarios
- Campus universitarios (como a propria FIAP)
- Estacionamentos comerciais com servico de recarga

---

## 10. Roadmap

| Fase | Entrega | Prazo |
|------|---------|-------|
| Sprint 01 | Pesquisa e documentacao | Jun/2026 |
| Sprint 02 | Prototipo funcional Python | Set/2026 |
| v1.0 | MVP: RFID + rateio + faturas | Dez/2026 |
| v1.5 | Motor de IA (4 dimensoes) | Mar/2027 |
| v2.0 | App mobile + dashboard + Sindico Virtual | Jun/2027 |
| v2.5 | Cloud (AWS) + multi-condominio | Set/2027 |
| v3.0 | V2G + ISO 15118 + marketplace | Dez/2027 |

---

## 11. Entregaveis Sprint 01 (Alinhamento com o Challenge)

Conforme o playbook, a avaliacao foca em raciocinio arquitetonico, de negocios e de gestao de dados:

1. **Arquitetura Funcional**: logica clara de entradas e saidas (Data Flow) em 3 camadas
2. **Papel da IA Integrada**: motor logico de 4 dimensoes, nao penduricalho de interface
3. **Aderencia ao Contexto**: solucao sob medida para condominios com ecossistema GoodWe/FIAP
4. **Visao de Produto Real**: plataforma para condominios que resolve rateio justo e gera inteligencia operacional

---

## Referencias

1. ANEEL. Resolucao Normativa n. 1.000/2021.
2. Brasil. Lei n. 14.300/2022 (Geracao Distribuida).
3. ABNT. NBR IEC 61851-1:2023.
4. EPE. Plano Nacional de Energia 2050.
5. INMETRO. Portaria n. 111/2023.
6. IEA. Global EV Outlook 2024.
7. ABVE. Anuario da Mobilidade Eletrica 2024.
8. Open Charge Alliance. OCPP 1.6 Specification.
9. GoodWe. HCA G2 Series - Technical Datasheet.
10. FIAP + GoodWe. EV Challenge 2026 - Playbook.
11. EU. AFIR - Alternative Fuels Infrastructure Regulation, 2023.
12. USA. NEVI Formula Program, 2022.
13. UK. Smart Charge Points Regulations 2021.

---

**Repositorio:** https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps
**Contato:** marcelobbaldin@gmail.com
