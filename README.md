# Google Gemini AI Chatbot (CLI & Telegram Bot) com RAG / Base da Empresa

Boilerplate modular para criar chatbots de Inteligência Artificial utilizando a nova SDK oficial **Google GenAI** (`google-genai`), com:
- **Base de Conhecimento da Empresa (RAG em Memória):** Busca automática de dados e políticas da empresa para responder dúvidas dos clientes com precisão.
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
│── memory_db.py                # Banco de dados em memória (histórico + RAG da empresa)
│── skill_loader.py             # Módulo de carregamento e parsing de skills
│── chatbot.py                  # Integração Gemini + injeção contextual de conhecimento
│── config.py                   # Leitura e validação de configurações (.env)
│── main.py                     # Chat interativo via Terminal (CLI)
│── telegram_bot.py             # Bot para Telegram integrado ao Gemini e banco em memória
│── requirements.txt            # Dependências do projeto
│── .env.example                # Modelo de variáveis de ambiente
└── README.md                   # Documentação
```

---

## 🏢 Como Configurar os Dados da Sua Empresa

No arquivo [`data/company_knowledge.json`](data/company_knowledge.json), você pode cadastrar qualquer informação que a IA deva consultar para responder aos clientes:

```json
[
  {
    "category": "Atendimento",
    "title": "Horários de Funcionamento",
    "content": "Atendimento humano das 09h às 18h de segunda a sexta. O bot funciona 24/7."
  },
  {
    "category": "Planos e Preços",
    "title": "Planos de Assinatura",
    "content": "Plano Básico: R$ 49/mês. Plano Pro: R$ 149/mês. Plano Enterprise: sob consulta."
  }
]
```

Sempre que um usuário perguntar algo sobre horários, planos, políticas ou formas de pagamento, o **`memory_db.py`** faz uma busca e fornece a resposta oficial ao Gemini.

---

## 🚀 Como Executar

### 1. Configurar Chaves no `.env`
Se ainda não criou o `.env`, copie o modelo:
```powershell
Copy-Item .env.example .env
```

Preencha no `.env`:
- `GEMINI_API_KEY`: Sua chave do [Google AI Studio](https://aistudio.google.com/app/apikey).
- `TELEGRAM_BOT_TOKEN`: Token obtido no [@BotFather](https://t.me/BotFather).

### 2. Execução

#### Opção A: Chat no Terminal (CLI)
```powershell
.\venv\Scripts\python.exe main.py
```

#### Opção B: Bot no Telegram
```powershell
.\venv\Scripts\python.exe telegram_bot.py
```
