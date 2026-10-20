from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class Loan:
    """Produto abstrato do Factory Method. As subclasses definem a política de cada perfil."""
    user_id: int
    copy_id: int
    loaned_at: date
    due_at: date
    returned_at: date | None = None
    renewals: int = 0
    renewal_requested: bool = False
    id: int | None = None

    LOAN_TYPE = ""
    LOAN_DAYS = 14
    MAX_ACTIVE = 3
    MAX_RENEWALS = 2
    DAILY_FINE = 1.00
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.LOAN_TYPE:
            Loan._registry[cls.LOAN_TYPE] = cls

    @property
    def loan_type(self) -> str:
        return self.LOAN_TYPE

    def days_overdue(self, today: date) -> int:
        end = self.returned_at or today
        return max((end - self.due_at).days, 0)

    def is_overdue(self, today: date) -> bool:
        return self.returned_at is None and today > self.due_at

    def fine(self, today: date) -> float:
        return round(self.days_overdue(today) * self.DAILY_FINE, 2)

    def can_renew(self, today: date) -> bool:
        return self.returned_at is None and not self.is_overdue(today) and self.renewals < self.MAX_RENEWALS

    def renew(self) -> None:
        self.due_at += timedelta(days=self.LOAN_DAYS)
        self.renewals += 1
        self.renewal_requested = False

    @staticmethod
    def from_row(row) -> "Loan":
        cls = Loan._registry[row["loan_type"]]
        parse = date.fromisoformat
        return cls(
            user_id=row["user_id"], copy_id=row["copy_id"],
            loaned_at=parse(row["loaned_at"]), due_at=parse(row["due_at"]),
            returned_at=parse(row["returned_at"]) if row["returned_at"] else None,
            renewals=row["renewals"], renewal_requested=bool(row["renewal_requested"]), id=row["id"],
        )


class StudentLoan(Loan):
    LOAN_TYPE, LOAN_DAYS, MAX_ACTIVE, MAX_RENEWALS, DAILY_FINE = "ALUNO", 14, 3, 2, 1.00


class ProfessorLoan(Loan):
    LOAN_TYPE, LOAN_DAYS, MAX_ACTIVE, MAX_RENEWALS, DAILY_FINE = "PROFESSOR", 30, 10, 3, 0.50


class StaffLoan(Loan):
    LOAN_TYPE, LOAN_DAYS, MAX_ACTIVE, MAX_RENEWALS, DAILY_FINE = "ADMIN", 21, 5, 1, 0.50
