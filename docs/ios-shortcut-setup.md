# Configurar o Atalho de captura no iPhone

Objetivo: 1 toque (sem precisar desbloquear o telefone, se seu modelo tiver
Botão de Ação) para começar a gravar, 1 toque para parar, e pronto — o áudio já
está a caminho do pipeline.

## 1. Instalar/configurar o Google Drive no iPhone

1. Instale o app **Google Drive** (se ainda não tiver).
2. Entre com a mesma conta Google que você vai usar no computador Windows.
3. Nas configurações do app Google Drive, ative **"Ativar integração com
   Arquivos"** (Files) — isso faz o Google Drive aparecer como um local
   disponível no app Arquivos do iOS, o que o Atalho precisa para salvar lá.
4. No app **Arquivos** do iPhone, dentro do Google Drive, crie a pasta:
   `VoiceCaptures/inbox`

## 2. Criar o Atalho

Abra o app **Atalhos** (Shortcuts) → toque em **+** para criar um novo atalho.
Nomeie como `Capturar Pensamento`. Adicione as ações nesta ordem:

1. **Gravar Áudio** (Record Audio)
   - Toque nas opções da ação e defina **"Parar Gravação" = "Ao Tocar
     Novamente"** (On Tap) — assim o mesmo toque que iniciou serve para
     encerrar, sem precisar de um segundo atalho.
2. **Definir Nome** (Set Name) no resultado da gravação, algo como:
   `Gravação [Data Atual formato yyyy-MM-dd HH-mm-ss].m4a`
   - Use a ação **Data Atual** (Current Date) formatada, encadeada dentro do
     texto do nome. Isso garante nomes únicos e ordenáveis por data.
3. **Salvar Arquivo** (Save File)
   - Destino: `Google Drive/VoiceCaptures/inbox`
   - **Desmarque** "Perguntar Onde Salvar" — isso é essencial: se o atalho
     perguntar onde salvar, você perde a captura sem toque único.
4. **Mostrar Notificação** (Show Notification)
   - Texto: `Pensamento salvo ✅`
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
