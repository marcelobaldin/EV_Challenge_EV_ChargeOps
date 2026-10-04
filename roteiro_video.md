# Roteiro do vídeo pitch — EV ChargeOps (Sprint 02)

**Enterprise Challenge 2026 — GoodWe + FIAP**  
**Aluno:** Marcelo Bastianello Baldin — RM568746 — Grupo 22  
**Duração alvo:** 2min50 (limite: 3min00)  
**Formato:** pitch presencial obrigatório; a nota só entra no boletim depois desta apresentação.

Este roteiro é o texto para falar. Não decore palavra por palavra: mantenha os **números** e a ordem dos blocos.

---

## Antes de gravar / apresentar — checklist

- [ ] Subir o sistema: `cd prototipo && python app_ev_chargeops.py`
- [ ] Abrir http://localhost:5050 já na tela de login
- [ ] Login de síndico: `sindico` / `senha`
- [ ] Ter `evidencias/rateio_por_unidade.png` e o PDF v6 à mão, caso a rede falhe
- [ ] Fonte do navegador em 110–125%
- [ ] Fechar notificações
- [ ] Cronômetro visível só para você
- [ ] Este roteiro impresso ou em segunda tela — **não** na tela projetada

---

## Sequência da demonstração (o que clicar)

| Momento | Ação | O que precisa aparecer |
|---|---|---|
| Bloco 1 | Tela de login | Marca EV ChargeOps |
| Bloco 2 | Entrar como `sindico` / `senha` | Dashboard: **952 sessões**, **28.501,4 kWh** |
| Bloco 3 | **Ranking Consumo**. Se der tempo, `administrador` → **Rateio** | Elena 301-B no topo; Felipe 302-B no fim (vendeu o carro). Outubro no lote: R$ 634,12 |
| Bloco 4 | **Regressão** e, se der tempo, **Síndico Virtual** | Ridge α=8, R² adj teste ~77%; projeção; pergunta “Como está o rateio?” |
| Encerramento | Voltar ao dashboard | Uma frase de fechamento |

Se o Flask falhar, mostre `evidencias/` e o PDF `relatorio_ev_chargeops_v6.pdf`.

---

# ROTEIRO NARRADO (~430 palavras, ~2min50)

> Fale olhando para a banca. Quando citar número, aponte para a tela.

---

## BLOCO 1 — Problema (0:00 – 0:25)

**Tela:** login.

> "Olá, sou o Marcelo Baldin, RM 568746, Grupo 22. Este é o EV ChargeOps, Sprint 2 do Enterprise Challenge GoodWe e FIAP.
>
> O problema é concreto: no condomínio, o carregador é compartilhado, mas a conta não é. Sem sessão por unidade, sem tarifa horária e sem rateio, ou todo mundo paga igual, ou ninguém consegue auditar o kWh.
>
> A pergunta da Sprint 01 continua valendo: como transformar sessão de recarga em dado, em rateio justo e em inteligência acionável?"

---

## BLOCO 2 — O que roda (0:25 – 0:55)

**Tela:** síndico. Dashboard.

> "Não reinventamos a arquitetura. A Sprint 01 definiu três camadas: o HCA G2 da GoodWe, a conectividade Modbus, e a camada digital com sessões, faturamento e um Motor de IA em quatro dimensões.
>
> O protótipo é Python com Flask. Quatro carregadores, oito unidades, novecentas e cinquenta e duas sessões em seis meses — vinte e oito mil e quinhentos kWh. Cada sessão tem RFID, kWh, tarifa do horário e, agora, a placa do carro."

**Ação:** apontar os cards 952 / 28.501,4 kWh.

---

## BLOCO 3 — Rateio (0:55 – 1:35)

**Tela:** Ranking; se der tempo, Rateio do administrador.

> "A lógica central é a fórmula da Sprint 01: custo da unidade é a soma de cada kWh vezes a tarifa daquela sessão, mais 5% de taxa administrativa.
>
> Fora ponta é a base; intermediária, mais 20%; ponta, das dezoito às vinte e uma em dia útil, mais 50%.
>
> No ranking, a Elena, 301 B, lidera. O Felipe, 302 B, vendeu o Kwid em setembro e quase some da conta — quem não usa, não subsidia. No lote de evidências, outubro fecha em seiscentos e trinta e quatro reais. Na tela ao vivo, leia o número da tabela."

---

## BLOCO 4 — Motor de IA (1:35 – 2:30)

**Tela:** Regressão; se possível, uma pergunta no Síndico Virtual.

> "A IA não é um chatbot pendurado. Ela entra em quatro pontos.
>
> Interpretação: classifica a sessão. Precificação: é o Motor de IA que calcula a tarifa no encerramento — sem isso o rateio não existe.
>
> Preditividade: o kWh diário tem 42% de zeros, então o alvo é semanal. Comparamos OLS com Ridge, Lasso e ElasticNet. O Ridge, alfa 8, chega a 77% de R² ajustado no teste. A projeção de novembro a abril alimenta o alerta de um quinto carregador.
>
> Conversação: o Síndico Virtual vai para a OpenAI com ranking, frota, KPIs e essa projeção. Sem a chave, cai no Gemini ou no fallback local."

**Ação:** mostrar os cards Ridge / corte 2026-S32. Se der tempo, perguntar “Como está o rateio?”.

---

## BLOCO 5 — Fechamento (2:30 – 2:55)

**Tela:** dashboard.

> "Resumo para a rubrica: sessões estruturadas, rateio auditável, IA no caminho crítico, evidências em JSON, CSV, gráfico, PDF e nesta tela.
>
> Desvio consciente: o HCA G2 está simulado, sem OCPP real, porque não temos o hardware no ambiente. O mapa Modbus e a regra de negócio são os da Sprint 01.
>
> EV ChargeOps: do RFID até o item no boleto, com inteligência que o síndico consegue usar. Obrigado."

Parar. Não improvisar um sexto bloco.

---

## Se estourar 3 minutos — ordem de corte

1. Tirar a frase do fallback OpenAI/Gemini.
2. Encurtar o bloco 2 (não listar as três camadas).
3. Não abrir o chat: somente a tela de Regressão.
4. Nunca cortar a fórmula do rateio nem o 952 / 28.501 kWh.

## Se faltar tempo de fala (acabou em 2:20)

Acrescente: “Felipe, 302 B, vendeu o carro em setembro e fecha outubro em zero reais. Transparência para a assembleia.”

---

## Cobertura da rubrica

| Critério | Peso | Bloco |
|---|---|---|
| Lógica central | 0–3,0 | 2 e 3 |
| IA estrutural | 0–3,0 | 4 |
| Evidência | 0–2,0 | demonstração + pasta `evidencias/` + PDF v6 |
| Autoria | 0–1,0 | todo o pitch |
| README e repositório | 0–1,0 | citar o GitHub se a banca pedir |

---

## Depois do pitch — entrega FIAP ON

1. Conferir se o GitHub contém `README.md`, `prototipo/`, `dados/`, `evidencias/` e `relatorio_ev_chargeops_v6.pdf`.
2. Na atividade, enviar **somente** o arquivo `link_repositorio.txt` (o edital pede um `.TXT` com o link).
3. A nota digital só é lançada após este pitch presencial. Falta na apresentação zera o Challenge.
