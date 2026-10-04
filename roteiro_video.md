# Roteiro do vídeo pitch — EV ChargeOps (Sprint 02)

**Enterprise Challenge 2026 — GoodWe + FIAP**  
**Aluno:** Marcelo Bastianello Baldin — RM568746 — Grupo 22  
**Duração alvo:** 2min50 (limite: 3min00)  
**Formato:** pitch presencial obrigatório; a nota só entra no boletim depois desta apresentação.

Este roteiro é o texto para falar. Não decore palavra por palavra: mantenha os **números** e a ordem dos blocos.

---

## Antes de gravar / apresentar — checklist

- [ ] Subir o sistema uma vez antes: `cd prototipo && python app_ev_chargeops.py`
- [ ] Abrir http://localhost:5050 já na tela de login (não gastar tempo do vídeo com o terminal)
- [ ] Login de síndico preparado: usuário `sindico` / senha `senha`
- [ ] Ter `evidencias/rateio_por_unidade.png` e o JSON à mão, caso a rede do dashboard falhe
- [ ] Fonte do navegador em 110–125%; tema escuro já é o padrão do app
- [ ] Fechar notificações
- [ ] Cronômetro visível só para você (celular virado para baixo, display 3:00)
- [ ] Este roteiro impresso ou em segunda tela — **não** na tela projetada

---

## Sequência da demonstração (o que clicar)

| Momento | Ação | O que precisa aparecer |
|---|---|---|
| Bloco 1 | Tela de login | Marca EV ChargeOps, campos usuário/senha |
| Bloco 2 | Entrar como `sindico` / `senha` | Dashboard: 4 carregadores, 8 unidades, sessões do mês |
| Bloco 3 | Síndico: **Ranking Consumo**. Se der tempo, `administrador` / `senha` → **Rateio** | Ranking dos 30 dias. Rateio do mês na tela do administrador. No JSON (semente 42) outubro fecha em R$ 671,63 — no ao vivo o valor muda; fale a fórmula e o número **da tela** |
| Bloco 4 | Menu **Análise IA** e, se der tempo, **Síndico Virtual** | Previsão crescente, alerta de expansão; pergunta “Como está o rateio?” |
| Encerramento | Voltar ao dashboard | Logo + uma frase de fechamento |

Se o Flask falhar no dia, mostre `evidencias/rateio_por_unidade.png` e `saida_prototipo.json`. A rubrica aceita captura, vídeo ou saída executada.

Login rápido do administrador (`administrador` / `senha`) só se sobrar tempo: CSV e faturas.

---

# ROTEIRO NARRADO (~430 palavras, ~2min50 em ritmo natural)

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

## BLOCO 2 — O que foi reaproveitado e o que roda (0:25 – 0:55)

**Tela:** entrar como síndico. Dashboard.

> "Não reinventamos a arquitetura. A Sprint 01 já definiu três camadas: o HCA G2 da GoodWe, a conectividade Modbus, e a camada digital com sessões, faturamento e um Motor de IA em quatro dimensões.
>
> O protótipo é Python com Flask. Quatro carregadores simulados, oito unidades, cerca de cento e oitenta sessões nos últimos trinta dias. RFID identifica a unidade, a sessão registra início, fim, kWh e a tarifa daquele horário."

**Ação:** apontar os cards de sessões / consumo / carregadores.

---

## BLOCO 3 — Rateio (0:55 – 1:40)

**Tela:** Ranking do síndico; se der tempo, Rateio do administrador.

> "A lógica central é esta fórmula, da Sprint 01: o custo da unidade é a soma de cada kWh vezes a tarifa daquela sessão, mais 5% de taxa administrativa.
>
> A tarifa não é chão único. Fora ponta é a base; intermediária, mais 20%; ponta, das dezoito às vinte e uma em dia útil, mais 50%. Fim de semana fica na base o dia todo — alinhado à ANEEL.
>
> No ranking dos últimos trinta dias a unidade 301 B, da Elena, lidera. No lote reproduzível de evidências, outubro fecha em seiscentos e setenta e um reais. Na tela ao vivo, leia o total da tabela. Quem recarrega mais, paga mais. Quem não usa, não subsidia."

**Ação:** mostrar a barra ou a tabela. Se estiver no live Flask, use os números da tela, não os do JSON.

---

## BLOCO 4 — Motor de IA (1:40 – 2:30)

**Tela:** Análise IA; se possível, uma pergunta no Síndico Virtual.

> "A IA não é um chatbot pendurado. Ela entra em quatro pontos do fluxo.
>
> Interpretação: classifica a sessão — normal, prolongada, baixa eficiência — e alerta cabo com 66% de eficiência ou recarga acima de 60 kWh.
>
> Precificação: é o Motor de IA que calcula a tarifa no encerramento da sessão. Sem isso, o rateio não existe.
>
> Preditividade: média de duzentos kWh por dia, tendência crescente de 39%, previsão de cerca de seis mil kWh no mês. O sistema recomenda carregador extra.
>
> Conversação: o Síndico Virtual agora vai para a OpenAI com o ranking, o rateio e as anomalias. Sem a chave, cai no Gemini ou no fallback local."

**Ação:** perguntar “Como está o rateio e as faturas?” e ler a resposta em voz alta.

---

## BLOCO 5 — Fechamento (2:30 – 2:55)

**Tela:** dashboard.

> "Resumo para a rubrica: sessões estruturadas, rateio auditável, IA no caminho crítico, evidências em JSON, CSV, gráfico e nesta tela.
>
> Desvio consciente: o HCA G2 está simulado, sem OCPP real, porque não temos o hardware no ambiente. O mapa Modbus e a regra de negócio são os da Sprint 01.
>
> EV ChargeOps: do RFID até o item no boleto, com inteligência que o síndico consegue usar. Obrigado."

Parar. Não improvisar um sexto bloco.

---

## Se estourar 3 minutos — ordem de corte

1. Tirar a frase do fallback OpenAI/Gemini.
2. Encurtar o bloco 2 (não listar as três camadas; dizer só “arquitetura da Sprint 01 em Python”).
3. Não abrir o chat: somente a tela de Análise IA.
4. Nunca cortar a fórmula do rateio nem o número do condomínio.

## Se faltar tempo de fala (acabou em 2:20)

Acrescente um exemplo de morador: “Ana, 101 A, três sessões, cento e vinte kWh, cento e sete reais com a taxa. Transparência para a assembleia.”

---

## Cobertura da rubrica

| Critério | Peso | Bloco |
|---|---|---|
| Lógica central (sessões, consumo, rateio) | 0–3,0 | 2 e 3 |
| IA estrutural | 0–3,0 | 4 |
| Evidência de funcionamento | 0–2,0 | demonstração ao vivo + pasta `evidencias/` |
| Autoria e compreensão | 0–1,0 | todo o pitch (você explica tarifa e 5%) |
| README e repositório | 0–1,0 | citar o GitHub no encerramento se a banca pedir |

---

## Depois do pitch — entrega FIAP ON

1. Conferir se o GitHub contém `README.md`, `prototipo/` e `evidencias/`.
2. Na atividade, enviar **somente** o arquivo `link_repositorio.txt` (o edital pede um `.TXT` com o link).
3. A nota digital só é lançada após este pitch presencial. Falta na apresentação zera o Challenge, mesmo com o repositório no ar.
