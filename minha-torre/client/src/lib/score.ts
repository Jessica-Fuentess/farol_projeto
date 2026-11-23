import { useEffect, useState } from 'react';
import { z } from 'zod';

// O score do modelo vem da rota do servidor (não de config/queries), porque a
// tabela gold.score_estouro_30d pode não existir. Sem score, a tela mostra "—".
const respostaScore = z.object({
  disponivel: z.boolean(),
  motivo: z.string().optional(),
  linhas: z.array(
    z.object({
      projeto_id: z.string(),
      data_referencia: z.string().nullable(),
      prob_estouro_30d: z.coerce.number(),
      ranking: z.coerce.number().nullable(),
      faixa_risco: z.string().nullable(),
      principais_fatores: z.string().nullable(),
    }),
  ),
});

export type RespostaScore = z.infer<typeof respostaScore>;
export type EstadoScore = { carregando: boolean; score: RespostaScore };

const SEM_SCORE: RespostaScore = { disponivel: false, linhas: [] };

export function useScoreEstouro(): EstadoScore {
  const [estado, setEstado] = useState<EstadoScore>({ carregando: true, score: SEM_SCORE });

  useEffect(() => {
    let ativo = true;
    fetch('/api/score-estouro')
      .then((r) => r.json())
      .then((json: unknown) => {
        const lido = respostaScore.safeParse(json);
        if (ativo) setEstado({ carregando: false, score: lido.success ? lido.data : SEM_SCORE });
      })
      .catch(() => {
        if (ativo) setEstado({ carregando: false, score: SEM_SCORE });
      });
    return () => {
      ativo = false;
    };
  }, []);

  return estado;
}
