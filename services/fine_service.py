from datetime import date

from services.errors import BusinessError


class FineService:
    def __init__(self, fines, notifier):
        self.fines = fines
        self.notifier = notifier

    def assess(self, loan, today=None, notify=False):
        """Calcula a multa pela política do tipo de empréstimo e a registra. Retorna o valor ou None."""
        amount = loan.fine(today or date.today())
        if amount <= 0:
            return None
        self.fines.upsert(loan.id, amount)
        if notify:
            self.notifier.send(
                loan.user_id,
                f"Multa de R$ {amount:.2f} pelo atraso de {loan.days_overdue(today or date.today())} dia(s) "
                f"no empréstimo #{loan.id}. Regularize no balcão da biblioteca.",
            )
        return amount

    def pay(self, fine_id):
        if not self.fines.pay(fine_id):
            raise BusinessError("Multa não encontrada ou já paga.")

    def pending_total(self, user_id):
        return self.fines.open_total(user_id)

    def open_total(self):
        return self.fines.open_total()
