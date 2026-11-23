# Decisões técnicas e problemas resolvidos

O que foi decidido, por quê, e os problemas reais que apareceram no caminho.

## Decisões de arquitetura

| Decisão | Por quê |
|---|---|
| **Arquitetura medalhão** (bronze → silver → gold) | A bronze guarda o dado como veio: se a limpeza errar, dá para voltar na origem e comparar. A silver limpa e integra; a gold responde as perguntas de negócio |
| **Pipeline declarativo** (Lakeflow, SQL, materialized views) | O Databricks resolve a ordem e as dependências entre as tabelas. Cada regra de qualidade é um `EXPECT ... ON VIOLATION FAIL UPDATE`: dado ruim para o pipeline em vez de chegar no painel |
| **Três ferramentas → uma tabela** (`silver.tarefas`) | Uma visão temporária por ferramenta, todas com as mesmas 13 colunas, e um `UNION ALL`. Daí em diante o resto do pipeline não sabe (nem precisa saber) de onde veio a tarefa |
| **Pouca tabela, de propósito** | 7 na silver, 4 na gold e uma metric view. A `projeto_situacao_atual` já traz o cadastro: não há `dim_projeto` para manter |
| **Data de referência fixa** (`DATE'2026-10-16'`) | Com `current_date()` os números mudariam todo dia e nenhum teste bateria. Reprodutibilidade primeiro |
| **Gestão por valor agregado (EVM)** | SPI e CPI saem das horas e do % das tarefas, não do farol que o gerente pinta. É isso que revela as **melancias**: verde no status, SPI < 0,9 no número |
| **IA só onde ela vale o custo** | `ai_classify` + `ai_extract` levam ~5 s por texto. A IA lê só os 163 status com bloqueio dos últimos 90 dias; regra para "sem bloqueio" e palavra-chave para o histórico. A tabela acumula com `MERGE`: a IA nunca reclassifica o mesmo texto |
| **Saída da IA tipada** | `ai_extract` 2.0 com JSON schema (`dias_impacto` como número), em vez de texto livre para converter depois |
| **Métricas governadas** (metric view `mv_projetos`) | A fórmula de cada KPI num lugar só. Razão da carteira é sempre `SUM(ev)/SUM(pv)`, nunca a média dos SPIs dos projetos |
| **Tudo como código** (Declarative Automation Bundles) | Job, pipeline, dashboard e Genie sobem com `databricks bundle deploy`. O ambiente inteiro é recriável a partir do repositório |
| **Segredos fora do Git** | As chaves do data lake são variáveis do bundle; o valor fica em `.databricks/`, ignorado pelo Git |
| **Genie em nome de quem pergunta** (user authorization) | O agente consulta com as permissões do usuário no Unity Catalog, não com as do app |
| **Recurso opcional não quebra o build** | O score de ML pode não existir: o app lê por uma rota do servidor que responde `{disponivel:false}` em vez de falhar |

## Problemas reais e como foram resolvidos

| Sintoma | Causa | Solução |
|---|---|---|
| A ingestão passou a falhar em ~20 s, todos os dias | O projeto do Supabase (plano Free) foi **pausado por inatividade** | Reativar o projeto; o job voltou a rodar verde. Primeira coisa a conferir quando a ingestão falha "do nada" |
| A verificação final falhou no item "custos com vírgula decimal" | A silver tratava a vírgula, mas não **registrava** quais linhas vieram assim | Flag `valor_veio_com_virgula` na silver: a correção foi na camada certa e nada mais mudou |
| O 🍉 aparecia em **todos** os projetos no app | O warehouse devolve booleano como texto, e `"false"` é verdadeiro em JavaScript | Comparação explícita com `"true"`; a tela passou a mostrar exatamente as 4 melancias |
| Chat do agente: `OAuth token does not have required scopes: genie` | O escopo mudou de nome (`dashboards.genie` → `genie`) e a autorização antiga continuava em cache | Escopo `genie` no `user_api_scopes`, reinício do app e nova autorização |
| O build do app falhou com `INSUFFICIENT_PERMISSIONS` | O app é um usuário do Unity Catalog e nasce sem acesso | `scripts/conceder-acesso.sh` dá `USE CATALOG`, `USE SCHEMA` e `SELECT` ao service principal |
| A metric view quebrava ao rodar pelo CLI | O comando achatava a indentação do YAML; e a `sql_task` corta o arquivo em todo `;` | `scripts/run_sql.py` (API de statements) e nenhum `;` dentro do YAML |
| A resposta do agente para "o que vai dar errado no próximo mês?" deixava entregas atrasadas de fora e não dizia o que fazer | A instrução do Genie filtrava as entregas por data | Instrução ajustada (sem o filtro, com ações concretas) e benchmark de novo: **20/20**, sem piorar nenhuma pergunta |

## Números do resultado

- **4.917 tarefas** de 3 ferramentas integradas num modelo só, sem perder um centavo
  (R$ 193,35 mi de custo na bronze = na silver).
- **17 de 41** projetos em risco, **R$ 6,47 mi** de estouro previsto e **4 melancias** encontradas.
- **2 SREs** com ~5% de uso no PRJ-007 enquanto o PRJ-011 ficou 12 semanas travado por falta de SRE.
- **Job de ponta a ponta em ~4 min**, toda segunda, com 10 testes de qualidade e 19 números conferidos.
