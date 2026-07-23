# Hellena Capturas

Ferramenta pessoal de captura de pensamentos por voz: aperta um botão no
iPhone, fala, solta — e a gravação chega sozinha, transcrita e estruturada, no
seu vault do Obsidian.

Não é um produto, não é um SaaS. É um script que roda no seu computador.

Leia primeiro **[ARCHITECTURE.md](ARCHITECTURE.md)** para o diagnóstico
completo, a comparação de alternativas e as decisões de arquitetura. Este
README é só o "como instalar e usar".

## Como funciona, resumido

```
iPhone (Atalho + Botão de Ação)
  → Google Drive (transporte)
    → Windows: Whisper local transcreve (áudio nunca sai da máquina)
      → Claude API estrutura o texto (só texto, nunca áudio)
        → Markdown escrito no vault do Obsidian
```

Detalhes de privacidade — o que sai da sua máquina e para onde — estão na
seção 12 de [ARCHITECTURE.md](ARCHITECTURE.md).

## Instalação

1. **No iPhone:** siga [docs/ios-shortcut-setup.md](docs/ios-shortcut-setup.md)
   para criar o Atalho de captura.
2. **No Windows:** siga [docs/windows-setup.md](docs/windows-setup.md) para
   instalar o pipeline e agendar sua execução automática.

## Uso do dia a dia

Depois de instalado, o uso é só:

1. Aperte o Botão de Ação (ou o widget na tela bloqueada).
2. Fale.
3. Aperte de novo para parar.
4. Volte ao que estava fazendo.

A nota aparece no Obsidian em até ~15 minutos, sozinha. Se algo falhar, você
vai ver uma nota `_Erros de captura.md` no vault explicando o que houve — a
captura nunca falha em silêncio.

## Comandos

```powershell
python -m voice_capture.run                    # processa o que estiver pendente
python -m voice_capture.run --status            # mostra o estado de cada item
python -m voice_capture.run --reprocess <hash>  # reprocessa um item específico
python -m voice_capture.cleanup                 # apaga áudio antigo já processado
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
