-- Projetos em andamento, do pior para o melhor (crítico → atenção → ok; dentro
-- de cada situação, o menor SPI primeiro). A causa vem do status semanal
-- classificado pela IA (gold.status_estruturado) nos últimos 90 dias.
WITH status_90d AS (
  SELECT projeto_id, causa_bloqueio, dias_impacto
  FROM farol_projeto.gold.status_estruturado
  WHERE data_status > DATE'2026-10-16' - INTERVAL 90 DAYS
),
-- quantas vezes cada causa apareceu no projeto ("sem bloqueio" e "não
-- reportado" não são causa)
contagem_causa AS (
  SELECT projeto_id, causa_bloqueio, count(*) AS vezes
  FROM status_90d
  WHERE causa_bloqueio NOT IN ('sem_bloqueio', 'nao_reportado')
  GROUP BY projeto_id, causa_bloqueio
),
-- a janela fica num CTE próprio: a causa mais frequente de cada projeto
causa_ranqueada AS (
  SELECT projeto_id, causa_bloqueio, vezes,
         row_number() OVER (PARTITION BY projeto_id ORDER BY vezes DESC, causa_bloqueio) AS posicao
  FROM contagem_causa
),
dias_por_causa AS (
  SELECT projeto_id,
         coalesce(sum(CASE WHEN causa_bloqueio = 'falta_sre'    THEN dias_impacto END), 0) AS dias_falta_sre,
         coalesce(sum(CASE WHEN causa_bloqueio = 'rotatividade' THEN dias_impacto END), 0) AS dias_rotatividade,
         count_if(causa_bloqueio = 'falta_sre')                                            AS semanas_falta_sre
  FROM status_90d
  GROUP BY projeto_id
)
SELECT
  p.projeto,
  p.nome,
  p.cliente,
  p.segmento,
  p.gerente_projeto,
  p.situacao,
  round(p.spi, 2)                       AS spi,
  round(p.cpi, 2)                       AS cpi,
  coalesce(p.estouro_previsto, 0)       AS estouro_previsto,
  round(p.atraso_projetado_dias, 0)     AS atraso_projetado_dias,
  p.farol_do_gerente,
  p.farol_calculado,
  p.melancia,
  c.causa_bloqueio                      AS causa_principal,
  c.vezes                               AS vezes_causa_principal,
  coalesce(d.dias_falta_sre, 0)         AS dias_falta_sre,
  coalesce(d.semanas_falta_sre, 0)      AS semanas_falta_sre,
  coalesce(d.dias_rotatividade, 0)      AS dias_rotatividade
FROM farol_projeto.gold.projeto_situacao_atual p
LEFT JOIN causa_ranqueada c ON c.projeto_id = p.projeto AND c.posicao = 1
LEFT JOIN dias_por_causa  d ON d.projeto_id = p.projeto
WHERE p.status = 'em_andamento'
ORDER BY CASE p.situacao WHEN 'crítico' THEN 1 WHEN 'atenção' THEN 2 ELSE 3 END,
         p.spi,
         p.projeto
