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

### 3. Instalar Flask

```bash
pip install flask
```

### 4. Executar a aplicacao

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
- Status dos 4 carregadores GoodWe HCA G2 (modelo, potencia, localizacao, telemetria)
- Analise de IA: previsao de demanda, deteccao de anomalias, interpretacao de sessoes
- **Sindico Virtual**: agente conversacional para consultas em linguagem natural
- Configuracoes de tarifa (visualizacao)

### Administrador
- Geracao de faturas mensais individuais por unidade
- Relatorio de rateio condominial (distribuicao de custos)
- Exportacao CSV para sistemas contabeis
- Historico de faturamento

---

## Integracoes (Simuladas)

| Integracao | Descricao | Dados |
|------------|-----------|-------|
| **GoodWe API** | Status dos carregadores, operacoes OCPP | Simulados localmente |
| **Open Charge Map** | Eletropostos publicos proximos | Dados simulados realistas |
| **Google Places** | Pontos de recarga por localizacao | Dados simulados realistas |

Todas as integracoes funcionam offline com dados simulados. Nao e necessario configurar chaves de API.

---

## Estrutura de Arquivos

```
EV challenge/
  app_ev_chargeops.py         # Aplicacao web Flask
  ev_chargeops.py             # Motor da plataforma (backend)
  instalar_ev_chargeops.py    # Instalador automatico
  instalacao_ev_chargeops.md  # Este guia
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

---

**Repositorio:** https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps
**Contato:** marcelobbaldin@gmail.com
