import { Badge, Button, GenieChatMessageList, useGenieChat } from '@databricks/appkit-ui/react';
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

// As 4 perguntas do dono: viram botões que mandam a pergunta direto para o Genie.
const PERGUNTAS_DO_DONO = [
  'Quais projetos estão atrasados, e de quais clientes?',
  'Quanto esse atraso vai me custar?',
  'Tenho gente parada enquanto outro projeto pede gente?',
  'O que vai dar errado no próximo mês?',
];

const ALTURA_MAXIMA_CAIXA = 96; // px: a caixa cresce até ~4 linhas e depois rola

// O <GenieChat> pronto só deixa trocar o placeholder: "Send", "New conversation" e a
// mensagem inicial são fixos em inglês. Por isso a tela monta o chat com as peças que o
// AppKit exporta (useGenieChat + GenieChatMessageList) e uma caixa de texto própria.
export function PerguntarPage() {
  const [email, setEmail] = useState<string | null>(null);
  const [texto, setTexto] = useState('');
  const caixaRef = useRef<HTMLTextAreaElement>(null);

  const { messages, status, error, sendMessage, reset, hasPreviousPage, fetchPreviousPage } = useGenieChat({
    alias: 'default',
  });
  const ocupado = status === 'streaming' || status === 'loading-history';

  useEffect(() => {
    fetch('/api/whoami')
      .then((r) => (r.ok ? (r.json() as Promise<{ email: string | null }>) : null))
      .then((me) => setEmail(me?.email ?? null))
      .catch(() => setEmail(null));
  }, []);

  function ajustarAltura() {
    const caixa = caixaRef.current;
    if (!caixa) return;
    caixa.style.height = 'auto';
    caixa.style.height = `${Math.min(caixa.scrollHeight, ALTURA_MAXIMA_CAIXA)}px`;
    caixa.style.overflowY = caixa.scrollHeight > ALTURA_MAXIMA_CAIXA ? 'auto' : 'hidden';
  }

  function enviar(pergunta: string) {
    const limpa = pergunta.trim();
    if (!limpa || ocupado) return;
    sendMessage(limpa);
    setTexto('');
    if (caixaRef.current) caixaRef.current.style.height = 'auto';
  }

  function aoTeclar(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter envia, Shift+Enter quebra a linha
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviar(texto);
    }
  }

  return (
    <div className="space-y-4 w-full max-w-5xl mx-auto">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Perguntar</h2>
          <p className="text-sm text-muted-foreground">
            O agente Genie “Farol · Diretoria” responde em português sobre a carteira, com dados de 16/10/2026.
          </p>
        </div>
        <Badge variant="secondary">{email ?? 'usuário conectado'}</Badge>
      </div>

      <div className="flex flex-col h-[480px] border rounded-lg overflow-hidden">
        {messages.length > 0 && (
          <div className="shrink-0 flex justify-end px-4 pt-3 pb-1">
            <Button variant="ghost" size="sm" onClick={reset} className="text-xs text-muted-foreground">
              Nova conversa
            </Button>
          </div>
        )}

        {messages.length > 0 || status === 'loading-history' ? (
          <GenieChatMessageList
            messages={messages}
            status={status}
            hasPreviousPage={hasPreviousPage}
            onFetchPreviousPage={fetchPreviousPage}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center px-6 text-center text-sm text-muted-foreground">
            Comece uma conversa: clique numa das perguntas do dono abaixo ou escreva a sua.
          </div>
        )}

        {error && (
          <div className="shrink-0 px-4 py-2 text-sm text-destructive bg-destructive/10 border-t">{error}</div>
        )}

        <div className="shrink-0 border-t p-3 space-y-2">
          <div className="flex flex-wrap gap-2">
            {PERGUNTAS_DO_DONO.map((p) => (
              <Button key={p} variant="outline" size="sm" disabled={ocupado} onClick={() => enviar(p)} className="h-auto py-1 text-xs whitespace-normal text-left">
                {p}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <textarea
              ref={caixaRef}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={aoTeclar}
              onInput={ajustarAltura}
              placeholder="Faça uma pergunta sobre os projetos..."
              disabled={ocupado}
              rows={1}
              aria-label="Pergunta para o Genie"
              className="flex-1 resize-none overflow-hidden rounded-md border border-input bg-background px-3 py-1.5 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
            <Button onClick={() => enviar(texto)} disabled={ocupado || !texto.trim()} className="self-end">
              Enviar
            </Button>
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Resposta gerada por IA a partir da gold: confira o SQL de cada resposta antes de decidir. As consultas rodam
        com as SUAS permissões no Unity Catalog (em seu nome), não com as do app.
      </p>
    </div>
  );
}
