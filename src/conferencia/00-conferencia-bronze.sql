-- Conferência da bronze: antes de transformar, a ingestão trouxe tudo?
-- Compara a contagem de cada uma das 9 tabelas com o esperado (seed 42).
-- Uma linha por tabela (esperado × obtido). Se alguma divergir, raise_error:
-- a tarefa falha e o medalhão nem começa.
-- (Um statement só: a sql_task mostra o resultado do último.)

WITH esperado (tabela, esperado) AS (
  VALUES
    ('projetos',             60),
    ('status_semanal',     3911),
    ('excel_tarefas',      1663),
    ('clickup_tarefas',    2119),
    ('msproject_tarefas',  1260),
    ('colaboradores',       523),
    ('apontamentos',      30883),
    ('custos',            23640),
    ('entregas_fornecedor', 640)
),
obtido AS (
  SELECT 'projetos'            AS tabela, count(*) AS obtido FROM farol_projeto.bronze.projetos
  UNION ALL SELECT 'status_semanal',      count(*) FROM farol_projeto.bronze.status_semanal
  UNION ALL SELECT 'excel_tarefas',       count(*) FROM farol_projeto.bronze.excel_tarefas
  UNION ALL SELECT 'clickup_tarefas',     count(*) FROM farol_projeto.bronze.clickup_tarefas
  UNION ALL SELECT 'msproject_tarefas',   count(*) FROM farol_projeto.bronze.msproject_tarefas
  UNION ALL SELECT 'colaboradores',       count(*) FROM farol_projeto.bronze.colaboradores
  UNION ALL SELECT 'apontamentos',        count(*) FROM farol_projeto.bronze.apontamentos
  UNION ALL SELECT 'custos',              count(*) FROM farol_projeto.bronze.custos
  UNION ALL SELECT 'entregas_fornecedor', count(*) FROM farol_projeto.bronze.entregas_fornecedor
),
conferencia AS (
  SELECT e.tabela, e.esperado, coalesce(o.obtido, 0) AS obtido
  FROM esperado e
  LEFT JOIN obtido o USING (tabela)
),
com_divergencias AS (
  -- a lista de todas as tabelas que divergem, repetida em cada linha
  SELECT *,
         array_join(collect_list(CASE WHEN esperado <> obtido
                                      THEN concat(tabela, ' (esperado ', esperado, ', obtido ', obtido, ')') END)
                    OVER (), '; ') AS divergentes
  FROM conferencia
)
SELECT
  tabela,
  esperado,
  obtido,
  CASE
    WHEN divergentes = '' THEN 'ok'
    ELSE raise_error(concat('Bronze diverge do esperado em: ', divergentes,
                            '. Olhe a saída da tarefa ingestao_data_lake.'))
  END AS resultado
FROM com_divergencias
ORDER BY tabela;
