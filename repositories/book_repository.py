_SELECT = """
SELECT b.*, COUNT(c.id) AS total,
       COALESCE(SUM(c.status = 'DISPONIVEL'), 0) AS available,
       (SELECT COUNT(*) FROM reservations r
         WHERE r.book_id = b.id AND r.status IN ('PENDENTE','NOTIFICADA')) AS queue
FROM books b LEFT JOIN copies c ON c.book_id = b.id
"""


class BookRepository:
    def __init__(self, conn):
        self.conn = conn

    def search(self, q="", category=""):
        return self.conn.execute(
            _SELECT + """WHERE (:q = '' OR b.title LIKE :like OR b.author LIKE :like OR b.isbn LIKE :like)
                           AND (:cat = '' OR b.category = :cat)
                         GROUP BY b.id ORDER BY b.title""",
            {"q": q, "like": f"%{q}%", "cat": category},
        ).fetchall()

    def get(self, book_id):
        return self.conn.execute(_SELECT + "WHERE b.id = ? GROUP BY b.id", (book_id,)).fetchone()

    def categories(self):
        return [r[0] for r in self.conn.execute("SELECT DISTINCT category FROM books ORDER BY category")]

    def copies_of(self, book_id):
        return self.conn.execute("SELECT * FROM copies WHERE book_id = ? ORDER BY code", (book_id,)).fetchall()

    def copy(self, copy_id):
        return self.conn.execute("SELECT * FROM copies WHERE id = ?", (copy_id,)).fetchone()

    def add_book(self, title, author, category, isbn, year, copies=1):
        cur = self.conn.execute(
            "INSERT INTO books(title, author, category, isbn, year) VALUES (?,?,?,?,?)",
            (title, author, category, isbn, year),
        )
        self.add_copies(cur.lastrowid, copies)
        return cur.lastrowid

    def add_copies(self, book_id, n):
        start = self.conn.execute("SELECT COUNT(*) FROM copies WHERE book_id = ?", (book_id,)).fetchone()[0]
        for i in range(start + 1, start + n + 1):
            self.conn.execute("INSERT INTO copies(book_id, code) VALUES (?,?)", (book_id, f"L{book_id:04d}-{i:02d}"))
        self.conn.commit()

    def find_available_copy(self, book_id, user_id):
        """Exemplar livre, ou exemplar separado (RESERVADO) para quem foi notificado na fila."""
        return self.conn.execute(
            """SELECT c.* FROM copies c
               WHERE c.book_id = ? AND (c.status = 'DISPONIVEL' OR (c.status = 'RESERVADO' AND EXISTS (
                     SELECT 1 FROM reservations r
                      WHERE r.book_id = c.book_id AND r.user_id = ? AND r.status = 'NOTIFICADA')))
               ORDER BY c.status LIMIT 1""",
            (book_id, user_id),
        ).fetchone()

    def set_copy_status(self, copy_id, status):
        self.conn.execute("UPDATE copies SET status = ? WHERE id = ?", (status, copy_id))
        self.conn.commit()
