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
anthropic_model: "claude-sonnet-5"
audio_retention_days: 30

# Opcional: só necessário se for usar a captura por atalho no desktop
# (ver seção 6). Sem esta seção, os valores abaixo (padrão) são usados.
desktop:
  vault_meeting_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Reuniões"
  vault_therapy_dir: "C:\\Users\\Hellena\\ObsidianVault\\Inbox\\Terapia"
  hotkeys:
    idea: "ctrl+alt+i"
    meeting: "ctrl+alt+r"
    therapy: "ctrl+alt+t"
```

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

Aperte `Ctrl+Alt+I` (modo ideia), fale, aperte de novo — deve aparecer uma
janelinha vermelha no canto da tela enquanto grava, e uma notificação
"Captura concluída" ao terminar. Teste também `Ctrl+Alt+R` (reunião) com
algum áudio tocando no computador (ex: um vídeo), para confirmar que a
trilha de sistema está sendo capturada.

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

A partir do próximo login, os três atalhos ficam ativos automaticamente, sem
precisar abrir nada.

## 7. Comandos úteis

```powershell
# Reprocessar um item específico (ex: depois de ajustar o prompt de IA)
python -m voice_capture.run --reprocess <hash>

# Ver o que está pendente/erro sem processar
python -m voice_capture.run --status

# Apagar áudio já processado com mais de N dias (config: audio_retention_days)
python -m voice_capture.cleanup
```
