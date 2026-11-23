-- KPIs da tela "Projetos em risco": uma linha só, lida da fotografia de hoje
-- (gold.projeto_situacao_atual, "hoje" = 16/10/2026). O score do modelo NÃO
-- entra aqui: ele pode não existir, e uma tabela ausente quebraria o build.
SELECT
  count_if(status = 'em_andamento')                                        AS em_andamento,
  count_if(status = 'em_andamento' AND situacao IN ('atenção', 'crítico')) AS em_risco,
  count_if(status = 'em_andamento' AND situacao = 'crítico')               AS criticos,
  count_if(status = 'em_andamento' AND situacao = 'atenção')               AS em_atencao,
  count_if(status = 'em_andamento' AND melancia)                           AS melancias,
  -- estouro previsto só existe quando positivo (EAC − orçamento)
  coalesce(sum(CASE WHEN status = 'em_andamento' THEN estouro_previsto END), 0) AS estouro_previsto,
  -- carteira = valor de contrato dos projetos em andamento (e o total dos 60)
  sum(CASE WHEN status = 'em_andamento' THEN valor_contrato END)           AS carteira_em_andamento,
  sum(valor_contrato)                                                       AS carteira_total
FROM farol_projeto.gold.projeto_situacao_atual
