# Google Gemini AI Chatbot (CLI & Telegram Bot) com RAG e Transbordo Inteligente

Boilerplate modular para criar chatbots de Inteligência Artificial utilizando a nova SDK oficial **Google GenAI** (`google-genai`), com:
- **Pontuação de Sessão e Transbordo Humano:** Sistema que pontua intenções de insatisfação, reclamação ou pedidos diretos de atendente. Se atingir a meta (ex: 15 pontos) **dentro** do horário comercial, a conversa é transferida. Se estiver **fora** do horário de atendimento, a transferência é bloqueada e a IA segue atendendo.
- **Base de Conhecimento da Empresa (RAG em Memória):** Consulta automática de dados oficiais da empresa (`data/company_knowledge.json`) para tirar dúvidas sobre planos, preços e políticas.
- **Skills de Comportamento:** Arquivos declarativos em Markdown (`skills/`) que definem persona, tom de voz e regras.
- **Banco de Dados em Memória:** SQLite `:memory:` para gerenciar histórico e contexto de conversas isolados por sessão/usuário.
- **Dupla Interface:** Terminal interativo (**CLI**) com streaming em tempo real e bot completo para o **Telegram**.

---

## 📁 Estrutura do Projeto

```text
AIChat/
│── data/
│   └── company_knowledge.json  # Base de dados com informações oficiais da empresa
│── skills/
│   └── support_agent.md        # Skill de comportamento (persona, tom e regras)
│── handoff_manager.py          # Lógica de pontuação de mensagens e validação de horário comercial
│── memory_db.py                # Banco em memória (histórico, RAG e pontuação de sessão)
│── skill_loader.py             # Módulo de carregamento e parsing de skills
│── chatbot.py                  # Integração Gemini + injeção de conhecimento + transbordo
│── config.py                   # Leitura e validação de configurações (.env)
│── main.py                     # Chat interativo via Terminal (CLI)
│── telegram_bot.py             # Bot para Telegram integrado
│── requirements.txt            # Dependências do projeto
│── .env.example                # Modelo de variáveis de ambiente
└── README.md                   # Documentação
```

---

## ⏰ Regras de Atendimento Humano e Pontuação

Configurável via `.env`:
```env
HANDOFF_THRESHOLD=15    # Limite de pontos para acionar a transferência
SUPPORT_START_HOUR=9    # Horário inicial (09h)
SUPPORT_END_HOUR=18     # Horário final (18h)
```

- **Como pontua:** Palavras como *"atendente"*, *"falar com alguém"*, *"humano"*, *"reclamação"*, *"cancelar"*, *"não resolveu"* somam pontos acumulados na sessão do usuário no banco em memória.
- **Dentro do horário comercial (Seg-Sex, 09h às 18h):** Ao atingir a pontuação, o bot aciona o transbordo para a fila de atendimento humano.
- **Fora do horário comercial:** O sistema detecta que o suporte humano está fechado, **não** transfere e mantém o usuário com o chatbot da IA 24/7.

---

## 🚀 Como Executar

### 1. Configurar Chaves no `.env`
```powershell
Copy-Item .env.example .env
```
Preencha a `GEMINI_API_KEY` e o `TELEGRAM_BOT_TOKEN`.

### 2. Executar no Terminal (CLI)
```powershell
.\venv\Scripts\python.exe main.py
```

### 3. Executar no Telegram
```powershell
.\venv\Scripts\python.exe telegram_bot.py
```
