# Configurar o processamento no Windows

## 1. Pré-requisitos

1. **Python 3.11+** — instale de [python.org](https://www.python.org/downloads/)
   marcando "Add python.exe to PATH" no instalador.
2. **Google Drive para Desktop** — instale e entre com a mesma conta usada no
   iPhone. Confirme que a pasta `VoiceCaptures/inbox` aparece dentro da unidade
   do Google Drive no Explorador de Arquivos (normalmente em
   `G:\Meu Drive\VoiceCaptures\inbox` ou `C:\Users\<você>\Google Drive\...`,
   dependendo da versão do app).
3. **Obsidian** já configurado com o seu vault em uma pasta local conhecida.

## 2. Instalar o projeto

```powershell
cd caminho\para\hellena-capturas
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

A primeira transcrição baixa o modelo do Whisper automaticamente (alguns
centenas de MB, uma única vez).

## 3. Configurar

```powershell
copy config.example.yaml config.yaml
copy .env.example .env
```

Edite `config.yaml` com os caminhos reais da sua máquina:

```yaml
inbox_dir: "G:\\Meu Drive\\VoiceCaptures\\inbox"
vault_inbox_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Voz"
data_dir: "data"
whisper_model: "small"
whisper_language: "pt"
whisper_initial_prompt: "Hellena, We Founders, Ravi, Yá."
anthropic_model: "claude-sonnet-5"
audio_retention_days: 30

# Opcional: só necessário se for usar a captura por atalho no desktop
# (ver seção 6). Sem esta seção, os valores abaixo (padrão) são usados.
desktop:
  vault_meeting_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Reuniões"
  vault_therapy_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Terapia"
  vault_class_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Aulas"
  vault_reflection_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Reflexões"
  hotkeys:
    idea: "ctrl+space"
    reflection: "ctrl+alt+d"
    meeting: "ctrl+alt+r"
    therapy: "ctrl+alt+t"
    class: "ctrl+alt+a"
    stop: "ctrl+alt+p"
```

`whisper_initial_prompt` é opcional e serve pra reduzir erro de grafia em
nomes próprios e termos em inglês que aparecem em meio à fala em português
(ex: `Hellena` virando `Helena`, `We Founders` virando `Way Fonders`, `Ravi`
virando `Javi`). Liste os termos que mais aparecem nas suas gravações,
escritos exatamente como devem sair. Não é uma substituição automática — o
Whisper continua transcrevendo só o que ouviu, isso apenas melhora a chance
de acertar a grafia certa desses termos específicos. Se mesmo assim o erro
persistir bastante (principalmente em trechos inteiros em inglês), o
próximo passo é trocar `whisper_model` de `"small"` para `"medium"` — mais
lento na CPU, mas sensivelmente melhor em nomes próprios e troca de idioma
no meio da fala.

Limite importante do `initial_prompt`: ele influencia a grafia, não o
significado. Um nome curto que soa igual a uma palavra comum (ex: "Yá" e
"IA") continua ambíguo pro Whisper mesmo com o prompt, porque a diferença
não está no som, e sim em quem está falando de quem — isso o modelo de
transcrição não tem como saber. Nesses casos a transcrição bruta pode sair
"IA" onde era "Yá" (ou o contrário) mesmo com o termo na lista; revise à
mão quando o contexto permitir.

Edite `.env` com sua chave da Claude API (crie em
[console.anthropic.com](https://console.anthropic.com)):

```
ANTHROPIC_API_KEY=sk-ant-...
```

`config.yaml` e `.env` **não são commitados** (estão no `.gitignore`) — contêm
caminhos e segredos pessoais.

## 4. Testar manualmente

Grave um áudio de teste pelo Atalho no iPhone (veja
`docs/ios-shortcut-setup.md`), espere sincronizar, e rode:

```powershell
python -m voice_capture.run
```

Saída esperada no terminal: um resumo do que foi processado. Confira:
- o arquivo `.md` apareceu na pasta configurada do vault;
- o Obsidian mostra a nova nota (pode precisar recarregar/reabrir o vault);
- `data/state.json` tem uma entrada com `"status": "done"`.

Se algo falhar, rode de novo — o pipeline retoma do que já foi salvo, e uma
nota `_Erros de captura.md` aparece no próprio vault explicando o que deu
errado.

## 5. Agendar execução automática (Task Scheduler)

Como seu computador fica ligado a maior parte do dia, a forma mais simples é
rodar o pipeline a cada 15 minutos:

1. Abra o **Agendador de Tarefas** (Task Scheduler).
2. **Criar Tarefa Básica** → nome `Hellena Capturas`.
3. Gatilho: **Diariamente**, repetir a cada **15 minutos**, indefinidamente.
4. Ação: **Iniciar um programa**
   - Programa/script: `caminho\para\hellena-capturas\.venv\Scripts\python.exe`
   - Argumentos: `-m voice_capture.run`
   - Iniciar em: `caminho\para\hellena-capturas`
5. Nas propriedades da tarefa, marque **"Executar mesmo que o usuário não
   esteja conectado"** se quiser que rode mesmo com a sessão bloqueada (pode
   pedir sua senha do Windows para salvar a tarefa).

A partir daqui: grave no celular, espere alguns minutos, abra o Obsidian. Não
precisa fazer mais nada.

## 6. Captura no desktop (substitui o Superwhisper)

Ver a decisão de arquitetura completa em `docs/desktop-capture.md`. Passos de
instalação:

```powershell
pip install -e .[desktop]
```

Confirme os atalhos e pastas em `config.yaml` (seção `desktop`, exemplo acima)
e teste rodando o listener em primeiro plano, num terminal:

```powershell
python -m voice_capture.listener
```

Aperte `Ctrl+Espaço` (modo ideia), fale, aperte de novo. Uma janelinha
vermelha aparece no canto da tela enquanto grava ("🔴 Gravando — Ideia"),
muda pra laranja assim que você para ("⏳ Processando — Ideia", enquanto
transcreve e a IA estrutura o texto), e some sozinha quando termina — não
fica nada visível o resto do tempo. Uma notificação "Captura concluída"
também aparece nesse momento. Teste também `Ctrl+Alt+R` (reunião) com
algum áudio tocando no computador (ex: um vídeo), para confirmar que a
trilha de sistema está sendo capturada. `Ctrl+Alt+A` (aula) usa a mesma
trilha de sistema, só que sem microfone. `Ctrl+Alt+D` (reflexão) grava só
o microfone, igual ideia, mas processa e salva num formato diferente (mais
próximo do de terapia).

Um ícone azul aparece na bandeja do sistema (perto do relógio) assim que o
listener inicia — fica vermelho enquanto uma gravação está em andamento.
Clique com o botão direito nele e escolha **"Sair"** para encerrar o
programa (não precisa mais fechar pelo terminal).

Depois de validar, registre o listener para iniciar com o Windows:

1. Crie um arquivo `iniciar_listener.vbs` (evita abrir uma janela de console)
   com este conteúdo, ajustando o caminho:
   ```vbscript
   Set WshShell = CreateObject("WScript.Shell")
   WshShell.Run "caminho\para\hellena-capturas\.venv\Scripts\pythonw.exe -m voice_capture.listener", 0
   ```
2. Pressione `Win+R`, digite `shell:startup` e Enter — abre a pasta
   Inicializar do seu usuário.
3. Copie um atalho para `iniciar_listener.vbs` dentro dessa pasta.

A partir do próximo login, os quatro atalhos de modo ficam ativos automaticamente, sem
precisar abrir nada.

### Problema conhecido (resolvido): `AssertionError` sem mensagem ao gravar

Versões anteriores usavam a biblioteca `soundcard`, que assume que todo
driver de áudio do Windows relata o formato `WAVEFORMATEXTENSIBLE`. Em
alguns drivers isso é falso e a gravação falhava com um `AssertionError`
sem mensagem — nenhuma configuração do Windows (nem trocar o "Formato
Padrão" em Painel de Controle → Som) resolvia, porque é uma característica
do driver, não algo configurável.

O projeto usa `PyAudioWPatch` (fork do PyAudio com patch de loopback
WASAPI) em vez de `soundcard`, que não tem essa limitação. Se você via
esse erro antes, dê `git pull`, reinstale a dependência nova
(`pip install -e .[desktop]`) e teste de novo — não deve precisar mexer em
nada no Windows.

Se ainda assim der erro na gravação, a mensagem agora deve vir com a causa
real (dispositivo não encontrado, etc.) em vez de um `AssertionError` em
branco — copie o texto e me mande.

### Problema conhecido (resolvido): listener morre com `Tcl_AsyncDelete`

Se o terminal mostrar `Tcl_AsyncDelete: async handler deleted by the wrong
thread` e o processo do listener morrer sozinho logo em seguida (o prompt
do PowerShell volta sem você apertar nada) — isso **não é um aviso
inofensivo, é um erro fatal do Tcl** que mata o processo inteiro,
incluindo qualquer gravação/transcrição em andamento no momento.

Causa: a janelinha vermelha de indicador visual criava um `Tk()` novo (e
uma thread nova) a cada gravação — criar vários interpretadores Tcl em
threads diferentes ao longo da vida do processo é uma causa conhecida
desse crash no Windows. A partir desta versão existe só uma janela Tk,
criada uma única vez e reaproveitada (mostra/esconde) em todas as
gravações seguintes — `git pull` traz a correção.

## 7. Comandos úteis

```powershell
# Reprocessar um item específico (ex: depois de ajustar o prompt de IA)
python -m voice_capture.run --reprocess <hash>

# Ver o que está pendente/erro sem processar
python -m voice_capture.run --status

# Apagar áudio já processado com mais de N dias (config: audio_retention_days)
python -m voice_capture.cleanup
```
