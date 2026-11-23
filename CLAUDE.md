# Projeto Farol · contexto do projeto

Contexto para desenvolvimento assistido por IA (Claude Code): leia antes de escrever qualquer código.
Explica o negócio, o modelo de dados, as decisões de arquitetura e as armadilhas já resolvidas.

---

## 1. O negócio

A **Vértice Tecnologia** (empresa fictícia) desenvolve e implanta sistemas para clientes de varejo,
financeiro, saúde, logística e indústria: **60 projetos, 520 pessoas, R$ 305 mi de carteira**.
Cada gerente controla o projeto numa ferramenta diferente (**20 em Excel, 25 no ClickUp e 15 no
MS Project**) e ninguém sabe dizer quais projetos estão atrasados.

O Projeto Farol responde as **quatro perguntas do dono**:

1. **Quais projetos estão atrasados, e de quais clientes?** (SPI, CPI, situação)
2. **Quanto esse atraso vai custar?** (EAC, estouro previsto, margem)
3. **Tenho gente parada enquanto outro projeto pede gente?** (utilização do timesheet + causa no status)
4. **O que vai dar errado no próximo mês?** (entregas de consultoria atrasadas e o change freeze do varejo)

Regras de corte: SPI ou CPI **< 0,9 = atenção**, **< 0,8 = crítico**.

| KPI | Fórmula |
|---|---|
| SPI | EV ÷ PV. Nas tarefas: Σ horas × % concluído ÷ Σ horas × % do prazo baseline decorrido. < 1 é atraso |
| CPI | EV ÷ AC, com EV = orçamento × horas agregadas ÷ horas totais. < 1 é estouro |
| EAC | orçamento ÷ CPI |
| Estouro previsto | EAC − orçamento, só quando positivo |
| Margem projetada | (valor do contrato − EAC) ÷ valor do contrato |
| Atraso projetado (dias) | duração baseline ÷ SPI − duração baseline |
| Farol calculado | verde com SPI ≥ 0,95; amarelo ≥ 0,90; vermelho abaixo |
| Melancia | farol do gerente verde e SPI < 0,9 (verde por fora, vermelho por dentro) |

**O "hoje" do dataset é 16/10/2026 (sexta).** Nunca use `current_date()`: escreva
`DATE'2026-10-16'`, para os números serem reproduzíveis.

---

## 2. Onde está o dado

Unity Catalog, catálogo **`farol_projeto`**, schemas `bronze`, `silver`, `gold` e o volume `bronze.raw`.

As fontes exportam para um **data lake** (Supabase Storage, protocolo S3). A tarefa
`ingestao_data_lake` (notebook `src/ingestao/ingestao_boto3.py`) baixa os arquivos com `boto3`,
pousa no volume `bronze.raw` e recria as 9 tabelas bronze com `read_files`. A bronze guarda o dado
**como veio**: é a única entrada da silver e nunca é alterada à mão.

As chaves do data lake são variáveis do bundle (`${var.s3_access_key_id}`, `${var.s3_secret_access_key}`)
e o valor fica em `.databricks/bundle/dev/variable-overrides.json`, fora do Git.
**Chave nunca vai para arquivo versionado:** o repositório é público.

| Tabela bronze | Linhas | O que é |
|---|---|---|
| `projetos` | 60 | cadastro do PMO: cliente, segmento, valor, orçamento, datas, **ferramenta** e **código na ferramenta** (o de-para) |
| `status_semanal` | 3.911 | o status de toda sexta: % concluído, farol do gerente, texto livre com bloqueios |
| `excel_tarefas` | 1.663 | as 20 planilhas (colunas renomeadas, tudo texto) + `arquivo` |
| `clickup_tarefas` | 2.119 | as tarefas das 25 listas: `list_id`, `status` (struct), datas em ms, `custom_fields` (lista) |
| `msproject_tarefas` | 1.260 | as `<Task>` dos 15 XML: `UID`, `OutlineLevel`, `Summary`, `Work`, `Baseline` (struct), `arquivo` |
| `colaboradores` | 523 | as 520 pessoas (3 duplicadas): papel, senioridade, custo/hora |
| `apontamentos` | 30.883 | timesheet semanal: horas disponíveis × apontadas por pessoa e projeto |
| `custos` | 23.640 | lançamentos de custo real (pessoal, consultoria, cloud, licenças, despesas) |
| `entregas_fornecedor` | 640 | entregas das consultorias: prometido × entregue |

