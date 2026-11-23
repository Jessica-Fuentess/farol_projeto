import { analytics, createApp, genie, getExecutionContext, getWarehouseId, server } from '@databricks/appkit';
import { z } from 'zod';

// O score do modelo (gold.score_estouro_30d) vem de um modelo de ML opcional e PODE NÃO EXISTIR.
// Por isso ele não está em config/queries: uma query com tabela inexistente quebra o
// typegen do build. Esta rota pergunta ao warehouse se a tabela existe e responde
// { disponivel: false, linhas: [] } quando não existe. A tela mostra "—".
const TABELA_SCORE = 'farol_projeto.gold.score_estouro_30d';

// O warehouse devolve todo número como texto: z.coerce.number() converte.
const linhaScore = z.object({
  projeto_id: z.string(),
  data_referencia: z.string().nullable(),
  prob_estouro_30d: z.coerce.number(),
  ranking: z.coerce.number().nullable(),
  faixa_risco: z.string().nullable(),
  principais_fatores: z.string().nullable(),
});

export type LinhaScore = z.infer<typeof linhaScore>;

async function lerScore(): Promise<{ disponivel: boolean; linhas: LinhaScore[]; motivo?: string }> {
  const { client } = getExecutionContext();
  const warehouse_id = await getWarehouseId();

  const existe = await client.statementExecution.executeStatement({
    warehouse_id,
    wait_timeout: '30s',
    statement: `SELECT count(*) FROM farol_projeto.information_schema.tables
                WHERE table_schema = 'gold' AND table_name = 'score_estouro_30d'`,
  });
  if (existe.status?.state !== 'SUCCEEDED') {
    return { disponivel: false, linhas: [], motivo: existe.status?.error?.message ?? 'consulta não terminou' };
  }
  if (Number(existe.result?.data_array?.[0]?.[0] ?? 0) === 0) {
    return { disponivel: false, linhas: [], motivo: `${TABELA_SCORE} ainda não existe` };
  }

  const resposta = await client.statementExecution.executeStatement({
    warehouse_id,
    wait_timeout: '30s',
    statement: `SELECT projeto_id, CAST(data_referencia AS STRING), prob_estouro_30d, ranking,
                       faixa_risco, principais_fatores
                FROM ${TABELA_SCORE}`,
  });
  if (resposta.status?.state !== 'SUCCEEDED') {
    return { disponivel: false, linhas: [], motivo: resposta.status?.error?.message ?? 'consulta não terminou' };
  }

  const colunas = ['projeto_id', 'data_referencia', 'prob_estouro_30d', 'ranking', 'faixa_risco', 'principais_fatores'];
  const linhas = (resposta.result?.data_array ?? []).map((valores) =>
    linhaScore.parse(Object.fromEntries(colunas.map((c, i) => [c, valores[i] ?? null]))),
  );
  return { disponivel: true, linhas };
}

// Sem cache no createApp: cada visita lê a gold como ela está.
// genie() lê DATABRICKS_GENIE_SPACE_ID (app.yaml → recurso genie-space) e registra o alias "default".
createApp({
  plugins: [analytics(), genie(), server()],
  onPluginsReady(appkit) {
    appkit.server.extend((app) => {
      // Quem está perguntando: o proxy do Databricks Apps manda o e-mail no header.
      app.get('/api/whoami', (req, res) => {
        res.json({ email: req.header('x-forwarded-email') ?? null });
      });

      app.get('/api/score-estouro', async (_req, res) => {
        try {
          res.json(await lerScore());
        } catch (erro) {
          // Nunca derruba a tela: sem score, a coluna P(estouro) mostra "—".
          console.error('score-estouro:', erro);
          res.json({ disponivel: false, linhas: [], motivo: 'erro ao ler o score' });
        }
      });
    });
  },
}).catch(console.error);
