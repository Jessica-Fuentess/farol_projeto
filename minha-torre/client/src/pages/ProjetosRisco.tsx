import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  useAnalyticsQuery,
} from '@databricks/appkit-ui/react';
import type { ReactNode } from 'react';
import { indice, nomeCausa, num, numeroInteiro, reaisCompacto, verdadeiro } from '../lib/formatar';

// As queries não têm parâmetro: um objeto fixo evita refazer a consulta a cada render.
const SEM_PARAMETROS = {};

export const FONTE = 'gold · fotografia de 16/10/2026';

export function BadgeSituacao({ situacao }: { situacao: string }) {
  if (situacao === 'crítico') {
    return <Badge className="bg-destructive text-destructive-foreground border-transparent">crítico</Badge>;
  }
  if (situacao === 'atenção') {
    return <Badge className="bg-warning text-warning-foreground border-transparent">atenção</Badge>;
  }
  return <Badge variant="outline">{situacao}</Badge>;
}

function Kpi({
  titulo,
  valor,
  detalhe,
  carregando,
  tom,
}: {
  titulo: string;
  valor: ReactNode;
  detalhe: ReactNode;
  carregando: boolean;
  tom?: 'destructive' | 'warning';
}) {
  const corValor = tom === 'destructive' ? 'text-destructive' : 'text-foreground';
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{titulo}</CardDescription>
        <CardTitle className={`text-3xl tabular-nums ${corValor}`}>
          {carregando ? <Skeleton className="h-9 w-24" /> : valor}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{detalhe}</CardContent>
    </Card>
  );
}

function Erro({ mensagem }: { mensagem: string }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Não foi possível ler a gold</AlertTitle>
      <AlertDescription>{mensagem}</AlertDescription>
    </Alert>
  );
}

export function ProjetosRiscoPage() {
  const kpis = useAnalyticsQuery('kpis', SEM_PARAMETROS);
  const projetos = useAnalyticsQuery('projetos_risco', SEM_PARAMETROS);

  const k = kpis.data?.[0];

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Projetos em risco</h2>
        <p className="text-sm text-muted-foreground">
          {k
            ? `${numeroInteiro(k.em_risco)} dos ${numeroInteiro(k.em_andamento)} projetos em andamento estão em atenção ou críticos (SPI ou CPI < 0,90).`
            : 'Quais projetos estão atrasados, de quais clientes, e quanto isso vai custar.'}
        </p>
      </div>

      {kpis.error && <Erro mensagem={kpis.error} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi
          titulo="Em risco"
          carregando={kpis.loading}
          tom="destructive"
          valor={k ? `${numeroInteiro(k.em_risco)} de ${numeroInteiro(k.em_andamento)}` : '—'}
          detalhe={
            k
              ? `${numeroInteiro(k.criticos)} críticos · ${numeroInteiro(k.em_atencao)} em atenção`
              : FONTE
          }
        />
        <Kpi
          titulo="Estouro previsto"
          carregando={kpis.loading}
          tom="destructive"
          valor={k ? reaisCompacto(k.estouro_previsto) : '—'}
          detalhe="Σ (EAC − orçamento) dos projetos em andamento"
        />
        <Kpi
          titulo="Carteira em andamento"
          carregando={kpis.loading}
          valor={k ? reaisCompacto(k.carteira_em_andamento) : '—'}
          detalhe={k ? `valor de contrato · ${reaisCompacto(k.carteira_total)} na carteira toda` : FONTE}
        />
        <Kpi
          titulo="🍉 Melancias"
          carregando={kpis.loading}
          tom="destructive"
          valor={k ? numeroInteiro(k.melancias) : '—'}
          detalhe="farol do gerente verde, SPI < 0,90"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Projetos em andamento, do pior para o melhor</CardTitle>
          <CardDescription>
            Situação pelo SPI/CPI calculado das tarefas · causa mais frequente no status semanal dos últimos 90 dias
            (classificada pela IA) · {FONTE}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {projetos.error && <Erro mensagem={projetos.error} />}
          {projetos.loading && (
            <div className="space-y-2">
              {Array.from({ length: 8 }, (_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          )}
          {projetos.data && projetos.data.length === 0 && (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>Nenhum projeto em andamento</EmptyTitle>
                <EmptyDescription>Rode o job farol_projeto_job para recarregar a gold.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {projetos.data && projetos.data.length > 0 && (
            <div className="overflow-x-auto">
              <Table className="text-sm [&_td]:whitespace-normal [&_th]:whitespace-normal [&_td]:px-2 [&_th]:px-2">
                <TableHeader>
                  <TableRow>
                    <TableHead>Projeto</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Situação</TableHead>
                    <TableHead className="text-right">SPI</TableHead>
                    <TableHead className="text-right">CPI</TableHead>
                    <TableHead className="text-right">Estouro previsto</TableHead>
                    <TableHead className="text-right">Atraso projetado</TableHead>
                    <TableHead>Farol gerente × calculado</TableHead>
                    <TableHead>Causa principal (90 dias)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {projetos.data.map((p) => {
                    const melancia = verdadeiro(p.melancia);
                    const spi = num(p.spi);
                    const cpi = num(p.cpi);
                    return (
                      <TableRow
                        key={p.projeto}
                        className={melancia ? 'bg-destructive/10 hover:bg-destructive/15' : undefined}
                      >
                        <TableCell>
                          <div className="font-medium">{p.projeto}</div>
                          <div className="text-xs text-muted-foreground max-w-52 truncate" title={p.nome}>
                            {p.nome}
                          </div>
                        </TableCell>
                        <TableCell className="min-w-28">{p.cliente}</TableCell>
                        <TableCell>
                          <BadgeSituacao situacao={p.situacao} />
                        </TableCell>
                        <TableCell className={`text-right tabular-nums ${spi < 0.9 ? 'text-destructive font-medium' : ''}`}>
                          {indice(spi)}
                        </TableCell>
                        <TableCell className={`text-right tabular-nums ${cpi < 0.9 ? 'text-destructive font-medium' : ''}`}>
                          {indice(cpi)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums !whitespace-nowrap">
                          {num(p.estouro_previsto) > 0 ? reaisCompacto(p.estouro_previsto) : '—'}
                        </TableCell>
                        <TableCell className="text-right tabular-nums !whitespace-nowrap">
                          {num(p.atraso_projetado_dias) > 0 ? `${numeroInteiro(p.atraso_projetado_dias)} dias` : '—'}
                        </TableCell>
                        <TableCell className="!whitespace-nowrap">
                          {melancia && (
                            <span title="Melancia: verde por fora, vermelho por dentro (farol do gerente verde e SPI < 0,90)">
                              🍉{' '}
                            </span>
                          )}
                          {p.farol_do_gerente} <span className="text-muted-foreground">×</span> {p.farol_calculado}
                        </TableCell>
                        <TableCell className="min-w-36">
                          {nomeCausa(p.causa_principal)}
                          {num(p.dias_falta_sre) > 0 && (
                            <div className="text-xs text-muted-foreground">
                              falta de SRE: {numeroInteiro(p.dias_falta_sre)} dias de impacto
                            </div>
                          )}
                          {num(p.dias_rotatividade) > 0 && (
                            <div className="text-xs text-muted-foreground">
                              rotatividade: {numeroInteiro(p.dias_rotatividade)} dias de impacto
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
