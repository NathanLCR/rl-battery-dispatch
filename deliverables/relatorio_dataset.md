# Relatório — Construção e preparação do dataset (CA1 — Aprendizado por Reforço)

## 1. Objetivo

Construir, a partir de fontes brutas, um dataset limpo e alinhado no tempo para
modelar uma microrrede residencial (solar + bateria + rede elétrica) como um
ambiente de Aprendizado por Reforço. O produto final é uma série de 30 em 30
minutos, por cliente, contendo geração solar, consumo, preço da energia e
demanda do sistema — pronta para ser dividida em episódios diários de 48 passos.

O trabalho cobriu três etapas:

1. **Construção** do dataset unificado (`data/merged_30min_v2.csv`);
2. **Contrato de dados e limpeza** (garantir episódios de 48 passos);
3. **Split** dos dias em treino/validação/teste, estratificado por mês.

---

## 2. Fontes de dados

| Fonte | Conteúdo | Formato |
|-------|----------|---------|
| **Ausgrid Solar Home** (2012–2013) | Consumo e geração solar de casas com painéis, por meia hora | "Largo": 1 linha por (cliente, categoria, dia) + 48 colunas de horário |
| **AEMO** (`PRICE_AND_DEMAND_*_NSW1`) | Preço spot e demanda do sistema em NSW | "Longo": 1 linha por intervalo de 30 min, 1 arquivo por mês |

Do Ausgrid usamos as categorias:
- **GC** (General Consumption) → `load_kwh` (consumo da casa);
- **GG** (Gross Generation) → `pv_kwh` (geração solar);
- **CL** (Controlled Load) → **descartada** (ver justificativa na Seção 6).

Selecionamos **5 clientes** (IDs 1 a 5) dos 300 disponíveis, filtrando logo na
leitura para reduzir o volume de processamento.

---

## 3. Construção do dataset (`merged_30min_v2.csv`)

### 3.1 Ausgrid: de "largo" para "longo"

O arquivo bruto tem uma linha por (cliente, categoria, dia) com 48 colunas de
horário (`0:30`, `1:00`, …, `0:00`). Aplicamos:

1. **`melt`** — as 48 colunas de horário viraram linhas (`wide → long`),
   resultando em 251.136 linhas para os 5 clientes;
2. **`pivot_table`** — a coluna de categoria foi espalhada em colunas separadas,
   produzindo uma linha por (cliente, dia, horário) com `load_kwh` e `pv_kwh`.
   A verificação de `NaN` deu zero: todo par cliente-dia possui GC e GG.

### 3.2 Timestamp e a regra do `0:00`

Os rótulos de horário são **fim de intervalo** (a coluna `0:30` do dia 01/07 é a
energia acumulada entre 00:00 e 00:30). A última coluna, `0:00`, corresponde ao
intervalo que **termina à meia-noite** — ou seja, pertence à **meia-noite do dia
seguinte**. Se fosse tratada como `00:00` do mesmo dia, ficaria antes do `00:30`
e quebraria a ordem cronológica.

Convenção adotada: ao montar o timestamp, somamos **+1 dia** apenas às linhas com
horário `0:00`. Verificação (cliente 1, dia 01/07/2012): a primeira leitura do
dia é `00:30` de 01/07 e a última (`0:00`) é `00:00` de 02/07 — série contínua e
sem timestamps duplicados.

### 3.3 AEMO: preço e demanda

Os 12 arquivos mensais foram concatenados (17.520 linhas = 48 × 365). O preço
(`RRP`) vem em **$/MWh** e foi convertido para **$/kWh** dividindo por 1000
(1 MWh = 1000 kWh). A demanda (`TOTALDEMAND`) foi mantida em MW.

Estatísticas do preço confirmam forte assimetria à direita:
média ≈ 0,055; mediana ≈ 0,053; máximo = 0,318; **mínimo negativo** (−0,059),
o que ocorre em momentos de excesso de geração no mercado.

### 3.4 Horário de verão (DST) — decisão central de alinhamento

As notas oficiais do Ausgrid afirmam:

> *"The time format for the 48 columns of interval data is Eastern Standard Time
> (EST) and Eastern Daylight Savings Time (EDT) during the summer period."*

Ou seja, o Ausgrid segue o **relógio local com horário de verão** (UTC+10 no
inverno, UTC+11 no verão). A **AEMO**, por outro lado, opera em **AEST fixo
(UTC+10) o ano todo**, sem horário de verão.

Uma primeira versão que localizava o Ausgrid com offset fixo (`Etc/GMT-10`)
produziu um **desalinhamento de exatamente 1 hora entre solar/carga e preço
durante todo o verão** (100% dos registros de novembro a março divergiam; 0% no
inverno). Como o estado do agente de RL associa geração e preço no mesmo
instante, esse desalinhamento seria um erro real de modelagem.

**Solução adotada** — alinhar as duas fontes pelo mesmo instante físico:
- **Ausgrid** localizado como `Australia/Sydney` (com DST). As horas das viradas
  de horário de verão (ambíguas no outono, inexistentes na primavera) foram
  marcadas como `NaT` e removidas.
- **AEMO** localizada como `Etc/GMT-10` (AEST fixo).
- Ambas convertidas para **UTC** antes do merge, e o timestamp final devolvido
  para o horário local (`Australia/Sydney`).

Cada fonte é localizada no fuso em que foi **realmente gravada** — localizar a
AEMO como `Australia/Sydney` introduziria, no lado do preço, o mesmo erro que se
tentava corrigir.

### 3.5 Merge e coluna derivada

