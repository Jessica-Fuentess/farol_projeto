# Qualidade de dados

Cinco camadas, da entrada à resposta do agente. Se uma falha, o problema aparece antes de chegar no painel.

| # | Camada | Onde | O que garante |
|---|---|---|---|
| 1 | **Conferência da bronze** | [`src/conferencia/00-conferencia-bronze.sql`](../src/conferencia/00-conferencia-bronze.sql) | As 9 tabelas chegaram com a contagem esperada. Se não, `raise_error` e o pipeline nem começa |
| 2 | **Expectations no pipeline** | `CONSTRAINT ... EXPECT ... ON VIOLATION FAIL UPDATE` em `src/silver/` e `src/gold/` | Data válida, farol conhecido, % entre 0 e 100, horas positivas, todo projeto encontrado na integração |
| 3 | **10 testes de qualidade** | [`src/testes/testes.sql`](../src/testes/testes.sql), tarefa do job | Regras de negócio entre camadas (lista abaixo). Se algum falha, o job para |
| 4 | **Verificação final** | [`verificacao-final.sql`](verificacao-final.sql) | 19 números de negócio, do bronze à gold, contra os valores de referência |
| 5 | **Benchmark do agente** | [`genie-benchmark-diretoria.json`](genie-benchmark-diretoria.json) | 20 perguntas com resposta conhecida para o Genie: **20/20** |

## Os 10 testes do job

1. Os 60 projetos têm cronograma na `silver.tarefas`
2. Cada projeto veio de **uma** ferramenta, a do cadastro do PMO
3. As horas do Excel na silver = a soma das linhas de TOTAL das planilhas
4. Uma linha por pessoa na silver (os 3 cadastros duplicados resolvidos)
5. A CodeForge (4 grafias) virou um fornecedor só
6. A limpeza não mudou o custo total (bronze com `replace` = silver)
7. Os 60 projetos têm fotografia de hoje na gold
8. Todo projeto em andamento tem SPI e CPI
9. O EV de hoje do status semanal bate com o das ferramentas (diferença < 1% na carteira)
10. O custo real (AC) de hoje no fato = a soma dos lançamentos até hoje

## Como rodar

```bash
# camadas 1 a 3 rodam sozinhas no job (toda segunda, ou sob demanda)
databricks bundle run farol_projeto_job --profile DEFAULT

# camada 4
python scripts/run_sql.py tests/verificacao-final.sql --profile DEFAULT

# camada 5
python scripts/genie.py benchmark "Farol · Diretoria" tests/genie-benchmark-diretoria.json --profile DEFAULT
```
