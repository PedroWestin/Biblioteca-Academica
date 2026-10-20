# Biblioteca Acadêmica

Sistema de biblioteca em Python (Flask + SQLite) com arquitetura em 3 camadas e **Factory Method**.

## Executar
```bash
pip install -r requirements.txt
python seed.py          # usuários, acervo e empréstimos de demonstração
python app.py           # http://127.0.0.1:5000
python -m unittest discover -s tests -t .
```
Contas de demonstração: `admin@biblioteca.edu / admin123`, `aluno@biblioteca.edu / aluno123`, `professor@biblioteca.edu / prof123`.

## Camadas
| Camada | Pasta | Responsabilidade |
|---|---|---|
| Apresentação | `presentation/` | Rotas Flask, templates e CSS. Não contém SQL nem regras. |
| Regra de negócio | `services/`, `models/`, `factories/` | Autenticação, catálogo, circulação, multas, notificações. |
| Persistência | `repositories/`, `database/` | SQL (SQLite) isolado em repositórios. |

Dependências apontam para baixo: `presentation → services → repositories`. `services/container.py` monta tudo.

## Factory Method
- `factories/loan_factory.py`: `LoanFactory` (Creator) declara `create_loan()`; `StudentLoanFactory`, `ProfessorLoanFactory` e `StaffLoanFactory` decidem o produto (`StudentLoan`, `ProfessorLoan`, `StaffLoan`).
- `factories/user_factory.py`: o mesmo padrão para perfis (`Student`, `Professor`, `Administrator`).
- `LoanService.request()` só usa `loan_factory_for(perfil).issue(...)`; prazo, limite, renovações e multa diária vêm do produto.

| Perfil | Prazo | Máx. simultâneos | Renovações | Multa/dia |
|---|---|---|---|---|
| Aluno | 14 dias | 3 | 2 | R$ 1,00 |
| Professor | 30 dias | 10 | 3 | R$ 0,50 |
| Bibliotecário | 21 dias | 5 | 1 | R$ 0,50 |

Novo perfil: criar produto em `models/`, fábrica concreta, e registrar nos dicionários `_FACTORIES`.

## Regras de circulação
Sem exemplar livre, o pedido vira reserva (fila por ordem de chegada). Na devolução, o exemplar fica `RESERVADO` para o primeiro da fila, que é notificado. Multas em aberto bloqueiam novos pedidos. Renovação exige pedido do leitor e aprovação do administrador, e é negada se houver fila ou atraso.

## Para produção
CSRF (Flask-WTF), aprovação de perfil Professor no cadastro, expiração de reservas notificadas, envio real de e-mail (`channels` do `NotificationService`), migração para PostgreSQL com transações por caso de uso, e agendamento diário de `send_reminders()`.
