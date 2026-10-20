from models.loan import Loan

_LOAN_SELECT = """
SELECT l.*, u.name AS user_name, u.profile AS user_profile,
       b.id AS book_id, b.title, c.code AS copy_code,
       f.id AS fine_id, f.amount AS fine_amount, f.status AS fine_status
FROM loans l
JOIN users u ON u.id = l.user_id
JOIN copies c ON c.id = l.copy_id
JOIN books b ON b.id = c.book_id
LEFT JOIN fines f ON f.loan_id = l.id
"""
_VIEWS = {
    "ativos": "l.returned_at IS NULL",
    "atrasados": "l.returned_at IS NULL AND l.due_at < :today",
    "historico": "l.returned_at IS NOT NULL",
    "renovacoes": "l.returned_at IS NULL AND l.renewal_requested = 1",
}


class LoanRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, loan: Loan) -> int:
        cur = self.conn.execute(
            """INSERT INTO loans(user_id, copy_id, loan_type, loaned_at, due_at)
               VALUES (?,?,?,?,?)""",
            (loan.user_id, loan.copy_id, loan.loan_type, loan.loaned_at.isoformat(), loan.due_at.isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, loan_id):
        return self.conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()

    def update(self, loan: Loan):
        self.conn.execute(
            "UPDATE loans SET due_at=?, returned_at=?, renewals=?, renewal_requested=? WHERE id=?",
            (loan.due_at.isoformat(), loan.returned_at.isoformat() if loan.returned_at else None,
             loan.renewals, int(loan.renewal_requested), loan.id),
        )
        self.conn.commit()

    def count_open(self, user_id):
        return self.conn.execute(
            "SELECT COUNT(*) FROM loans WHERE user_id = ? AND returned_at IS NULL", (user_id,)
        ).fetchone()[0]

    def has_open_for_book(self, user_id, book_id):
        return self.conn.execute(
            """SELECT 1 FROM loans l JOIN copies c ON c.id = l.copy_id
               WHERE l.user_id = ? AND c.book_id = ? AND l.returned_at IS NULL""",
            (user_id, book_id),
        ).fetchone() is not None

    def list_view(self, view, today):
        order = "l.returned_at DESC" if view == "historico" else "l.due_at"
        return self.conn.execute(
            _LOAN_SELECT + f"WHERE {_VIEWS[view]} ORDER BY {order}", {"today": today.isoformat()}
        ).fetchall()

    def by_user(self, user_id):
        return self.conn.execute(
            _LOAN_SELECT + "WHERE l.user_id = ? ORDER BY l.returned_at IS NOT NULL, l.due_at DESC", (user_id,)
        ).fetchall()


class ReservationRepository:
    OPEN = ("PENDENTE", "NOTIFICADA")

    def __init__(self, conn):
        self.conn = conn

    def add(self, user_id, book_id):
        self.conn.execute("INSERT INTO reservations(user_id, book_id) VALUES (?,?)", (user_id, book_id))
        self.conn.commit()

    def has_open(self, user_id, book_id):
        return self.conn.execute(
            "SELECT 1 FROM reservations WHERE user_id=? AND book_id=? AND status IN ('PENDENTE','NOTIFICADA')",
            (user_id, book_id),
        ).fetchone() is not None

    def next_pending(self, book_id):
        return self.conn.execute(
            "SELECT * FROM reservations WHERE book_id=? AND status='PENDENTE' ORDER BY created_at, id LIMIT 1",
            (book_id,),
        ).fetchone()

    def set_status(self, reservation_id, status):
        self.conn.execute("UPDATE reservations SET status=? WHERE id=?", (status, reservation_id))
        self.conn.commit()

    def mark_attended(self, user_id, book_id):
        self.conn.execute(
            "UPDATE reservations SET status='ATENDIDA' WHERE user_id=? AND book_id=? AND status IN ('PENDENTE','NOTIFICADA')",
            (user_id, book_id),
        )
        self.conn.commit()

    def for_user(self, user_id):
        return self.conn.execute(
            """SELECT r.*, b.title FROM reservations r JOIN books b ON b.id = r.book_id
               WHERE r.user_id=? AND r.status IN ('PENDENTE','NOTIFICADA') ORDER BY r.created_at""",
            (user_id,),
        ).fetchall()


class FineRepository:
    def __init__(self, conn):
        self.conn = conn

    def upsert(self, loan_id, amount):
        self.conn.execute(
            """INSERT INTO fines(loan_id, amount) VALUES (?,?)
               ON CONFLICT(loan_id) DO UPDATE SET amount = excluded.amount WHERE fines.status = 'ABERTA'""",
            (loan_id, amount),
        )
        self.conn.commit()

    def get_by_loan(self, loan_id):
        return self.conn.execute("SELECT * FROM fines WHERE loan_id=?", (loan_id,)).fetchone()

    def pay(self, fine_id):
        cur = self.conn.execute(
            "UPDATE fines SET status='PAGA', paid_at=CURRENT_TIMESTAMP WHERE id=? AND status='ABERTA'", (fine_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def open_total(self, user_id=None):
        sql = "SELECT COALESCE(SUM(f.amount),0) FROM fines f JOIN loans l ON l.id=f.loan_id WHERE f.status='ABERTA'"
        args = ()
        if user_id is not None:
            sql, args = sql + " AND l.user_id=?", (user_id,)
        return self.conn.execute(sql, args).fetchone()[0]
