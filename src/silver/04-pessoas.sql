-- silver.colaboradores e silver.apontamentos: quem trabalha e onde apontou as horas.


-- sujeira 16: COL0102, COL0257 e COL0433 aparecem duas vezes (a cópia com nome e papel em CAIXA ALTA).
-- Fica o cadastro com o papel em minúsculas.
CREATE OR REFRESH MATERIALIZED VIEW colaboradores
COMMENT 'As 520 pessoas da Vértice (uma linha por colaborador): nome, papel (dev, qa, sre, tech_lead...), senioridade, custo por hora e datas de admissão e desligamento. Os 3 cadastros duplicados da bronze foram resolvidos.'
AS
WITH numerado AS (
  SELECT
    *,
    row_number() OVER (
      PARTITION BY colaborador_id
      ORDER BY CASE WHEN papel = lower(papel) THEN 0 ELSE 1 END
    ) AS ordem
  FROM farol_projeto.bronze.colaboradores
)
SELECT
  colaborador_id,
  nome,
  papel,
  senioridade,
  CAST(custo_hora AS DECIMAL(10, 2))                 AS custo_hora,
  to_date(data_admissao)                             AS data_admissao,
  to_date(nullif(trim(data_desligamento), ''))       AS data_desligamento
FROM numerado
WHERE ordem = 1;


-- O timesheet semanal.
CREATE OR REFRESH MATERIALIZED VIEW apontamentos
COMMENT 'Timesheet semanal (uma linha por pessoa, projeto e semana): horas disponíveis e horas apontadas no projeto. semana é a sexta da semana, para casar com o status semanal. Base da utilização das pessoas.'
AS
SELECT
  colaborador_id,
  projeto_id,
  to_date(semana_inicio)                             AS semana_inicio,
  date_add(to_date(semana_inicio), 4)                AS semana,       -- a sexta
  CAST(horas_disponiveis AS DOUBLE)                  AS horas_disponiveis,
  CAST(horas_apontadas   AS DOUBLE)                  AS horas_apontadas
FROM farol_projeto.bronze.apontamentos;
