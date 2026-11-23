-- silver.tarefas: AS TRÊS FERRAMENTAS VIRAM UMA.
-- Cada ferramenta tem a sua visão temporária, todas com as MESMAS 13 colunas:
--   projeto_id, ferramenta, id_na_ferramenta, fase, tarefa, responsavel,
--   inicio_baseline, fim_baseline, inicio_real, fim_real,
--   pct_como_veio, horas, status_na_ferramenta
-- e no fim um UNION ALL junta as três numa tabela só.


-- ============================================================
-- 1 · Excel (20 planilhas): tudo chega como texto
-- ============================================================
CREATE TEMPORARY VIEW tarefas_excel AS
WITH planilha AS (
  SELECT
    e.*,
    -- de-para: o código na ferramenta é o nome do arquivo. Se não casar (código vazio,
    -- ou o arquivo chegou sem acento: 'Core bancario' × 'Core bancário'), o PRJ-xxx do nome do arquivo.
    coalesce(p.projeto_id, regexp_extract(e.arquivo, 'PRJ-[0-9]{3}', 0)) AS projeto_id_resolvido
  FROM farol_projeto.bronze.excel_tarefas e
  LEFT JOIN projetos p
    ON p.ferramenta = 'excel' AND p.codigo_ferramenta = e.arquivo
  WHERE e.tarefa <> 'TOTAL'                       -- sujeira 6: a linha de TOTAL soma as de cima
)
SELECT
  projeto_id_resolvido                             AS projeto_id,
  'excel'                                          AS ferramenta,
  CAST(id AS STRING)                               AS id_na_ferramenta,
  fase,
  tarefa,
  responsavel,
  -- sujeira 4: data com '/' é dd/MM/yyyy; sem '/' é o número de série do Excel (dias desde 30/12/1899)
  CASE WHEN inicio_previsto  LIKE '%/%' THEN to_date(inicio_previsto, 'dd/MM/yyyy')
       ELSE date_add(DATE'1899-12-30', CAST(nullif(trim(inicio_previsto), '') AS INT)) END  AS inicio_baseline,
  CASE WHEN termino_previsto LIKE '%/%' THEN to_date(termino_previsto, 'dd/MM/yyyy')
       ELSE date_add(DATE'1899-12-30', CAST(nullif(trim(termino_previsto), '') AS INT)) END AS fim_baseline,
  CASE WHEN inicio_real      LIKE '%/%' THEN to_date(inicio_real, 'dd/MM/yyyy')
       ELSE date_add(DATE'1899-12-30', CAST(nullif(trim(inicio_real), '') AS INT)) END      AS inicio_real,
  CASE WHEN termino_real     LIKE '%/%' THEN to_date(termino_real, 'dd/MM/yyyy')
       ELSE date_add(DATE'1899-12-30', CAST(nullif(trim(termino_real), '') AS INT)) END     AS fim_real,
  -- sujeira 5: '45%' ou '10,5%' → tira o % e troca a vírgula; sem % é fração (0.45) → × 100
  CASE WHEN contains(pct_concluido, '%')
       THEN CAST(replace(replace(pct_concluido, '%', ''), ',', '.') AS DOUBLE)
       ELSE CAST(pct_concluido AS DOUBLE) * 100 END                                          AS pct_como_veio,
  -- sujeira 7: horas '40h'
  CAST(replace(horas_previstas, 'h', '') AS DOUBLE)                                          AS horas,
  CAST(NULL AS STRING)                                                                       AS status_na_ferramenta
FROM planilha;


-- ============================================================
-- 2 · ClickUp (25 listas): datas em milissegundos, % e baseline em custom_fields
-- ============================================================
CREATE TEMPORARY VIEW tarefas_clickup AS
WITH lista AS (
  SELECT
    c.*,
    -- de-para: o código na ferramenta é o list_id; se o código faltar, casa pelo nome da lista
    coalesce(p_codigo.projeto_id, p_nome.projeto_id) AS projeto_id_resolvido,
    filter(c.custom_fields, f -> f.name = 'Progresso (%)')[0].value   AS cf_progresso,
    filter(c.custom_fields, f -> f.name = 'Início baseline')[0].value AS cf_inicio_baseline,
    filter(c.custom_fields, f -> f.name = 'Fim baseline')[0].value    AS cf_fim_baseline,
    filter(c.custom_fields, f -> f.name = 'Fase')[0].value            AS cf_fase
  FROM farol_projeto.bronze.clickup_tarefas c
  LEFT JOIN projetos p_codigo
    ON p_codigo.ferramenta = 'clickup' AND p_codigo.codigo_ferramenta = c.list_id
  LEFT JOIN projetos p_nome
    ON p_nome.ferramenta = 'clickup' AND p_nome.codigo_ferramenta IS NULL AND p_nome.nome_projeto = c.list_name
)
SELECT
  projeto_id_resolvido                                                 AS projeto_id,
  'clickup'                                                            AS ferramenta,
  id                                                                   AS id_na_ferramenta,
  initcap(cf_fase)                                                     AS fase,
  name                                                                 AS tarefa,
  assignees[0].username                                                AS responsavel,
  -- sujeira 8: datas em milissegundos desde 1970
  to_date(timestamp_millis(CAST(cf_inicio_baseline AS BIGINT)))        AS inicio_baseline,
  to_date(timestamp_millis(CAST(cf_fim_baseline    AS BIGINT)))        AS fim_baseline,
  to_date(timestamp_millis(CAST(start_date         AS BIGINT)))        AS inicio_real,
  to_date(timestamp_millis(CAST(date_done          AS BIGINT)))        AS fim_real,
  CAST(cf_progresso AS DOUBLE)                                         AS pct_como_veio,
  time_estimate / 3600000.0                                            AS horas,   -- ms → horas
  -- sujeira 9: o status escrito de 12 jeitos vira 3
  CASE
    WHEN lower(trim(status.status)) IN ('done', 'concluído', 'concluido', 'closed')                  THEN 'concluida'
    WHEN lower(trim(status.status)) IN ('to do', 'backlog', 'a fazer')                               THEN 'a_fazer'
    WHEN lower(trim(status.status)) IN ('in progress', 'em andamento', 'review', 'doing')             THEN 'em_andamento'
  END                                                                  AS status_na_ferramenta
