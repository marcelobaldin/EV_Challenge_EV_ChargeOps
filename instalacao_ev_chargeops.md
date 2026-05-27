# EV ChargeOps - Guia de Instalacao

**Enterprise Challenge 2026 - FIAP + GoodWe**
**Aluno:** Marcelo Bastianello Baldin | RM568746

---

## Requisitos

- Python 3.9 ou superior
- Conexao com internet (apenas na primeira execucao, para instalar o Flask)

---

## Instalacao Automatica (Recomendado)

```bash
python instalar_ev_chargeops.py
```

O instalador cria automaticamente o ambiente virtual, instala as dependencias e inicia o sistema.

---

## Instalacao Manual

### 1. Criar ambiente virtual

```bash
python -m venv venv_ev_chargeops
```

### 2. Ativar o ambiente

**Windows:**
```bash
venv_ev_chargeops\Scripts\activate
```

**Mac / Linux:**
```bash
source venv_ev_chargeops/bin/activate
```

### 3. Instalar dependencias

```bash
pip install flask google-genai
```

### 4. Configurar Sindico Virtual com IA (opcional)

O Sindico Virtual funciona sem configuracao (respostas locais). Para habilitar IA generativa com Google Gemini (gratuito):

1. Acesse https://aistudio.google.com/apikey
2. Clique em "Create API Key"
3. Exporte a variavel antes de executar:

**Mac / Linux:**
```bash
export GEMINI_API_KEY="sua-chave-aqui"
```

**Windows:**
```bash
set GEMINI_API_KEY=sua-chave-aqui
```

### 5. Executar a aplicacao

```bash
python app_ev_chargeops.py
```

---

## Acesso

**URL:** http://localhost:5050

---

## Credenciais de Acesso

| Perfil | Usuario | Senha | Descricao |
|--------|---------|-------|-----------|
| **Morador** | `morador` | `senha` | Painel pessoal de consumo e sessoes |
| **Sindico** | `sindico` | `senha` | Gestao completa do condominio + Sindico Virtual |
| **Administrador** | `administrador` | `senha` | Faturamento, rateio e exportacao financeira |

---

## Funcionalidades por Perfil

### Morador
- Dashboard pessoal com consumo (kWh), custo (R$) e numero de sessoes
- Historico completo de sessoes de recarga (data, duracao, energia, tarifa, custo)
- Recomendacoes de IA: melhores horarios para carregar, economia estimada
- Eletropostos proximos: pontos publicos de recarga via Open Charge Map e Google Places

### Sindico
- Dashboard consolidado do condominio (todas as unidades)
- Ranking de consumo por unidade habitacional
- Status dos 4 carregadores GoodWe HCA G2 (modelo, potencia, localizacao, telemetria Modbus, modo de carregamento, DLM)
- Analise de IA: previsao de demanda, deteccao de anomalias, interpretacao de sessoes
- **Sindico Virtual**: agente conversacional para consultas em linguagem natural
- Configuracoes de tarifa (visualizacao)
- Modos de carregamento: visualizacao dos 5 modos do HCA G2 (Rapido, Solar, PV+Bat, Agendamento, DLM)
- Dados Modbus: registradores reais simulados com tensao por fase, corrente, potencia e status

### Administrador
- Geracao de faturas mensais individuais por unidade
- Relatorio de rateio condominial (distribuicao de custos)
- Exportacao CSV para sistemas contabeis
- Historico de faturamento

---

## Integracoes (Simuladas)

| Integracao | Descricao | Dados |
|------------|-----------|-------|
| **GoodWe Modbus TCP** | Registradores Modbus reais (10000-30015), modos de carga, DLM | Simulados localmente |
| **Open Charge Map** | Eletropostos publicos proximos | Dados simulados realistas |
| **Google Places** | Pontos de recarga por localizacao | Dados simulados realistas |

Todas as integracoes funcionam offline com dados simulados. Nao e necessario configurar chaves de API.

### Simulacao Modbus

O sistema simula os registradores Modbus reais do carregador GoodWe HCA G2 (ref: Mapa MODBUS_HCA G2.pdf V1.0.15):

| Registrador | Funcao | Tipo |
|-------------|--------|------|
| 10009-10014 | Tensao e corrente por fase (mono 220V / tri 380V) | Leitura |
| 10015-10016 | Potencia (kW) e energia da sessao (kWh) | Leitura |
| 10017 | Status da estacao (11 estados reais) | Leitura |
| 10025-10026 | Controle Dinamico de Carga (DLM) e corrente disjuntor | Escrita |
| 10032 | Modo de carregamento (rapido/solar/PV+bat) | Escrita |
| 10060 | Liga/desliga carregador | Escrita |
| 10065 | Energia historica acumulada (kWh) | Leitura |
| 10075 | Status conexao do veiculo (3 estados) | Leitura |
| 10108 | Fonte de energia (bitmap: rede/PV/bateria) | Leitura |

---

## Estrutura de Arquivos

```
EV challenge/
  app_ev_chargeops.py         # Aplicacao web Flask
  ev_chargeops.py             # Motor da plataforma (backend + Modbus)
  instalar_ev_chargeops.py    # Instalador automatico
  instalacao_ev_chargeops.md  # Este guia
  Assets/
    GW_HCA-G2_Datasheet-PT.pdf    # Datasheet do carregador (specs reais)
    GW_HCA-G2_User-Manual-PT.pdf  # Manual do usuario completo
    Mapa MODBUS_HCA G2.pdf        # Mapa de registradores Modbus (V1.0.15)
  templates/
    login.html                # Pagina de login
    dashboard.html            # Dashboard principal (SPA)
```

---

## Notas Tecnicas

- Todos os dados sao gerados em memoria (30 dias de historico simulado)
- Os dados sao regenerados a cada reinicio da aplicacao
- Nao requer banco de dados
- Motor de IA com 4 dimensoes: interpretacao, preditividade, precificacao, conversacao
- Simulacao baseada no Mapa de Registradores Modbus real do HCA G2 (~80 registradores)
- 5 modos de carregamento: Rapido, Prioridade Solar, PV+Bateria, Agendamento, DLM
- Controle Dinamico de Carga (DLM) para gestao da demanda condominial
- Status do carregador com 11 estados reais conforme registrador Modbus 10017
- Protecao IP66 (carregador) conforme datasheet GoodWe
- Porta padrao: 5050 (pode ser alterada no codigo)
- Para encerrar o servidor: pressione Ctrl+C no terminal

---

## Solucao de Problemas

| Problema | Solucao |
|----------|---------|
| Porta 5050 ocupada | Altere a porta no final de `app_ev_chargeops.py` |
| ModuleNotFoundError: flask | Execute `pip install flask` no ambiente virtual |
| ModuleNotFoundError: ev_chargeops | Certifique-se de executar na pasta `EV challenge/` |
| Pagina em branco | Limpe o cache do navegador (Ctrl+Shift+R) |
| Sindico Virtual sem IA | Exporte GEMINI_API_KEY para habilitar Google Gemini |

---

**Repositorio:** https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps
**Contato:** marcelobbaldin@gmail.com
