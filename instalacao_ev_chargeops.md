# EV ChargeOps — Guia de Instalação (Sprint 02)

**Enterprise Challenge 2026 — FIAP + GoodWe**  
**Aluno:** Marcelo Bastianello Baldin | RM568746 | Grupo 22

---

## Requisitos

- Python 3.10 ou superior (testado com Anaconda)
- Conexão com internet na primeira instalação (`pip`)
- Opcional: chave OpenAI para o Síndico Virtual

---

## Instalação automática

Na pasta `prototipo/`:

```bash
python instalar_ev_chargeops.py
```

O instalador cria o ambiente virtual, instala as dependências e sobe o Flask.

---

## Instalação manual

```bash
cd prototipo
python -m venv venv_ev_chargeops
source venv_ev_chargeops/bin/activate   # Windows: venv_ev_chargeops\Scripts\activate
pip install -r requirements.txt
python app_ev_chargeops.py
```

Abrir http://localhost:5050

---

## Credenciais

| Perfil | Usuário | Senha | O que vê |
|---|---|---|---|
| Morador | `morador` | `senha` | Ana Silva, 101-A |
| Síndico | `sindico` | `senha` | Dashboard, ranking, Análise IA, **Regressão**, Síndico Virtual |
| Administrador | `administrador` | `senha` | Faturas, rateio e CSV |

Na subida o servidor carrega as 952 sessões de 6 meses e treina a regressão (Ridge).

---

## Síndico Virtual (OpenAI)

Crie `prototipo/.env` (não versionado):

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Sem a chave, tenta Gemini (`GEMINI_API_KEY`) e, por último, o fallback local por regras.

---

## Regenerar dados e evidências

```bash
cd prototipo
python gerar_consumo_6meses.py      # série + frota (semente 42)
python gerar_evidencias.py          # JSON, CSV, gráfico de rateio
```

---

## Funcionalidades por perfil

### Morador
- Consumo, custo e sessões da unidade
- Histórico com tarifa e veículo (placa/modelo)
- Recomendações de horário

### Síndico
- Consolidado do condomínio (952 sessões / 28.501,4 kWh nesta série)
- Ranking, carregadores HCA G2, Análise IA
- **Regressão**: OLS vs Ridge/Lasso/ElasticNet, KPIs, projeção nov/2026–abr/2027
- Síndico Virtual com contexto RAG (histórico, frota, KPIs, projeção)

### Administrador
- Faturas do mês corrente
- Rateio `Σ(kWh × tarifa) + 5%`
- Exportação CSV

---

## Solução de problemas

| Problema | Solução |
|---|---|
| Porta 5050 ocupada | Encerre o processo anterior ou altere a porta no final de `app_ev_chargeops.py` |
| ModuleNotFoundError | `pip install -r requirements.txt` no venv |
| Síndico Virtual sem LLM | Configure `OPENAI_API_KEY` em `.env` |

**Repositório:** https://github.com/marcelobaldin/EV_Challenge_EV_ChargeOps  
**Contato:** marcelobbaldin@gmail.com