FROM lista;


-- ============================================================
-- 3 · MS Project (15 XML): só as tarefas de verdade, a fase vem da tarefa-resumo
-- ============================================================
CREATE TEMPORARY VIEW tarefas_msproject AS
WITH com_fase AS (
  SELECT
    m.*,
    p.projeto_id,
    -- sujeira 11: a fase é a última tarefa-resumo de nível 1 que aparece antes da tarefa
    last_value(CASE WHEN m.OutlineLevel = 1 THEN m.Name END, true)
      OVER (PARTITION BY m.arquivo ORDER BY m.UID) AS fase
  FROM farol_projeto.bronze.msproject_tarefas m
  LEFT JOIN projetos p
    ON p.ferramenta = 'msproject' AND p.codigo_ferramenta = m.arquivo
)
SELECT
  projeto_id,
  'msproject'                                                          AS ferramenta,
  CAST(UID AS STRING)                                                  AS id_na_ferramenta,
  fase,
  Name                                                                 AS tarefa,
  CAST(NULL AS STRING)                                                 AS responsavel,
  to_date(Baseline.Start)                                              AS inicio_baseline,
  to_date(Baseline.Finish)                                             AS fim_baseline,
  to_date(ActualStart)                                                 AS inicio_real,
  to_date(ActualFinish)                                                AS fim_real,
  CAST(PercentComplete AS DOUBLE)                                      AS pct_como_veio,
  -- sujeira 12: horas em 'PT40H0M0S'
  CAST(regexp_extract(Work, 'PT([0-9]+)H', 1) AS DOUBLE)               AS horas,
  CAST(NULL AS STRING)                                                 AS status_na_ferramenta
FROM com_fase
WHERE Summary = 0;                                -- sujeira 10: as tarefas-resumo somam as de baixo


-- ============================================================
-- A tabela integrada
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW tarefas (
  CONSTRAINT achou_o_projeto  EXPECT (projeto_id IS NOT NULL)           ON VIOLATION FAIL UPDATE,
  CONSTRAINT pct_entre_0_e_100 EXPECT (pct_concluido BETWEEN 0 AND 100) ON VIOLATION FAIL UPDATE,
  CONSTRAINT horas_positivas  EXPECT (horas > 0)                        ON VIOLATION FAIL UPDATE
)
COMMENT 'Todas as tarefas dos cronogramas dos 60 projetos num modelo só (uma linha por tarefa): as 20 planilhas Excel, as 25 listas do ClickUp e os 15 arquivos do MS Project. Traz fase, responsável, datas baseline e reais, % concluído (limitado a 100, com flag quando veio acima) e horas previstas. É a fotografia de hoje do avanço: as ferramentas só guardam o % atual.'
AS
WITH tres_ferramentas AS (
  SELECT * FROM tarefas_excel
  UNION ALL
  SELECT * FROM tarefas_clickup
  UNION ALL
  SELECT * FROM tarefas_msproject
)
SELECT
  concat_ws('-', projeto_id, ferramenta, id_na_ferramenta) AS tarefa_id,
  projeto_id,
  ferramenta,
  id_na_ferramenta,
  fase,
  tarefa,
  responsavel,
  inicio_baseline,
  fim_baseline,
  inicio_real,
  fim_real,
  pct_como_veio,
  least(pct_como_veio, 100)    AS pct_concluido,           -- sujeira 5: 11 tarefas acima de 100%
  pct_como_veio > 100          AS pct_veio_acima_de_100,
  horas,
  status_na_ferramenta
FROM tres_ferramentas;