O merge foi feito por timestamp (em UTC) com `how='inner'`, garantindo que toda
linha final tenha preço válido (um estado de RL sem preço é inútil). Em seguida
calculamos:

```
net_load_kwh = load_kwh − pv_kwh
```

O sinal é informativo: positivo indica importação da rede (consumo > solar);
negativo indica excedente solar exportável.

### 3.6 Validação da construção

O dataset resultante foi comparado, linha a linha, com uma versão de referência
existente (após alinhar os timestamps pelo instante em UTC):

- **Formato idêntico:** 83.692 linhas, 5 clientes;
- `pv_kwh`, `price` e `total_demand_mw` com **diferença máxima 0,00** (match exato);
- `load_kwh` idêntico, exceto **5 linhas** no dia da virada de horário de verão
  (que são descartadas na limpeza da etapa seguinte);
- Offsets corretos: `+10:00` no inverno, `+11:00` no verão.

**Produto:** `data/merged_30min_v2.csv` — colunas `customer_id, timestamp,
pv_kwh, load_kwh, price_per_kwh, total_demand_mw, net_load_kwh`.

---

## 4. Contrato de dados e limpeza

Regra do ambiente: **1 episódio = 1 dia = 48 passos**. Logo, todo dia usado
precisa ter exatamente 48 leituras. Duas regras de limpeza, independentes:

### 4.1 Remoção de dias com ≠ 48 passos

Agrupando por (cliente, dia), os únicos dias com contagem diferente de 48 foram
**07/10/2012** e **07/04/2013** — exatamente as viradas de horário de verão
(cada uma com 46 passos, por causa da hora removida). Nenhum outro dia de
fronteira ou buraco apareceu, o que confirma a integridade da série. Esses dias
foram descartados.

O "dia do episódio" foi derivado do timestamp com o cuidado da regra do `0:00`:
como o timestamp é fim de intervalo, o dia de referência é o de
`timestamp − 1 minuto` (assim o ponto `00:00` volta ao dia de trading correto).

### 4.2 Descarte do cliente 2

O cliente 2 **não** foi descartado por dias mal-formados — seus dias são normais
(282 de 284 com 48 passos). O motivo é **cobertura temporal incompleta**: ele tem
apenas 284 dias contra 365 dos demais, com **novembro e dezembro de 2012
totalmente ausentes** e outubro pela metade. Isso inviabilizaria o split
estratificado por mês e enviesaria a visão sazonal do agente.

Estratégia: **treino no cliente 1**, com os clientes **3, 4 e 5** reservados como
teste de generalização.

Após a limpeza: **4 clientes × 363 dias × 48 passos = 69.696 linhas**.

---

## 5. Split treino / validação / teste (estratificado por mês)

Os dias foram divididos em **~70% treino / 15% validação / 15% teste**,
com dois princípios:

- **Unidade = dia inteiro**, nunca linhas soltas. Como cada episódio é um dia
  completo, dividir linhas causaria vazamento e episódios truncados.
- **Estratificação por mês**, não split cronológico. Solar, carga e preço têm
  forte sazonalidade; um corte cronológico treinaria numa estação e avaliaria em
  outra. Estratificar por mês garante que todas as estações apareçam nos três
  conjuntos.

O procedimento embaralha os dias **dentro de cada mês** com semente fixa
(`seed = 50`) e aplica as proporções, garantindo reprodutibilidade.

**Resultado:** 363 dias → **256 treino / 54 validação / 53 teste**, sem
sobreposição, com todos os 12 meses representados nos três conjuntos, e
determinístico entre execuções.

O split foi **congelado** em `data/day_split.json` para que todas as etapas
seguintes (discretizador, ambiente, avaliação) usem exatamente a mesma partição.

---

## 6. Resumo das decisões de projeto e justificativas

| Decisão | Justificativa |
|---------|---------------|
| Ignorar a categoria `CL` (Controlled Load) | Carga controlada pela concessionária, fora do controle do agente; incluí-la só adicionaria ruído que a política não pode influenciar. |
| Coluna `0:00` → meia-noite do dia seguinte | É fim de intervalo; mantém a série contínua e sem timestamps duplicados. |
| `RRP ÷ 1000` | Conversão de $/MWh (AEMO) para $/kWh (unidade do modelo). |
| `dayfirst=True` só no Ausgrid | Ausgrid usa data dia/mês/ano; AEMO usa ISO ano/mês/dia (sem ambiguidade). Evita troca de dia por mês. |
| Merge `inner` | Descarta instantes sem preço; todo estado precisa de preço válido. |
| Ausgrid = `Australia/Sydney`, AEMO = `Etc/GMT-10` | Cada fonte no fuso em que foi gravada; corrige o desalinhamento de 1 h no verão. |
| Remover dias ≠ 48 passos | O episódio e o bin de tempo pressupõem 48 passos uniformes; consertar 2 dias/ano com dados inventados seria menos honesto que descartá-los. |
| Descartar cliente 2 | Cobertura incompleta (faltam nov/dez 2012); quebraria a estratificação mensal. |
| Split por dia, estratificado por mês, com semente fixa | Evita vazamento entre episódios, cobre todas as estações, e é reprodutível. |

---

## 7. Arquivos gerados

| Arquivo | Descrição |
|---------|-----------|
| `build_dataset2.ipynb` | Pipeline de construção do dataset unificado. |
| `data/merged_30min_v2.csv` | Dataset final (83.692 linhas, 5 clientes). |
| `data_split.ipynb` | Limpeza (Passo 0) e split estratificado por mês (Passo 1a). |
| `data/day_split.json` | Partição congelada treino/val/teste (seed 50). |
