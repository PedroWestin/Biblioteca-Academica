from datetime import date, timedelta

from factories.loan_factory import loan_factory_for
from models.loan import Loan
from services.errors import BusinessError

VIEWS = ("ativos", "atrasados", "historico", "renovacoes")


class LoanService:
    def __init__(self, loans, books, reservations, fines, notifier):
        self.loans, self.books, self.reservations = loans, books, reservations
        self.fines, self.notifier = fines, notifier

    # ── leitor ────────────────────────────────────────────────
    def request(self, user, book_id, today=None):
        """Empréstimo se houver exemplar; caso contrário, entra na fila de reserva."""
        today = today or date.today()
        book = self.books.get(book_id)
        if not book:
            raise BusinessError("Livro não encontrado.")
        if self.fines.pending_total(user.id) > 0:
            raise BusinessError("Você tem multas em aberto. Regularize-as para fazer novos pedidos.")
        if self.loans.has_open_for_book(user.id, book_id):
            raise BusinessError("Você já está com um exemplar deste livro.")

        copy = self.books.find_available_copy(book_id, user.id)
        if copy is None:
            if self.reservations.has_open(user.id, book_id):
                raise BusinessError("Você já está na fila de reserva deste livro.")
            self.reservations.add(user.id, book_id)
            self.notifier.send(user.id, f"Reserva registrada para “{book['title']}”. Avisaremos quando houver exemplar.")
            return "RESERVA", None

        loan = loan_factory_for(user.PROFILE).issue(user.id, copy["id"], today)   # ← Factory Method
        if self.loans.count_open(user.id) >= loan.MAX_ACTIVE:
            raise BusinessError(f"Limite de {loan.MAX_ACTIVE} empréstimos simultâneos atingido.")
        loan.id = self.loans.add(loan)
        self.books.set_copy_status(copy["id"], "EMPRESTADO")
        self.reservations.mark_attended(user.id, book_id)
        self.notifier.send(user.id, f"Empréstimo de “{book['title']}” registrado. Devolução até {loan.due_at:%d/%m/%Y}.")
        return "EMPRESTIMO", loan

    def request_renewal(self, user, loan_id, today=None):
        today = today or date.today()
        row = self.loans.get(loan_id)
        if not row or row["user_id"] != user.id:
            raise BusinessError("Empréstimo não encontrado.")
        loan = Loan.from_row(row)
        if loan.renewal_requested:
            raise BusinessError("A renovação já foi solicitada e aguarda aprovação.")
        if not loan.can_renew(today):
            raise BusinessError("Este empréstimo não pode ser renovado (atrasado ou limite de renovações atingido).")
        book_id = self.books.copy(loan.copy_id)["book_id"]
        if self.reservations.next_pending(book_id):
            raise BusinessError("Há outras pessoas na fila de reserva deste livro.")
        loan.renewal_requested = True
        self.loans.update(loan)

    def for_user(self, user_id, today=None):
        today = today or date.today()
        return {
            "loans": self._enrich(self.loans.by_user(user_id), today),
            "reservations": self.reservations.for_user(user_id),
            "pending_fines": self.fines.pending_total(user_id),
        }

    # ── administrador ─────────────────────────────────────────
    def admin_overview(self, view, today=None):
        today = today or date.today()
        return {
            "rows": self._enrich(self.loans.list_view(view, today), today),
            "counts": {v: len(self.loans.list_view(v, today)) for v in VIEWS},
            "open_fines": self.fines.open_total(),
        }

    def return_loan(self, loan_id, today=None):
        """Registra devolução, gera multa se houver atraso e libera/reserva o exemplar. Retorna a multa (ou None)."""
        today = today or date.today()
        loan = self._get(loan_id)
        if loan.returned_at:
            raise BusinessError("Este empréstimo já foi devolvido.")
        loan.returned_at = today
        loan.renewal_requested = False
        self.loans.update(loan)
        fine = self.fines.assess(loan, today, notify=True)

        copy = self.books.copy(loan.copy_id)
        waiting = self.reservations.next_pending(copy["book_id"])
        if waiting:
            self.books.set_copy_status(copy["id"], "RESERVADO")
            self.reservations.set_status(waiting["id"], "NOTIFICADA")
            title = self.books.get(copy["book_id"])["title"]
            self.notifier.send(waiting["user_id"], f"“{title}” já está disponível para você. Solicite o empréstimo no catálogo.")
        else:
            self.books.set_copy_status(copy["id"], "DISPONIVEL")
        return fine

    def assess_fine(self, loan_id, today=None):
        today = today or date.today()
        amount = self.fines.assess(self._get(loan_id), today, notify=True)
        if amount is None:
            raise BusinessError("Este empréstimo não tem atraso.")
        return amount

    def approve_renewal(self, loan_id, today=None):
        today = today or date.today()
        loan = self._get(loan_id)
        if not loan.renewal_requested:
            raise BusinessError("Não há renovação pendente neste empréstimo.")
        if not loan.can_renew(today):
            raise BusinessError("Renovação não permitida (atraso ou limite de renovações).")
        loan.renew()
        self.loans.update(loan)
        self.notifier.send(loan.user_id, f"Renovação aprovada. Nova data de devolução: {loan.due_at:%d/%m/%Y}.")

    def reject_renewal(self, loan_id):
        loan = self._get(loan_id)
        if not loan.renewal_requested:
            raise BusinessError("Não há renovação pendente neste empréstimo.")
        loan.renewal_requested = False
        self.loans.update(loan)
        self.notifier.send(loan.user_id, f"Renovação do empréstimo #{loan.id} não aprovada. Devolva até {loan.due_at:%d/%m/%Y}.")

    def send_reminders(self, today=None, days_before=2):
        """Avisa vencimentos próximos e atrasos (no máximo 1 aviso por dia/empréstimo)."""
        today, sent = today or date.today(), 0
        for r in self.loans.list_view("ativos", today):
            due = date.fromisoformat(r["due_at"])
            if due < today:
                msg = f"“{r['title']}” está atrasado desde {due:%d/%m/%Y}. Devolva o quanto antes."
            elif due <= today + timedelta(days=days_before):
                msg = f"“{r['title']}” vence em {due:%d/%m/%Y}."
            else:
                continue
            sent += self.notifier.send_once_per_day(r["user_id"], msg)
        return sent

    # ── internos ──────────────────────────────────────────────
    def _get(self, loan_id) -> Loan:
        row = self.loans.get(loan_id)
        if not row:
            raise BusinessError("Empréstimo não encontrado.")
        return Loan.from_row(row)

    @staticmethod
    def _enrich(rows, today):
        out = []
        for r in rows:
            loan = Loan.from_row(r)
            d = dict(r)
            d.update(overdue=loan.is_overdue(today), overdue_days=loan.days_overdue(today),
                     fine_estimate=loan.fine(today), can_renew=loan.can_renew(today),
                     max_renewals=loan.MAX_RENEWALS)
            out.append(d)
        return out
