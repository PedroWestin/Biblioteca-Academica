"""Factory Method para empréstimos.

Creator  : LoanFactory (declara o factory method `create_loan`)
Concrete : StudentLoanFactory, ProfessorLoanFactory, StaffLoanFactory
Product  : models.loan.Loan e subclasses (StudentLoan, ProfessorLoan, StaffLoan)

O LoanService depende apenas de LoanFactory/Loan: novos perfis (ex.: Pesquisador)
entram criando um produto + uma fábrica e registrando-a em _FACTORIES.
"""
from abc import ABC, abstractmethod
from datetime import date, timedelta

from models.loan import Loan, ProfessorLoan, StaffLoan, StudentLoan


class LoanFactory(ABC):
    @abstractmethod
    def create_loan(self, user_id: int, copy_id: int, today: date) -> Loan:
        """Factory method: cada subclasse decide qual produto instanciar."""

    def issue(self, user_id: int, copy_id: int, today: date | None = None) -> Loan:
        return self.create_loan(user_id, copy_id, today or date.today())

    @staticmethod
    def _build(cls: type[Loan], user_id: int, copy_id: int, today: date) -> Loan:
        return cls(user_id=user_id, copy_id=copy_id, loaned_at=today, due_at=today + timedelta(days=cls.LOAN_DAYS))


class StudentLoanFactory(LoanFactory):
    def create_loan(self, user_id, copy_id, today):
        return self._build(StudentLoan, user_id, copy_id, today)


class ProfessorLoanFactory(LoanFactory):
    def create_loan(self, user_id, copy_id, today):
        return self._build(ProfessorLoan, user_id, copy_id, today)


class StaffLoanFactory(LoanFactory):
    def create_loan(self, user_id, copy_id, today):
        return self._build(StaffLoan, user_id, copy_id, today)


_FACTORIES = {"ALUNO": StudentLoanFactory(), "PROFESSOR": ProfessorLoanFactory(), "ADMIN": StaffLoanFactory()}


def loan_factory_for(profile: str) -> LoanFactory:
    try:
        return _FACTORIES[profile]
    except KeyError:
        raise ValueError(f"Perfil sem política de empréstimo: {profile}") from None