As **18 sujeiras** da bronze e o tratamento de cada uma estão em [`docs/sujeiras.md`](docs/sujeiras.md).
O teste de uma boa limpeza: o custo total não muda (R$ 193,35 mi na bronze = na silver) e as horas
de cada planilha batem com a linha de TOTAL.

---

## 3. Arquitetura

```
 job farol_projeto_job · toda segunda às 6h · ~4 min de ponta a ponta
 ingestao_data_lake → conferencia_bronze → medalhao ─┬─ testes_de_qualidade ─┬─ metricas_governadas
 (notebook, boto3)     (sql_task)          (pipeline) └─ status_com_ia ───────┘   (metric view)
                                           silver ×7 → gold ×3                 ai_classify + ai_extract

 recursos do bundle: dashboard "Projeto Farol · Portfólio" · Genie "Farol · Diretoria"
 bundle próprio:     app minha-torre/ (Databricks Apps + AppKit)
```

- **Um bundle só** (`databricks.yml` na raiz) com o job, o pipeline, o dashboard e o Genie.
  O app é um bundle à parte em `minha-torre/` (excluído do `sync` da raiz).
- **Silver e gold num pipeline declarativo** (Lakeflow Spark Declarative Pipelines, SQL, serverless).
  Silver = schema padrão do pipeline; gold = nome completo `farol_projeto.gold.x`. Um arquivo por
  assunto em `src/silver/` e `src/gold/`. Qualidade com `CONSTRAINT ... EXPECT (...) ON VIOLATION FAIL UPDATE`.
- **A integração mora em `silver.tarefas`**: três `CREATE TEMPORARY VIEW` (uma por ferramenta,
  todas com as mesmas 13 colunas) e um `UNION ALL` numa materialized view.
- **O histórico do avanço vem do status semanal**: as ferramentas só guardam o % de hoje.
  `gold.fato_projeto_semana` usa o % de cada sexta; `gold.projeto_situacao_atual` usa as tarefas.
- **Pouca tabela, de propósito.** Silver: `projetos`, `tarefas`, `status_semanal`, `custos`,
  `colaboradores`, `apontamentos`, `entregas_fornecedor`. Gold: `fato_projeto_semana`,
  `projeto_situacao_atual`, `utilizacao_pessoa_semana`, `status_estruturado` e a metric view
  `mv_projetos`. Fornecedor é lido direto da silver. Não crie `dim_projeto`.
- **IA, testes e métricas como `sql_task`** no warehouse, com o caminho completo das tabelas.
- **Dashboard e Genie como código**: o JSON de cada um é gerado por `scripts/gerar_dashboard.py`
  e `scripts/gerar_genie.py`. Nunca edite no workspace (trava o próximo deploy com "modified remotely").

---

## 4. Armadilhas já resolvidas (Databricks Free Edition)

### Bundle, pipeline e job

| Armadilha | O que fazer |
|---|---|
| `mode: development` prefixa nomes com `[dev usuario]` | Não use. No target `dev`, `presets: { trigger_pause_status: PAUSED }` |
| `bundle generate job` grava as chaves do S3 em texto no YAML | Trocar por `${var.…}` (`scripts/tirar_chaves.py`) antes de qualquer commit |
| Função de janela dentro de agregação dá erro no pipeline | Janela num CTE, agregação no CTE seguinte |
| `CREATE OR REPLACE` não existe no pipeline | `CREATE OR REFRESH MATERIALIZED VIEW` e `CREATE TEMPORARY VIEW` |
| `try_cast` em `'12345,67'` devolve NULL em silêncio (R$ 5,4 mi sumiriam) | `replace(',', '.')` antes do `CAST`, e o teste do custo total |
| Apagar o pipeline **não** apaga as materialized views | Apagar silver e gold tabela a tabela |
| Supabase Free pausa o projeto por inatividade e a ingestão falha em ~20 s | Reativar o projeto no Supabase; o job volta a rodar verde |

