# Configurar o Atalho de captura no iPhone

Objetivo: 1 toque (sem precisar desbloquear o telefone, se seu modelo tiver
Botão de Ação) para começar a gravar, 1 toque para parar, e pronto — o áudio já
está a caminho do pipeline.

## 1. Pasta de transporte no iCloud Drive

No app **Arquivos** do iPhone, dentro do iCloud Drive, use a pasta
`VoiceCaptures/Inbox`. No Windows, o iCloud para Windows sincroniza essa pasta
para `C:\Users\helle\iCloudDrive\VoiceCaptures\Inbox`.

## 2. Criar o Atalho

Abra o app **Atalhos** (Shortcuts) → toque em **+** para criar um novo atalho.
Crie tres atalhos: `Capturar Ideia`, `Capturar Reflexão` e
`Capturar Insight de Livro`. As ações são iguais; muda apenas o prefixo do nome:

1. **Gravar Áudio** (Record Audio)
   - Toque nas opções da ação e defina **"Parar Gravação" = "Ao Tocar
     Novamente"** (On Tap) — assim o mesmo toque que iniciou serve para
     encerrar, sem precisar de um segundo atalho.
2. **Definir Nome** (Set Name) no resultado da gravação, algo como:
   - `IDEIA__ [Data Atual formato yyyy-MM-dd HH-mm-ss].m4a`
   - `REFLEXAO__ [Data Atual formato yyyy-MM-dd HH-mm-ss].m4a`
   - `LIVRO__ [Data Atual formato yyyy-MM-dd HH-mm-ss].m4a`
   - Use a ação **Data Atual** (Current Date) formatada, encadeada dentro do
     texto do nome. Isso garante nomes únicos e ordenáveis por data.
3. **Salvar Arquivo** (Save File)
   - Destino: `iCloud Drive/VoiceCaptures/Inbox`
   - **Desmarque** "Perguntar Onde Salvar" — isso é essencial: se o atalho
     perguntar onde salvar, você perde a captura sem toque único.
4. **Mostrar Notificação** (Show Notification)
   - Texto correspondente: `Ideia salva`, `Reflexão salva` ou `Insight de livro salvo`.

Ao gravar um insight de livro, diga o título no começo. Para livro físico, use
uma formulação como: `Livro X. Página 42. Grifei: ... Isso me fez pensar...`.
Trechos ditados ficam marcados para conferência no exemplar, pois a transcrição
pode trocar palavras e não deve ser tratada automaticamente como citação literal.
   - Isso é a "confirmação discreta" — aparece e some, sem exigir nenhuma ação
     sua.

## 3. Colocar o Atalho a 1 toque de distância

Escolha **uma** destas opções (ou as duas):

### Opção A — Botão de Ação (iPhone 15 Pro ou mais novo)
Ajustes → Botão de Ação → escolha **Atalho** → selecione `Capturar Pensamento`.
Resultado: aperta e segura o Botão de Ação, mesmo com a tela desligada, e a
gravação começa. Aperta de novo para parar.

### Opção B — Widget na Tela Bloqueada (qualquer iPhone com iOS 16+)
Mantenha pressionada a tela bloqueada → **Personalizar** → **Tela Bloqueada** →
adicione um widget de **Atalhos** → escolha `Capturar Pensamento`.
Resultado: toque no widget na tela bloqueada (pode pedir Face ID/toque para
confirmar, dependendo das suas configurações de privacidade) e a gravação
começa.

### Opção C — fallback: Central de Controle
Ajustes → Centro de Controle → adicione **Atalho** e associe a
`Capturar Pensamento`. Útil como alternativa se A/B não estiverem disponíveis.

## 4. Testar

1. Ative o atalho (Botão de Ação ou widget).
2. Fale uma frase de teste.
3. Ative de novo para parar.
4. Confira a notificação "Pensamento salvo ✅".
5. Abra o app Arquivos → Google Drive → `VoiceCaptures/inbox` e confirme que o
   `.m4a` está lá.
6. Espere a sincronização (geralmente segundos a poucos minutos, dependendo da
   conexão) e confira no computador Windows, na mesma pasta do Google Drive
   Desktop, se o arquivo chegou.

A partir daqui, o pipeline no Windows (ver `docs/windows-setup.md`) assume o
resto sozinho.
