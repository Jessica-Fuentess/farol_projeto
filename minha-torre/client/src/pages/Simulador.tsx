import {
  Alert,
  AlertDescription,
  AlertTitle,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  useAnalyticsQuery,
} from '@databricks/appkit-ui/react';
import { useState } from 'react';
import {
  indice,
  nomeCausa,
  nomeCausaFrase,
  nomePapel,
  nomeSenioridade,
  num,
  numero1,
  numeroInteiro,
  percentual,
  reaisCompacto,
  reaisInteiro,
} from '../lib/formatar';
import { BadgeSituacao, FONTE } from './ProjetosRisco';

const SEM_PARAMETROS = {};
const SEMANAS_NO_MES = 4;
const ONBOARDING_PADRAO = 40;

function Linha({ rotulo, valor, destaque }: { rotulo: string; valor: string; destaque?: 'bom' | 'ruim' }) {
  const cor = destaque === 'bom' ? 'text-success' : destaque === 'ruim' ? 'text-destructive' : 'text-foreground';
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 border-b last:border-b-0">
      <span className="text-sm text-muted-foreground">{rotulo}</span>
      <span className={`text-lg font-semibold tabular-nums ${cor}`}>{valor}</span>
    </div>
  );
}

export function SimuladorPage() {
  const pessoas = useAnalyticsQuery('pessoas_ociosas', SEM_PARAMETROS);
  const projetos = useAnalyticsQuery('projetos_risco', SEM_PARAMETROS);

  const [pessoaId, setPessoaId] = useState<string>('');
  const [projetoId, setProjetoId] = useState<string>('');
  const [onboardingTexto, setOnboardingTexto] = useState<string>(String(ONBOARDING_PADRAO));

  const listaPessoas = pessoas.data ?? [];
  // A chave da pessoa inclui o projeto de origem: a mesma pessoa pode estar ociosa em dois projetos.
  const chavePessoa = (p: (typeof listaPessoas)[number]) => `${p.colaborador_id}|${p.projeto_id}`;
  const pessoa = listaPessoas.find((p) => chavePessoa(p) === pessoaId) ?? listaPessoas[0];
  const ehSre = pessoa?.papel.toLowerCase() === 'sre';

  // Destino: só projeto em atenção ou crítico. Para SRE, quem mais sofre com falta de SRE vem primeiro.
  const destinos = (projetos.data ?? [])
    .filter((p) => p.situacao === 'atenção' || p.situacao === 'crítico')
    .filter((p) => p.projeto !== pessoa?.projeto_id)
    .slice()
    .sort((a, b) => (ehSre ? num(b.dias_falta_sre) - num(a.dias_falta_sre) : 0));
  const destino = destinos.find((p) => p.projeto === projetoId) ?? destinos[0];

  // A causa que esta pessoa ajuda a destravar: SRE → falta_sre; outros papéis → rotatividade (gente que saiu).
  const causa = ehSre ? 'falta_sre' : 'rotatividade';
  const diasCausa90 = destino ? num(ehSre ? destino.dias_falta_sre : destino.dias_rotatividade) : 0;

  const horasOnboarding = Math.max(0, num(onboardingTexto));
  const horasMes = pessoa ? num(pessoa.horas_ociosas_semana) * SEMANAS_NO_MES : 0;
  const ociosidadeEvitada = pessoa ? num(pessoa.custo_ocioso_semana) * SEMANAS_NO_MES : 0;
  const diasRecuperados = (diasCausa90 / 90) * 30;
  const mobilizacao = pessoa ? horasOnboarding * num(pessoa.custo_hora) : 0;
  const saldo = ociosidadeEvitada - mobilizacao;

  const carregando = pessoas.loading || projetos.loading;
  const erro = pessoas.error ?? projetos.error;

  return (
    <div className="space-y-6 w-full max-w-5xl mx-auto">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Simulador de realocação</h2>
        <p className="text-sm text-muted-foreground">
          Tenho gente parada enquanto outro projeto pede gente? Mova uma pessoa ociosa para um projeto em risco e veja
          a conta de um mês.
        </p>
      </div>

      {erro && (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível ler a gold</AlertTitle>
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      )}

      {carregando && <Skeleton className="h-64 w-full" />}

      {!carregando && !erro && listaPessoas.length === 0 && (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Ninguém abaixo de 20% de utilização</EmptyTitle>
            <EmptyDescription>Nas últimas 12 semanas todo mundo apontou pelo menos 20% das horas disponíveis.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}

      {!carregando && pessoa && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Quem e para onde</CardTitle>
              <CardDescription>Pessoas com utilização &lt; 20% nas últimas 12 semanas · {FONTE}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="pessoa">Pessoa ociosa</Label>
                <Select
                  value={chavePessoa(pessoa)}
                  onValueChange={(v) => {
                    setPessoaId(v);
                    setProjetoId('');
                  }}
                >
                  <SelectTrigger id="pessoa" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {listaPessoas.map((p) => (
                      <SelectItem key={chavePessoa(p)} value={chavePessoa(p)}>
                        {p.colaborador_id} · {p.nome} · {nomePapel(p.papel)} {nomeSenioridade(p.senioridade)} · {p.projeto_id} ({percentual(p.utilizacao)})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Hoje em {pessoa.projeto_id}, com {percentual(pessoa.utilizacao)} de uso · {numero1(pessoa.horas_ociosas_semana)}{' '}
                  h paradas por semana · custo/hora {reaisInteiro(pessoa.custo_hora)}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="destino">Projeto destino (atenção ou crítico)</Label>
                {destino ? (
                  <Select value={destino.projeto} onValueChange={setProjetoId}>
                    <SelectTrigger id="destino" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {destinos.map((p) => (
                        <SelectItem key={p.projeto} value={p.projeto}>
                          {p.projeto} · {p.cliente} · {p.situacao}
                          {ehSre && num(p.dias_falta_sre) > 0 ? ` · ${numeroInteiro(p.dias_falta_sre)} dias de falta de SRE` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-sm text-muted-foreground">Nenhum projeto em atenção ou crítico.</p>
                )}
                {destino && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <BadgeSituacao situacao={destino.situacao} />
                    <span>
                      SPI {indice(destino.spi)} · CPI {indice(destino.cpi)} · causa principal: {nomeCausa(destino.causa_principal)}
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="onboarding">Horas de onboarding</Label>
                <Input
                  id="onboarding"
                  type="number"
                  min={0}
                  step={8}
                  value={onboardingTexto}
                  onChange={(e) => setOnboardingTexto(e.target.value)}
                  className="w-32"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                {pessoa.colaborador_id} → {destino?.projeto ?? '—'}: um mês
              </CardTitle>
              <CardDescription>Estimativa com as médias das últimas 12 semanas · {SEMANAS_NO_MES} semanas no mês</CardDescription>
            </CardHeader>
            <CardContent>
              <Linha rotulo="Horas no mês" valor={`${numeroInteiro(horasMes)} h`} />
              <Linha rotulo="Ociosidade que deixa de ser paga" valor={reaisCompacto(ociosidadeEvitada)} destaque="bom" />
              <Linha
                rotulo={`Dias de cronograma recuperados (${nomeCausaFrase(causa)})`}
                valor={`${numero1(diasRecuperados)} dias`}
                destaque={diasRecuperados > 0 ? 'bom' : undefined}
              />
              <Linha rotulo="Mobilização (onboarding)" valor={`− ${reaisCompacto(mobilizacao)}`} destaque="ruim" />
              <Linha rotulo="Saldo do mês" valor={reaisCompacto(saldo)} destaque={saldo >= 0 ? 'bom' : 'ruim'} />

              <details className="mt-4 text-sm text-muted-foreground">
                <summary className="cursor-pointer text-foreground">Como a conta é feita</summary>
                <ul className="mt-2 space-y-1 list-disc pl-5">
                  <li>
                    <b>Horas no mês</b> = horas paradas por semana × {SEMANAS_NO_MES} = {numero1(pessoa.horas_ociosas_semana)} ×{' '}
                    {SEMANAS_NO_MES} = {numeroInteiro(horasMes)} h. É o tempo que a pessoa já recebe sem ter o que apontar.
                  </li>
                  <li>
                    <b>Ociosidade evitada</b> = custo ocioso por semana × {SEMANAS_NO_MES} = {reaisInteiro(pessoa.custo_ocioso_semana)} ×{' '}
                    {SEMANAS_NO_MES} = {reaisInteiro(ociosidadeEvitada)}. O salário já é pago: a realocação transforma esse custo em
                    trabalho.
                  </li>
                  <li>
                    <b>Dias recuperados</b> = dias de impacto declarados no status por {nomeCausaFrase(causa)} nos últimos 90
                    dias ÷ 90 × 30 = {numeroInteiro(diasCausa90)} ÷ 90 × 30 = {numero1(diasRecuperados)} dias. Para SRE vale a causa
                    falta de SRE; para os demais papéis, rotatividade.
                  </li>
                  <li>
                    <b>Mobilização</b> = horas de onboarding × custo/hora = {numeroInteiro(horasOnboarding)} ×{' '}
                    {reaisInteiro(pessoa.custo_hora)} = {reaisInteiro(mobilizacao)}.
                  </li>
                  <li>
                    <b>Saldo</b> = ociosidade evitada − mobilização = {reaisInteiro(saldo)}. Os dias recuperados ficam fora do
                    saldo em R$: são o ganho de prazo, somado por cima.
                  </li>
                </ul>
              </details>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
