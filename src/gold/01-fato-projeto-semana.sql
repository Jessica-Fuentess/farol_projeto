-- gold.fato_projeto_semana: a história de cada projeto, sexta a sexta.
-- Uma linha por projeto e semana, da semana do início até hoje (16/10/2026).
--   PV (valor planejado) = o que o baseline das tarefas dizia que já devia estar pronto
--   EV (valor agregado)  = o % que o gerente declarou no status daquela sexta
--   AC (custo real)      = tudo o que já se gastou até aquela sexta
-- O histórico do avanço vem do status semanal: as ferramentas só guardam o % de hoje.

CREATE OR REFRESH MATERIALIZED VIEW farol_projeto.gold.fato_projeto_semana (
  CONSTRAINT pv_nao_negativo     EXPECT (pv >= 0)          ON VIOLATION FAIL UPDATE,
  CONSTRAINT ev_ate_o_orcamento  EXPECT (ev <= orcamento)  ON VIOLATION FAIL UPDATE
)
COMMENT 'Evolução semanal de cada projeto (uma linha por projeto e sexta-feira, do início até 16/10/2026): PV, EV e AC acumulados, SPI (EV/PV, < 1 é atraso), CPI (EV/AC, < 1 é estouro), EAC (orçamento/CPI), % concluído e farol declarados pelo gerente no status semanal, e as horas disponíveis, apontadas e ociosas da equipe na semana.'
AS
WITH
-- 1 · as sextas de cada projeto, da semana do início até hoje
semanas AS (
  SELECT
    projeto_id,
    orcamento_custo AS orcamento,
    explode(sequence(date_add(date_trunc('WEEK', data_inicio), 4), DATE'2026-10-16', INTERVAL 1 WEEK)) AS semana
  FROM projetos
),

-- 2 · PV: em cada sexta, quanto do baseline de cada tarefa já devia ter passado (0 a 1), pesado pelas horas
tarefa_semana AS (
  SELECT
    s.projeto_id,
    s.semana,
    t.horas,
    CASE
      WHEN s.semana >= t.fim_baseline   THEN 1.0
      WHEN s.semana <  t.inicio_baseline THEN 0.0
      ELSE greatest(0, least(1, datediff(s.semana, t.inicio_baseline) / datediff(t.fim_baseline, t.inicio_baseline)))
    END AS fracao_baseline
  FROM semanas s
  JOIN tarefas t ON t.projeto_id = s.projeto_id
),
planejado AS (
  SELECT projeto_id, semana,
         sum(horas * fracao_baseline) / sum(horas) AS fracao_planejada
  FROM tarefa_semana
  GROUP BY projeto_id, semana
),

-- 3 · EV e farol: o status daquela sexta. Projeto concluído não publica mais: vale o último publicado
status_da_semana AS (
  SELECT
    s.projeto_id,
    s.semana,
    last_value(st.pct_concluido, true) OVER (PARTITION BY s.projeto_id ORDER BY s.semana) AS pct_concluido,
    last_value(st.farol, true)         OVER (PARTITION BY s.projeto_id ORDER BY s.semana) AS farol_do_gerente
  FROM semanas s
  LEFT JOIN status_semanal st
    ON st.projeto_id = s.projeto_id AND st.data_status = s.semana
),

-- 4 · AC: o custo de cada semana, e o acumulado até cada sexta (inclui o que foi gasto antes da 1ª sexta)
custo_semanal AS (
  SELECT projeto_id, semana, sum(valor) AS custo_semana
  FROM custos
  GROUP BY projeto_id, semana
),
custo_acumulado AS (
  SELECT s.projeto_id, s.semana,
         coalesce(sum(CASE WHEN c.semana = s.semana THEN c.custo_semana END), 0) AS custo_semana,
         coalesce(sum(c.custo_semana), 0)                                        AS ac
  FROM semanas s
  LEFT JOIN custo_semanal c
    ON c.projeto_id = s.projeto_id AND c.semana <= s.semana
  GROUP BY s.projeto_id, s.semana
),

-- 5 · as horas da equipe na semana (timesheet)
horas_semana AS (
  SELECT projeto_id, semana,
         sum(horas_disponiveis)                             AS horas_disponiveis,
         sum(horas_apontadas)                               AS horas_apontadas,
         sum(greatest(horas_disponiveis - horas_apontadas, 0)) AS horas_ociosas
  FROM apontamentos
  GROUP BY projeto_id, semana
),

-- 6 · tudo junto, com os valores em reais
valores AS (
  SELECT
    s.projeto_id,
    s.semana,
    CAST(s.orcamento AS DOUBLE)                                           AS orcamento,
    st.pct_concluido,
    st.farol_do_gerente,
    CAST(s.orcamento AS DOUBLE) * coalesce(pl.fracao_planejada, 0)        AS pv,
    CAST(s.orcamento AS DOUBLE) * coalesce(st.pct_concluido, 0) / 100     AS ev,
    CAST(ca.custo_semana AS DOUBLE)                                       AS custo_semana,
    CAST(ca.ac AS DOUBLE)                                                 AS ac,
    coalesce(h.horas_disponiveis, 0)                                      AS horas_disponiveis,
    coalesce(h.horas_apontadas, 0)                                        AS horas_apontadas,
    coalesce(h.horas_ociosas, 0)                                          AS horas_ociosas
  FROM semanas s
  LEFT JOIN planejado        pl ON pl.projeto_id = s.projeto_id AND pl.semana = s.semana
  LEFT JOIN status_da_semana st ON st.projeto_id = s.projeto_id AND st.semana = s.semana
  LEFT JOIN custo_acumulado  ca ON ca.projeto_id = s.projeto_id AND ca.semana = s.semana
  LEFT JOIN horas_semana     h  ON h.projeto_id  = s.projeto_id AND h.semana  = s.semana
)
SELECT
  projeto_id,
  semana,
  orcamento,
  pct_concluido,
  farol_do_gerente,
  round(pv, 2)                                AS pv,
  round(ev, 2)                                AS ev,
  round(custo_semana, 2)                      AS custo_semana,
  round(ac, 2)                                AS ac,
  round(try_divide(ev, pv), 4)                AS spi,
  round(try_divide(ev, ac), 4)                AS cpi,
  round(try_divide(orcamento, try_divide(ev, ac)), 2) AS eac,
  horas_disponiveis,
  horas_apontadas,
  horas_ociosas
FROM valores;
