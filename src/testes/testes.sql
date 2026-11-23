-- Testes de qualidade da silver e da gold. Roda depois do medalhão.
-- Uma linha por teste (o que foi medido e se passou). Se algum falhar, raise_error
-- com a lista dos que falharam e o job para.
-- (Um statement só: a sql_task mostra o resultado do último.)

WITH
-- 1 · os 60 projetos têm cronograma na silver.tarefas
t1 AS (
  SELECT count(DISTINCT t.projeto_id) AS medido
  FROM farol_projeto.silver.tarefas t
  JOIN farol_projeto.silver.projetos p ON p.projeto_id = t.projeto_id
),
-- 2 · cada projeto veio de UMA ferramenta, a do cadastro do PMO
t2 AS (
  SELECT count(*) AS medido
  FROM (
    SELECT t.projeto_id
    FROM farol_projeto.silver.tarefas t
    JOIN farol_projeto.silver.projetos p ON p.projeto_id = t.projeto_id
    GROUP BY t.projeto_id
    HAVING count(DISTINCT t.ferramenta) <> 1 OR max(t.ferramenta) <> max(p.ferramenta)
  )
),
-- 3 · as horas do Excel na silver = a soma das linhas de TOTAL das planilhas
t3 AS (
  SELECT
    (SELECT sum(horas) FROM farol_projeto.silver.tarefas WHERE ferramenta = 'excel') AS silver,
    (SELECT sum(CAST(replace(horas_previstas, 'h', '') AS DOUBLE))
       FROM farol_projeto.bronze.excel_tarefas WHERE tarefa = 'TOTAL')              AS total
),
-- 4 · uma linha por pessoa na silver
t4 AS (
  SELECT count(*) AS linhas, count(DISTINCT colaborador_id) AS pessoas
  FROM farol_projeto.silver.colaboradores
),
-- 5 · a CodeForge virou um fornecedor só
t5 AS (
  SELECT count(DISTINCT fornecedor) AS medido
  FROM farol_projeto.silver.entregas_fornecedor
  WHERE replace(lower(fornecedor_como_veio), ' ', '') LIKE '%codeforge%'
),
-- 6 · a limpeza não mudou o custo total (bronze com replace = silver)
t6 AS (
  SELECT
    (SELECT sum(CAST(replace(valor, ',', '.') AS DECIMAL(15, 2))) FROM farol_projeto.bronze.custos) AS bronze,
    (SELECT sum(valor) FROM farol_projeto.silver.custos)                                           AS silver
),
-- 7 · os 60 projetos têm fotografia de hoje
t7 AS (
  SELECT count(DISTINCT projeto) AS medido FROM farol_projeto.gold.projeto_situacao_atual
),
-- 8 · todo projeto em andamento tem SPI e CPI
t8 AS (
  SELECT count(*) AS medido
  FROM farol_projeto.gold.projeto_situacao_atual
  WHERE status = 'em_andamento' AND (spi IS NULL OR cpi IS NULL)
),
-- 9 · o EV de hoje do status semanal (fato) bate com o das ferramentas (situação), na carteira: diferença < 1%
t9 AS (
  SELECT
    (SELECT sum(ev) FROM farol_projeto.gold.fato_projeto_semana WHERE semana = DATE'2026-10-16') AS ev_status,
    (SELECT sum(ev) FROM farol_projeto.gold.projeto_situacao_atual)                               AS ev_ferramentas
),
-- 10 · AC de hoje no fato = soma dos lançamentos até hoje
t10 AS (
  SELECT
    (SELECT sum(ac) FROM farol_projeto.gold.fato_projeto_semana WHERE semana = DATE'2026-10-16') AS ac_fato,
    (SELECT sum(valor) FROM farol_projeto.silver.custos WHERE data <= DATE'2026-10-16')           AS ac_lancamentos
),
resultados AS (
  SELECT 1 AS n, 'os 60 projetos têm cronograma na silver.tarefas' AS teste,
         concat(medido, ' projetos') AS medido, medido = 60 AS passou FROM t1
  UNION ALL
  SELECT 2, 'cada projeto veio de UMA ferramenta, a do cadastro',
         concat(medido, ' projetos fora da regra'), medido = 0 FROM t2
  UNION ALL
  SELECT 3, 'horas do Excel na silver = soma das linhas de TOTAL',
         concat(round(silver, 1), ' × ', round(total, 1)), abs(silver - total) < 0.01 FROM t3
  UNION ALL
  SELECT 4, 'uma linha por pessoa na silver',
         concat(linhas, ' linhas, ', pessoas, ' pessoas'), linhas = pessoas FROM t4
  UNION ALL
  SELECT 5, 'a CodeForge virou um fornecedor só',
         concat(medido, ' grafia(s)'), medido = 1 FROM t5
  UNION ALL
  SELECT 6, 'a limpeza não mudou o custo total',
         concat('bronze ', bronze, ' × silver ', silver), bronze = silver FROM t6
  UNION ALL
  SELECT 7, 'os 60 projetos têm fotografia de hoje',
         concat(medido, ' projetos'), medido = 60 FROM t7
  UNION ALL
  SELECT 8, 'todo projeto em andamento tem SPI e CPI',
         concat(medido, ' sem SPI ou CPI'), medido = 0 FROM t8
  UNION ALL
  SELECT 9, 'EV de hoje: status semanal × ferramentas (< 1%)',
         concat(round(ev_status / 1e6, 2), ' mi × ', round(ev_ferramentas / 1e6, 2), ' mi (',
                round(abs(ev_status - ev_ferramentas) / ev_ferramentas * 100, 2), '%)'),
         abs(ev_status - ev_ferramentas) / ev_ferramentas < 0.01 FROM t9
  UNION ALL
  SELECT 10, 'AC de hoje no fato = soma dos lançamentos até hoje',
         concat(round(ac_fato, 2), ' × ', round(ac_lancamentos, 2)), abs(ac_fato - ac_lancamentos) < 0.01 FROM t10
),
com_falhas AS (
  SELECT *,
         array_join(collect_list(CASE WHEN NOT coalesce(passou, false) THEN concat(n, ' (', teste, ': ', medido, ')') END)
                    OVER (), '; ') AS falhas
  FROM resultados
)
SELECT
  n,
  teste,
  medido,
  CASE
    WHEN falhas = '' THEN 'ok'
    ELSE raise_error(concat('Testes de qualidade falharam: ', falhas))
  END AS resultado
FROM com_falhas
ORDER BY n;
