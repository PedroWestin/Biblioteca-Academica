import unittest
from datetime import date, timedelta

from database.db import connect, init_schema
from factories.loan_factory import (ProfessorLoanFactory, StudentLoanFactory, loan_factory_for)
from models.loan import ProfessorLoan, StudentLoan
from services.container import build_services
from services.errors import BusinessError

T = date(2026, 3, 2)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        conn = connect(":memory:")
        init_schema(conn)
        self.s = build_services(conn)
        self.ana = self.s.auth.register("Ana Lima", "ana@x.edu", "123456", "ALUNO")
        self.beto = self.s.auth.register("Beto Dias", "beto@x.edu", "123456", "ALUNO")
        self.prof = self.s.auth.register("Prof Cruz", "cruz@x.edu", "123456", "PROFESSOR")
        self.book = self.s.catalog.add_book("Livro A", "Autor", "Computação", "111", 2020, copies=1)

    def test_factory_method_cria_produto_por_perfil(self):
        self.assertIsInstance(loan_factory_for("ALUNO"), StudentLoanFactory)
        self.assertIsInstance(loan_factory_for("PROFESSOR"), ProfessorLoanFactory)
        a, p = loan_factory_for("ALUNO").issue(1, 1, T), loan_factory_for("PROFESSOR").issue(1, 1, T)
        self.assertIsInstance(a, StudentLoan)
        self.assertIsInstance(p, ProfessorLoan)
        self.assertEqual((a.due_at - T).days, 14)
        self.assertEqual((p.due_at - T).days, 30)

    def test_multa_depende_do_tipo_de_emprestimo(self):
        a, p = loan_factory_for("ALUNO").issue(1, 1, T), loan_factory_for("PROFESSOR").issue(1, 1, T)
        self.assertEqual(a.fine(a.due_at + timedelta(days=4)), 4.00)
        self.assertEqual(p.fine(p.due_at + timedelta(days=4)), 2.00)

    def test_fluxo_emprestimo_reserva_devolucao_e_multa(self):
        kind, loan = self.s.loans.request(self.ana, self.book, T)
        self.assertEqual(kind, "EMPRESTIMO")
        self.assertEqual(self.s.loans.request(self.beto, self.book, T)[0], "RESERVA")
        fine = self.s.loans.return_loan(loan.id, today=loan.due_at + timedelta(days=3))
        self.assertEqual(fine, 3.00)
        self.assertEqual(self.s.catalog.detail(self.book)["copies"][0]["status"], "RESERVADO")
        with self.assertRaises(BusinessError):                       # multa aberta bloqueia novos pedidos
            self.s.loans.request(self.ana, self.book, T)
        self.assertEqual(self.s.loans.request(self.beto, self.book, T)[0], "EMPRESTIMO")  # exemplar separado para Beto

    def test_limite_de_emprestimos_do_aluno(self):
        ids = [self.s.catalog.add_book(f"L{i}", "A", "X", f"9{i}", 2020, 1) for i in range(4)]
        for b in ids[:3]:
            self.s.loans.request(self.ana, b, T)
        with self.assertRaises(BusinessError):
            self.s.loans.request(self.ana, ids[3], T)

    def test_renovacao_pedida_e_aprovada(self):
        _, loan = self.s.loans.request(self.ana, self.book, T)
        self.s.loans.request_renewal(self.ana, loan.id, T)
        self.assertEqual(len(self.s.loans.admin_overview("renovacoes", T)["rows"]), 1)
        self.s.loans.approve_renewal(loan.id, T)
        row = self.s.loans.admin_overview("ativos", T)["rows"][0]
        self.assertEqual((row["renewals"], row["due_at"]), (1, (loan.due_at + timedelta(days=14)).isoformat()))


if __name__ == "__main__":
    unittest.main()
