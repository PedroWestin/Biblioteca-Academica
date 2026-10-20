"""Popula o banco com usuários, acervo e alguns empréstimos de demonstração."""
from datetime import date, timedelta

import config
from database.db import connect, init_schema
from services.container import build_services

BOOKS = [  # título, autor, categoria, ISBN, ano, nº de exemplares
    ("Estruturas de Dados e Algoritmos", "Thomas H. Cormen", "Computação", "9788535236996", 2012, 2),
    ("Arquitetura Limpa", "Robert C. Martin", "Computação", "9788550804606", 2019, 1),
    ("Padrões de Projeto", "Erich Gamma et al.", "Computação", "9788573076103", 2007, 2),
    ("Cálculo, volume 1", "James Stewart", "Matemática", "9788522125838", 2016, 3),
    ("Álgebra Linear", "David C. Lay", "Matemática", "9788521622086", 2018, 1),
    ("Curso de Direito Constitucional", "Gilmar Mendes", "Direito", "9788553609307", 2020, 2),
    ("Introdução ao Direito Civil", "Caio Mário da Silva Pereira", "Direito", "9788530989330", 2022, 1),
    ("Fundamentos de Física, vol. 1", "Halliday e Resnick", "Física", "9788521630357", 2016, 2),
    ("Anatomia Humana Sistêmica", "Dângelo e Fattini", "Saúde", "9788538807209", 2011, 1),
    ("Dom Casmurro", "Machado de Assis", "Literatura", "9788535910663", 1899, 2),
    ("Grande Sertão: Veredas", "João Guimarães Rosa", "Literatura", "9788520925270", 1956, 1),
    ("Metodologia do Trabalho Científico", "Antônio Joaquim Severino", "Pesquisa", "9788524924484", 2017, 2),
]


def run():
    conn = connect(config.DATABASE)
    init_schema(conn)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        print("Banco já populado.")
        return
    s = build_services(conn)
    s.auth.create_admin("Marina Albuquerque", "admin@biblioteca.edu", "admin123")
    aluno = s.auth.register("Rafael Souza", "aluno@biblioteca.edu", "aluno123", "ALUNO")
    prof = s.auth.register("Helena Prado", "professor@biblioteca.edu", "prof123", "PROFESSOR")
    ids = [s.catalog.add_book(*b) for b in BOOKS]

    today = date.today()
    s.loans.request(aluno, ids[1], today - timedelta(days=20))   # atrasado (prazo do aluno: 14 dias)
    s.loans.request(aluno, ids[4], today - timedelta(days=3))    # em dia
    s.loans.request(prof, ids[6], today - timedelta(days=12))    # em dia; vai pedir renovação
    loan = s.loans.loans.by_user(prof.id)[0]
    s.loans.request_renewal(prof, loan["id"], today)
    print("Banco populado. Contas: admin@biblioteca.edu/admin123, aluno@biblioteca.edu/aluno123, professor@biblioteca.edu/prof123")


if __name__ == "__main__":
    run()
