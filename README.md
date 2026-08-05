# Hellena Capturas

Ferramenta pessoal de captura de pensamentos por voz — no celular e no
computador — com processamento automático e chegada final no seu vault do
Obsidian.

Não é um produto, não é um SaaS. São dois scripts que rodam no seu computador.

Leia primeiro **[ARCHITECTURE.md](ARCHITECTURE.md)** (pipeline mobile) e
**[docs/desktop-capture.md](docs/desktop-capture.md)** (captura no desktop
com atalho de teclado) para o diagnóstico completo e as decisões de
arquitetura. Este README é só o "como instalar e usar".

## Dois fluxos

**Mobile** — aperta o Botão de Ação no iPhone, fala, solta:

```
iPhone (Atalho + Botão de Ação)
  → Google Drive (transporte)
    → Windows: Whisper local transcreve (áudio nunca sai da máquina)
      → Claude API estrutura o texto (só texto, nunca áudio)
        → Markdown escrito no vault do Obsidian
```

**Desktop** — substitui o Superwhisper: atalho de teclado global com 4
modos (ideia, reunião, terapia, aula), gravando microfone e, quando o modo
pede, também o áudio do sistema (para separar "você" de "outra pessoa" sem
diarização) — o modo aula grava só o áudio do sistema, sem microfone:

```
Ctrl+Alt+I / Ctrl+Alt+R / Ctrl+Alt+T / Ctrl+Alt+A
  → grava mic (+ áudio do sistema se o modo pedir; aula só grava sistema)
    → Whisper local transcreve cada trilha
      → Claude API estrutura conforme o modo (ideia / reunião / terapia / aula)
        → Markdown escrito no vault do Obsidian
```

Detalhes de privacidade — o que sai da sua máquina e para onde — estão na
seção 12 de [ARCHITECTURE.md](ARCHITECTURE.md) (vale para os dois fluxos: só
texto trafega para a Claude API, áudio nunca sai da máquina).

## Instalação

1. **No iPhone:** siga [docs/ios-shortcut-setup.md](docs/ios-shortcut-setup.md)
   para criar o Atalho de captura.
2. **No Windows:** siga [docs/windows-setup.md](docs/windows-setup.md) para
   instalar o pipeline mobile (seções 1–5), agendar sua execução automática,
   e opcionalmente a captura no desktop (seção 6).

## Uso do dia a dia

**Mobile:** aperte o Botão de Ação (ou o widget na tela bloqueada), fale,
aperte de novo para parar, volte ao que estava fazendo. A nota aparece no
Obsidian em até ~15 minutos, sozinha.

**Desktop:** aperte `Ctrl+Alt+I`/`R`/`T`/`A` conforme o modo, fale (exceto no
modo aula), aperte de novo para parar — ou `Ctrl+Alt+P` pra parar qualquer
um sem precisar lembrar qual você usou. Uma notificação confirma quando a
nota estiver pronta. Ícones equivalentes ficam disponíveis na Área de
Trabalho depois de rodar `scripts\windows\criar-atalhos-desktop.ps1`.

Se algo falhar, em qualquer um dos dois fluxos, você vai ver uma nota
`_Erros de captura.md` no vault explicando o que houve — a captura nunca
falha em silêncio.

## Comandos

```powershell
# Pipeline mobile (roda em lote, disparado pelo Task Scheduler)
python -m voice_capture.run                    # processa o que estiver pendente
python -m voice_capture.run --status            # mostra o estado de cada item
python -m voice_capture.run --reprocess <hash>  # reprocessa um item específico
python -m voice_capture.cleanup                 # apaga áudio antigo já processado

# Captura no desktop (roda continuamente, ouvindo os atalhos)
python -m voice_capture.listener
```

## Testando o caminho completo

Checklist para validar o fluxo ponta a ponta com uma gravação real:

- [ ] Gravar pelo Atalho no iPhone (Botão de Ação ou widget) e ver a
      notificação "Pensamento salvo ✅".
- [ ] Confirmar o `.m4a` na pasta `VoiceCaptures/inbox` do Google Drive, no
      app Arquivos do iPhone.
- [ ] Confirmar que o mesmo arquivo chegou na pasta correspondente do Google
      Drive Desktop no Windows.
- [ ] Rodar `python -m voice_capture.run` (ou esperar o Task Scheduler) e
      conferir no terminal/log que o item foi processado sem erro.
- [ ] Abrir o Obsidian e encontrar a nova nota em `Inbox/Voz` (ou a pasta que
      você configurou), com frontmatter preenchido e as seções do corpo
      coerentes com o que foi falado.
- [ ] Rodar `python -m voice_capture.run` de novo com o mesmo áudio ainda na
      pasta (sem apagar) e confirmar que **nenhuma nota duplicada** é criada.
- [ ] Forçar um erro (ex: renomear `.env` temporariamente, tirando a chave da
      API) e confirmar que aparece `_Erros de captura.md` no vault, e que o
      áudio/transcrição não são perdidos.
- [ ] Rodar `python -m voice_capture.run --reprocess <hash>` no item que
      falhou (depois de corrigir o problema) e confirmar que a nota é gerada
      normalmente.

## Testes automatizados

```powershell
pip install -r requirements.txt
pytest
```

Os testes usam transcrição e chamada à Claude API mockadas — não exigem
modelo Whisper baixado nem chave de API real para rodar.

## Escopo do MVP e o que fica para depois

Ver seção 4 de [ARCHITECTURE.md](ARCHITECTURE.md). Resumo: este projeto
alimenta o Second Brain (Obsidian). Ele identifica possíveis ideias de
conteúdo (`possible_uses` no frontmatter), mas não decide sozinho o que vira
conteúdo — isso continua sendo uma decisão editorial sua, feita depois, fora
do momento de captura.
