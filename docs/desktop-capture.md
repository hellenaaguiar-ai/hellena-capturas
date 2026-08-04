# Captura no desktop — substituindo o Superwhisper

Extensão do projeto: captura por voz **no computador**, com atalho de teclado
global, para três casos que hoje passam pelo Superwhisper — reunião/aula,
terapia e ideia solta — sem pagar a assinatura dele.

## Por que isso é um componente diferente do pipeline do celular

O pipeline mobile roda em lote: o Task Scheduler dispara o script a cada 15
minutos, ele processa o que encontrar na pasta e termina. Um atalho de
teclado global **precisa de um processo rodando continuamente** em segundo
plano, esperando o toque da tecla a qualquer momento — essa é uma peça de
arquitetura nova, não uma extensão do script existente.

## Decisões

### 1. Atalho global — biblioteca `keyboard`

Um hotkey diferente por modo (sem seletor no meio, sem clique extra):

| Modo | Atalho padrão | Captura áudio do sistema? |
|---|---|---|
| Ideia | `Ctrl+Alt+I` | Não — só microfone |
| Reunião/aula | `Ctrl+Alt+R` | Sim — microfone + o que toca no computador |
| Terapia | `Ctrl+Alt+T` | Sim — microfone + o que toca no computador |

Apertar uma vez começa a gravar; apertar de novo (mesmo atalho) encerra —
igual ao comportamento do Atalho no iPhone. Todos os três atalhos e seus
nomes/pastas são configuráveis em `config.yaml`, sem precisar mexer em código.

Considerei usar AutoHotkey (mais robusto historicamente para hotkeys no
Windows) em vez da biblioteca Python `keyboard`, mas isso significaria
instalar e manter duas ferramentas em vez de uma. Como o uso aqui é hotkeys
simples (sem combinações complexas nem necessidade de suprimir o
comportamento padrão da tecla), `keyboard` é suficiente e mantém tudo num
único stack (Python).

### 2. Captura dupla de áudio — `soundcard` (WASAPI loopback)

Reunião e terapia gravam **duas trilhas separadas** ao mesmo tempo:
- microfone (sua voz)
- "loopback" do dispositivo de saída padrão (o que está tocando no
  computador — voz da outra pessoa numa chamada, áudio de uma aula gravada,
  etc.)

Efeito colateral bom: como as duas vozes já chegam em arquivos separados, a
transcrição naturalmente já vem com "quem é você" e "quem é a outra pessoa"
**sem precisar de um modelo de diarização** (que adicionaria complexidade e
outra dependência pesada para um ganho marginal aqui). O custo dessa
simplificação: se duas pessoas falam ao mesmo tempo dentro da mesma trilha
(ex: duas pessoas na *sua* sala usando só o seu microfone), elas não são
separadas entre si — só "você" (mic) é separado de "o que o computador
reproduz" (loopback).

As duas trilhas são transcritas cada uma para o seu texto e apresentadas como
duas seções distintas na nota (não interligadas frase a frase por timestamp
— alinhar duas gravações independentes no tempo é frágil e o ganho não
compensa a complexidade para o caso de uso).

### 3. Processo sempre ativo, inicia com o Windows

Para reproduzir a sensação do Superwhisper ("a tecla sempre funciona"), o
listener roda como um processo leve iniciado no login do Windows (atalho na
pasta Inicializar), não algo que você precisa lembrar de abrir. Ele só ouve
teclado e, quando aciona uma gravação, delega a transcrição/processamento
pesado para uma thread separada — o hotkey continua responsivo enquanto uma
gravação anterior ainda está sendo processada.

### 3.1. Alternativa ao atalho de teclado: ícone no Desktop

Quem preferir clicar em vez de decorar `Ctrl+Alt+I/R/T` pode usar os
arquivos em `scripts/windows/` (`Gravar Ideia.bat`, `Gravar Reuniao.bat`,
`Gravar Terapia.bat`). Copie o(s) que quiser direto para a Área de
Trabalho — um duplo clique simula o pressionamento do atalho
correspondente contra o `listener` que já está rodando (não substitui o
listener, só oferece outra forma de acioná-lo). Ajuste o caminho
`C:\hellena-capturas` dentro do `.bat` se o projeto estiver em outro
lugar.

### 4. Destino das notas

Reaproveita o vault do Second Brain já configurado:
- **Ideia** → mesma pasta e mesma estrutura já usada pelo celular
  (`type: voice-capture`), só que a origem passa a ser `desktop-voice` em vez
  de `mobile-voice`.
- **Reunião** → pasta própria (`Inbox/Reuniões` por padrão), nota tipo
  `meeting-capture`: resumo, decisões, itens de ação, e as duas transcrições
  (você / outros participantes).
- **Terapia** → pasta própria (`Inbox/Terapia` por padrão), nota tipo
  `therapy-capture`: síntese da sessão, temas abordados, percepções,
  encaminhamentos, e as duas transcrições (você / terapeuta).

Mesmas regras de autoria já usadas no pipeline mobile se aplicam aqui: não
inventar, não completar, não diagnosticar ou interpretar além do que foi
dito — o modo terapia em especial só organiza o que foi falado, não produz
uma "análise" da sessão.

### 5. Nota sobre gravar a outra pessoa

Tecnicamente isso está resolvido, mas vale registrar: o modo reunião/terapia
grava a voz de quem está do outro lado (participante da chamada, terapeuta).
Isso é uma decisão sua sobre avisar ou não as pessoas envolvidas — a
ferramenta não decide isso por você.

## O que não foi implementado agora (fica para depois, se fizer falta)

- Interface gráfica/tray icon para trocar configuração sem editar
  `config.yaml`.
- Diarização real (separar múltiplas vozes dentro da mesma trilha).
- Alinhamento cronológico das duas transcrições numa única linha do tempo.
- Detecção automática de "isso parece uma reunião, ativa o modo sistema" —
  o modo é sempre escolhido explicitamente pelo atalho que você aperta.

## Instalação

Ver `docs/windows-setup.md`, seção "Captura no desktop" (adicionada), para
os passos de instalação das dependências novas, configuração dos atalhos e
autostart.
