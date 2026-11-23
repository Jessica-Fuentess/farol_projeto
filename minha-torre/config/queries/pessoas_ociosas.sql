-- Pessoas com utilização < 20% nas últimas 12 semanas (sextas de 31/07 a
-- 16/10/2026), por projeto. Horas paradas e custo ocioso são MÉDIAS por
-- semana: o simulador multiplica por 4 para chegar ao mês.
WITH ultimas_12_semanas AS (
  SELECT *
  FROM farol_projeto.gold.utilizacao_pessoa_semana
  WHERE semana > DATE'2026-10-16' - INTERVAL 84 DAYS
),
por_pessoa AS (
  SELECT
    colaborador_id, nome, papel, senioridade, projeto_id,
    count(DISTINCT semana)                        AS semanas,
    sum(horas_apontadas) / sum(horas_disponiveis) AS utilizacao,
    sum(horas_ociosas)   / count(DISTINCT semana) AS horas_ociosas_semana,
    sum(custo_ocioso)    / count(DISTINCT semana) AS custo_ocioso_semana
  FROM ultimas_12_semanas
  GROUP BY colaborador_id, nome, papel, senioridade, projeto_id
)
SELECT
  o.colaborador_id,
  o.nome,
  o.papel,
  o.senioridade,
  o.projeto_id,
  o.semanas,
  round(o.utilizacao, 4)            AS utilizacao,
  round(o.horas_ociosas_semana, 2)  AS horas_ociosas_semana,
  round(o.custo_ocioso_semana, 2)   AS custo_ocioso_semana,
  c.custo_hora
FROM por_pessoa o
JOIN farol_projeto.silver.colaboradores c USING (colaborador_id)
WHERE o.utilizacao < 0.20
ORDER BY o.utilizacao, o.colaborador_id
