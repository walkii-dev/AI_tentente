# Telegram AI Bot com Google Gemini

Bot profissional para o **Telegram** integrado à API oficial do **Google Gemini** (`google-genai`).

Desenvolvido para atendimento a clientes, suporte técnico institucional e vendas, com:
- **Respostas Inteligentes com Google Gemini (`gemini-2.5-flash`):** Respostas rápidas e contextuais.
- **Base de Conhecimento da Empresa (RAG em Memória):** Consulta automática de dados e políticas da empresa (`data/company_knowledge.json`) para tirar dúvidas sobre planos, preços e regras.
- **Horário Oficial de Brasília em Tempo Real:** Consciência temporal sem precisar perguntar data/hora ao usuário.
- **Pontuação de Sessão e Transbordo Humano:** Se o cliente demonstrar insatisfação ou solicitar atendimento humano dentro do horário comercial (Seg-Sex, 09h às 18h), a conversa é transferida. Fora desse período, a IA segue atendendo 24/7.
- **Sessões Isoladas por Usuário:** Banco SQLite em memória (`cache=shared`) garantindo contexto individual para cada usuário do Telegram.

---

## 📁 Estrutura do Projeto

```text
AIChat/
│── telegram_bot.py             # Arquivo principal de execução do Bot do Telegram
│── chatbot.py                  # Serviço de integração com Google Gemini e regras de negócio
│── handoff_manager.py          # Pontuação de mensagens e validação de horário de Brasília
│── memory_db.py                # Banco relacional em memória (histórico, RAG e sessões)
│── skill_loader.py             # Leitor de arquivos de personalidade e tom de voz
│── config.py                   # Validação de credenciais e parâmetros (.env)
│── data/
│   └── company_knowledge.json  # FAQ e dados cadastrados da empresa
│── skills/
│   └── support_agent.md        # Prompt de persona e diretrizes da IA
│── requirements.txt            # Dependências Python
│── .env.example                # Modelo de variáveis de ambiente
└── README.md                   # Documentação
```

---

## 🚀 Como Configurar e Rodar o Bot

### 1. Criar e Ativar o Ambiente Virtual

No Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Instalar as Dependências

```powershell
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente (`.env`)

Copie o modelo de exemplo:
```powershell
Copy-Item .env.example .env
```

Abra o arquivo `.env` e preencha suas chaves:
```env
# Obtenha em: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=sua_chave_aqui

# Obtenha ao criar o bot com o @BotFather no Telegram
TELEGRAM_BOT_TOKEN=seu_token_do_telegram_aqui

# Modelo padrão
GEMINI_MODEL=gemini-2.5-flash
TIMEZONE=America/Sao_Paulo
```

### 4. Iniciar o Bot

```powershell
python telegram_bot.py
```
*(ou `.\venv\Scripts\python.exe telegram_bot.py`)*

Pronto! Acesse seu bot no aplicativo do **Telegram**, envie `/start` e comece a conversar.

---

## 💬 Comandos no Telegram
- `/start` — Inicia o atendimento e apresenta o assistente.
- `/ajuda` — Informa horários e comandos disponíveis.
- `/limpar` — Apaga a memória e histórico da conversa atual no banco.
