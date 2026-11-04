# Google Gemini AI Chatbot (CLI & Telegram Bot)

Boilerplate modular para criar chatbots de Inteligência Artificial utilizando a nova SDK oficial **Google GenAI** (`google-genai`), com suporte a modelos como **Gemini 2.5 Flash** e **Gemini 2.5 Pro**.

---

## ✨ Recursos

- **Google GenAI SDK Oficial (`google-genai`):** Modelos rápidos com streaming e suporte a instruções do sistema (`system_instruction`).
- **Skills de Comportamento:** Arquivos declarativos em Markdown (`skills/`) que definem persona, tom de voz e regras.
- **Banco de Dados em Memória:** SQLite `:memory:` para gerenciar histórico e contexto de conversas isolados por sessão/usuário.
- **Dupla Interface:** Terminal interativo (**CLI**) com streaming em tempo real e bot completo para o **Telegram**.

---

## 📁 Estrutura do Projeto

```text
AIChat/
│── skills/
│   └── support_agent.md   # Skill de comportamento (persona, tom e regras)
│── memory_db.py           # Banco de dados relacional em memória (SQLite :memory:)
│── skill_loader.py        # Módulo de carregamento e parsing de skills
│── chatbot.py             # Cliente Gemini: integração com google-genai e streaming
│── config.py              # Leitura e validação de configurações (.env)
│── main.py                # Chat interativo via Terminal (CLI)
│── telegram_bot.py        # Bot para Telegram integrado ao Gemini e banco em memória
│── requirements.txt       # Dependências do projeto
│── .env.example           # Modelo de variáveis de ambiente
└── README.md              # Documentação
```

---

## 🚀 Como Configurar e Executar

### 1. Obter a Chave de API do Gemini
A chave pode ser obtida gratuitamente no [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Configurar o `.env`
Se ainda não criou o `.env`, copie o modelo:
```powershell
Copy-Item .env.example .env
```

Abra o arquivo `.env` e configure:
```env
GEMINI_API_KEY=sua_chave_do_google_ai_studio
GEMINI_MODEL=gemini-2.5-flash
```

*(Se for usar o Telegram, adicione também o seu `TELEGRAM_BOT_TOKEN` gerado no [@BotFather](https://t.me/BotFather))*.

---

### 3. Execução

#### Opção A: Executar no Terminal (CLI)
```powershell
.\venv\Scripts\python.exe main.py
```
- `/limpar`: Reinicia a memória da conversa no banco em memória.
- `/sair`: Encerra o chat.

#### Opção B: Executar no Telegram
```powershell
.\venv\Scripts\python.exe telegram_bot.py
```
- Cada usuário tem sua sessão isolada no banco de dados em memória.
- Comandos disponíveis: `/start`, `/limpar`, `/ajuda`.
