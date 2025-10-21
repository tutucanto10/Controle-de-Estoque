# 🏗️ DOMMA - Sistema de Controle de Estoque

Aplicativo desktop desenvolvido em **Python + CustomTkinter** para gerenciamento de estoque e notebooks corporativos da **DOMMA Incorporações**.  
O sistema permite controlar ativos por obra, registrar transferências, baixas, devoluções, anexar arquivos e gerar relatórios automáticos.

---

## 🚀 Funcionalidades Principais

### 📦 Controle de Estoque
- Cadastro, edição e exclusão de itens por obra.  
- Campos detalhados: nome, número de série, categoria, status, condição e observações.  
- Controle de quantidades: total, em uso, disponível, manutenção.  
- Filtros dinâmicos por categoria, nome e status.  

### 🔄 Movimentações e Log
- Registro automático de **entradas**, **saídas**, **devoluções** e **transferências**.  
- Logs com data, responsável, observação e obra de origem/destino.  
- Controle seguro de transferências entre obras.  

### 💻 Módulo de Notebooks
- Controle individual de notebooks corporativos.  
- Situações: Disponível, Alocado, Triagem, Em Verificação, Manutenção.  
- Associação de periféricos (mouse, teclado, monitor, etc).  
- Armazenamento local em **SQLite**, com futura integração via Supabase.

### 📊 Relatórios e Dashboards
- Painel com indicadores gerais e gráficos interativos (Matplotlib).  
- Filtros por período, tipo de movimentação e obra.  
- Exportação de relatórios em **Excel (.xlsx)** e **PDF (.pdf)**.  
- Gráficos: “Movimentações por Tipo” e “Top 5 Itens Movimentados”.

### 📂 Anexos e Documentação
- Upload de notas fiscais, comprovantes e imagens.  
- Armazenamento vinculado ao item (com caminho dinâmico no banco).  

---

## 🧩 Tecnologias Utilizadas

| Tecnologia | Função |
|-------------|--------|
| **Python 3.11+** | Linguagem principal |
| **CustomTkinter** | Interface gráfica moderna |
| **SQLite / PostgreSQL (Supabase)** | Banco de dados local e remoto |
| **Matplotlib** | Geração de gráficos e relatórios |
| **Pandas + OpenPyXL** | Exportação de planilhas Excel |
| **ReportLab** | Exportação de relatórios em PDF |
| **asyncpg** | Integração assíncrona e sincronização em tempo real (futura) |

---

## 🛠️ Instalação e Execução

### 1️⃣ Clone o repositório
```bash
git clone https://github.com/tutucanto10/Controle-de-Estoque.git
cd Controle-de-Estoque

2️⃣ Crie o ambiente virtual
python -m venv .venv
.venv\Scripts\activate

3️⃣ Instale as dependências
pip install -r requirements.txt

4️⃣ Execute o aplicativo
python controle_estoque.py

🧱 Estrutura do Projeto
📦 Controle-de-Estoque
 ┣ 📂 dist/                 → executáveis gerados pelo PyInstaller
 ┣ 📂 build/                → arquivos temporários de compilação
 ┣ 📂 assets/               → ícones, imagens, PDFs
 ┣ 📜 controle_estoque.py   → módulo principal da aplicação
 ┣ 📜 db.py                 → camada de comunicação com banco de dados
 ┣ 📜 requirements.txt      → dependências do projeto
 ┣ 📜 README.md             → este arquivo
 ┗ 📜 .gitignore            → arquivos ignorados pelo Git

🧮 Build (.exe)
pyinstaller --onefile --noconsole --icon=domma.ico ^
  --hidden-import=customtkinter ^
  --collect-all pandas --collect-all matplotlib --collect-all reportlab ^
  controle_estoque.py

O executável ficará disponível em:
dist/controle_estoque.exe

###📘 Próximas Atualizações
🔁 Sincronização em tempo real com Supabase.
🌐 Dashboard Web (FastAPI + React).
📱 App mobile para consulta de estoque.
🧾 Impressão de etiquetas com QR Code.
🧠 Inteligência de manutenção preventiva.
☁️ Integração com SharePoint / Microsoft 365.

👨‍💻 Autor
Artur Canto
🏢 DOMMA Incorporações
📧 contato: a.canto@dommainc.com.br
