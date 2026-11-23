// Formatação em português. O warehouse devolve número como texto: tudo passa por Number().

const decimal1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const decimal2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const inteiro = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
const reais = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

export function num(valor: unknown): number {
  const n = Number(valor);
  return Number.isFinite(n) ? n : 0;
}

/** R$ 6,5 mi · R$ 30,1 mil · R$ 850 */
export function reaisCompacto(valor: unknown): string {
  const v = num(valor);
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `R$ ${decimal1.format(v / 1_000_000)} mi`;
  if (abs >= 1_000) return `R$ ${decimal1.format(v / 1_000)} mil`;
  return reais.format(v);
}

export function reaisInteiro(valor: unknown): string {
  return reais.format(num(valor));
}

/** Índices (SPI, CPI) com 2 casas: 0,92 */
export function indice(valor: unknown): string {
  return decimal2.format(num(valor));
}

export function numeroInteiro(valor: unknown): string {
  return inteiro.format(num(valor));
}

export function numero1(valor: unknown): string {
  return decimal1.format(num(valor));
}

/** 0,0577 → 5,8% */
export function percentual(valor: unknown): string {
  return `${decimal1.format(num(valor) * 100)}%`;
}

const NOMES_CAUSA: Record<string, string> = {
  change_freeze: 'Change freeze',
  falta_sre: 'Falta de SRE',
  dependencia_fornecedor: 'Dependência de fornecedor',
  rotatividade: 'Rotatividade',
  mudanca_escopo: 'Mudança de escopo',
  bug_retrabalho: 'Bug / retrabalho',
  aprovacao_cliente: 'Aprovação do cliente',
};

export function nomeCausa(causa: string | null | undefined): string {
  if (!causa) return '—';
  return NOMES_CAUSA[causa] ?? causa;
}

/** "falta de SRE", "aprovação do cliente": a causa no meio de uma frase. */
export function nomeCausaFrase(causa: string | null | undefined): string {
  const nome = nomeCausa(causa);
  return nome.charAt(0).toLowerCase() + nome.slice(1);
}

/**
 * O warehouse devolve booleano como texto ("true"/"false"). "false" é uma
 * string não vazia e vale true em JavaScript: por isso a comparação explícita.
 */
export function verdadeiro(valor: unknown): boolean {
  return valor === true || String(valor).toLowerCase() === 'true';
}

const NOMES_PAPEL: Record<string, string> = {
  sre: 'SRE',
  qa: 'QA',
  agilista: 'Agilista',
  arquiteto: 'Arquiteto',
  designer_ux: 'Designer UX',
  dev_backend: 'Dev back-end',
  dev_frontend: 'Dev front-end',
  dev_mobile: 'Dev mobile',
  engenheiro_dados: 'Engenheiro de dados',
  gestor_engenharia: 'Gestor de engenharia',
  product_owner: 'Product owner',
  tech_lead: 'Tech lead',
  scrum_master: 'Scrum master',
  gerente_projeto: 'Gerente de projeto',
};

export function nomePapel(papel: string | null | undefined): string {
  if (!papel) return '—';
  const p = papel.toLowerCase();
  if (NOMES_PAPEL[p]) return NOMES_PAPEL[p];
  const texto = p.replace(/_/g, ' ');
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

const NOMES_SENIORIDADE: Record<string, string> = {
  junior: 'Júnior',
  pleno: 'Pleno',
  senior: 'Sênior',
  especialista: 'Especialista',
};

export function nomeSenioridade(senioridade: string | null | undefined): string {
  if (!senioridade) return '—';
  return NOMES_SENIORIDADE[senioridade.toLowerCase()] ?? senioridade;
}
