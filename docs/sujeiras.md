# Os 18 tipos de sujeira da bronze

A bronze chega com sujeira proposital. Cada tipo é tratado na silver (`src/silver/`).
Dois testes mostram que a limpeza não perdeu nada: o custo total da bronze é igual ao da
silver (R$ 193,35 mi), e as horas de cada planilha Excel batem com a linha de TOTAL dela.

| Nº | Sujeira | Tabela.coluna (bronze) | Tratamento |
|---|---|---|---|
| 1 | Data em `yyyy-MM-dd` e `dd/MM/yyyy` | `projetos.data_inicio` (24 de 60) | `coalesce` de dois `try_to_date` |
| 2 | Ferramenta escrita de 8 jeitos | `projetos.ferramenta` | `excel`, `clickup` ou `msproject` por `LIKE` |
| 3 | Código da ferramenta vazio | `projetos.codigo_ferramenta` (2) | Excel pelo `PRJ-xxx` do nome do arquivo, ClickUp pelo nome da lista |
| 4 | Data em texto **ou** número de série do Excel | `excel_tarefas.inicio_previsto`, `termino_previsto`, `inicio_real`, `termino_real` | com `/` é `dd/MM/yyyy`, senão `date_add(DATE'1899-12-30', n)` |
| 5 | % em `'45%'`, `'10,5%'` ou `0.45`; 11 acima de 100 | `excel_tarefas.pct_concluido` | normaliza, `least(…, 100)` e flag `pct_veio_acima_de_100` |
| 6 | Linha de TOTAL no fim da planilha | `excel_tarefas.tarefa` (20 linhas) | `WHERE tarefa <> 'TOTAL'` + teste: soma da silver = TOTAL |
| 7 | Horas como `'40h'` | `excel_tarefas.horas_previstas` | `replace(x, 'h', '')` |
| 8 | Datas em milissegundos; % e baseline dentro de uma lista | `clickup_tarefas.start_date`, `date_done`, `custom_fields` | `to_date(timestamp_millis(…))` e `filter(custom_fields, f -> f.name = '…')[0].value` |
| 9 | Status escrito de 12 jeitos | `clickup_tarefas.status.status` | `concluida`, `a_fazer` ou `em_andamento` |
| 10 | Tarefas-resumo somando as horas de baixo | `msproject_tarefas.Summary` (105 linhas) | `WHERE Summary = 0` |
| 11 | A fase não está na tarefa | `msproject_tarefas.OutlineLevel`, `Name` | `last_value(CASE WHEN OutlineLevel = 1 THEN Name END, true) OVER (…)` |
| 12 | Horas como `'PT40H0M0S'` | `msproject_tarefas.Work` | `regexp_extract(Work, 'PT([0-9]+)H', 1)` |
| 13 | Vírgula decimal `12345,67` | `custos.valor` (671) | `replace(',', '.')` antes do `CAST` (nunca `try_cast`) + flag `valor_veio_com_virgula` |
| 14 | Estorno como valor negativo | `custos.valor` (331) | **mantido** (o custo é líquido) + flag `estorno` |
| 15 | A mesma consultoria com 4 grafias | `entregas_fornecedor.fornecedor` | normaliza para `CodeForge Consultoria Ltda` e guarda `fornecedor_como_veio` |
| 16 | Pessoa cadastrada duas vezes | `colaboradores` (COL0102, COL0257, COL0433) | fica o cadastro com `papel` em minúsculas (`row_number`) |
| 17 | Farol como `'Verde'`, `'VERDE'` | `status_semanal.farol` | `lower(trim())` |
| 18 | Status vazio (`''`, `N/A`, `ver ata da reunião`) | `status_semanal.texto_status` (51) | **não descartado**: flag `status_vazio` |

Os 18 são tipos de sujeira, não colunas: o 4 e o 8 envolvem várias colunas cada.