### IA, métricas e Genie

| Armadilha | O que fazer |
|---|---|
| `ai_classify` + `ai_extract` levam ~5 s por texto | IA só nos status **com bloqueio** dos **últimos 90 dias** (163); regra e palavra-chave no resto; `MERGE` incremental |
| `ai_extract` sem schema devolve tudo como texto | Versão 2.0 com JSON schema tipado: `ai_extract(texto, '{...}', map('version','2.0')):response` |
| Metric view pelo `aitools tools query` perde a indentação do YAML | Rodar como `sql_task` ou com `python scripts/run_sql.py` (API de statements) |
| A `sql_task` corta o arquivo em todo `;`, inclusive dentro do `$$ ... $$` | Nada de `;` dentro do YAML da metric view, nem em comentário |
| Genie do bundle falha no deploy com `Table ... does not exist` | Do zero: deploy → run do job → deploy |

### App (Databricks Apps + AppKit)

| Armadilha | O que fazer |
|---|---|
| O app é um usuário do Unity Catalog e nasce sem acesso: o build falha com `INSUFFICIENT_PERMISSIONS` | `scripts/conceder-acesso.sh`: `USE CATALOG`, `USE SCHEMA` e `SELECT` na silver e na gold para o service principal |
| O warehouse devolve **todo número e booleano como texto** (`"false"` é verdadeiro em JavaScript) | `Number()` nos números e comparação explícita com `"true"` (`verdadeiro()` em `lib/formatar.ts`) |
| Chat do Genie: `OAuth token does not have required scopes: genie` | `user_api_scopes` com `genie` (o nome antigo era `dashboards.genie`), reiniciar o app e autorizar de novo |
| Query de `config/queries/` com tabela inexistente quebra o build | Tabela opcional (o score de ML) é lida por uma rota do servidor que responde `{disponivel:false}` |
| `bundle deploy` cria o app parado | O código sobe com `databricks apps deploy` |

---

## 5. Convenções

- snake_case e português, como na bronze. Caminho completo nas `sql_task`.
- `COMMENT` em toda tabela da silver e da gold: é o que o Genie lê.
- SQL legível > SQL esperto. Comentário explica o **porquê**, não o quê.
- Razões da carteira são sempre `SUM/SUM`, nunca média de razões.
- Sempre `--profile DEFAULT` nos comandos `databricks`.
- Telas do app em português, valores em R$ e índices com 2 casas.

---

## 6. Números de referência (seed 42)

Conferidos por `tests/verificacao-final.sql` (19 itens) e pelos 10 testes do job.

| O que | Valor |
|---|---|
| Tarefas na silver | 4.917: Excel 1.643, ClickUp 2.119, MS Project 1.155 |
| Projetos em andamento | 41 (19 concluídos) |
| Críticos / em atenção / melancias | 7 / 10 / 4 (PRJ-012, PRJ-028, PRJ-034, PRJ-042) |
| Estouro previsto (em andamento) | R$ 6,47 mi |
| SPI / CPI da carteira | 0,92 / 0,96 |
| Custo real total | R$ 193,35 mi |
| Entregas em atraso | 5, todas da CodeForge (prazo real ÷ prometido = 1,41) |
| SREs com < 20% de uso (12 semanas) | COL0017 e COL0018, no PRJ-007 (5,8% e 5,5%) |
| PRJ-011 | falta de SRE, 12 semanas, 57 dias de impacto declarado |
| Status classificados pela IA | 163 (últimos 90 dias, com bloqueio) |
| Genie "Farol · Diretoria" | 20/20 em `tests/genie-benchmark-diretoria.json` |
| Job | 6 tarefas, ~4 min de ponta a ponta |

---

Case e dataset sintético da imersão Jornada de Dados (Luciano Vasconcelos), refeito e adaptado por Jéssica Fuentes.
