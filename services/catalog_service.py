from services.errors import BusinessError

MANUAL_STATUSES = ("DISPONIVEL", "DANIFICADO", "EXTRAVIADO")


class CatalogService:
    def __init__(self, books):
        self.books = books

    def search(self, q="", category=""):
        return self.books.search(q.strip(), category)

    def categories(self):
        return self.books.categories()

    def detail(self, book_id):
        book = self.books.get(book_id)
        if not book:
            raise BusinessError("Livro não encontrado.")
        return {"book": book, "copies": self.books.copies_of(book_id)}

    def add_book(self, title, author, category, isbn, year, copies=1):
        return self.books.add_book(title, author, category, isbn, year, copies)

    def set_copy_status(self, copy_id, status):
        copy = self.books.copy(copy_id)
        if not copy or status not in MANUAL_STATUSES:
            raise BusinessError("Alteração de exemplar inválida.")
        if copy["status"] in ("EMPRESTADO", "RESERVADO"):
            raise BusinessError("Exemplar em circulação: registre a devolução antes de alterar o status.")
        self.books.set_copy_status(copy_id, status)
