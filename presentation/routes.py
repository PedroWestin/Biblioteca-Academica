"""Camada de Apresentação: rotas Flask. Só conversa com os serviços (nunca com SQL)."""
from functools import wraps

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from database.db import get_db
from presentation.filters import brl
from services.container import build_services
from services.errors import BusinessError
from services.loan_service import VIEWS

auth_bp = Blueprint("auth", __name__)
catalog_bp = Blueprint("catalog", __name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def svc():
    if "services" not in g:
        g.services = build_services(get_db())
    return g.services


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


# ── Autenticação ──────────────────────────────────────────────
@auth_bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = svc().auth.get(uid) if uid else None
    g.unread = svc().notifications.unread(g.user.id) if g.user else []


@auth_bp.route("/entrar", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user = svc().auth.login(request.form["email"], request.form["password"])
        except BusinessError as e:
            flash(str(e), "erro")
        else:
            session.clear()
            session["user_id"] = user.id
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin.loans" if user.is_admin else "catalog.index"))
    return render_template("auth.html", mode="login")


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        try:
            user = svc().auth.register(f["name"], f["email"], f["password"], f.get("profile", "ALUNO"))
        except BusinessError as e:
            flash(str(e), "erro")
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("catalog.index"))
    return render_template("auth.html", mode="register")


@auth_bp.post("/sair")
def logout():
    session.clear()
    return redirect(url_for("catalog.index"))


# ── Tela 1: catálogo e pedido de empréstimo/reserva ───────────
@catalog_bp.get("/")
def index():
    q, cat = request.args.get("q", "").strip(), request.args.get("categoria", "")
    return render_template("catalog.html", books=svc().catalog.search(q, cat),
                           categories=svc().catalog.categories(), q=q, categoria=cat)


@catalog_bp.get("/livros/<int:book_id>")
def book_detail(book_id):
    try:
        return render_template("book.html", **svc().catalog.detail(book_id))
    except BusinessError as e:
        flash(str(e), "erro")
        return redirect(url_for("catalog.index"))


@catalog_bp.post("/livros/<int:book_id>/solicitar")
@login_required
def request_book(book_id):
    try:
        kind, loan = svc().loans.request(g.user, book_id)
    except BusinessError as e:
        flash(str(e), "erro")
    else:
        flash(f"Empréstimo registrado. Devolva até {loan.due_at:%d/%m/%Y}." if kind == "EMPRESTIMO"
              else "Sem exemplar livre agora: você entrou na fila de reserva.", "ok")
    return redirect(url_for("catalog.index", q=request.form.get("q", ""), categoria=request.form.get("categoria", "")))


@catalog_bp.get("/meus-emprestimos")
@login_required
def my_loans():
    html = render_template("my_loans.html", **svc().loans.for_user(g.user.id))
    svc().notifications.mark_read(g.user.id)
    return html


@catalog_bp.post("/meus-emprestimos/<int:loan_id>/renovar")
@login_required
def request_renewal(loan_id):
    try:
        svc().loans.request_renewal(g.user, loan_id)
        flash("Pedido de renovação enviado ao bibliotecário.", "ok")
    except BusinessError as e:
        flash(str(e), "erro")
    return redirect(url_for("catalog.my_loans"))


@catalog_bp.post("/exemplares/<int:copy_id>/status")
@admin_required
def copy_status(copy_id):
    try:
        svc().catalog.set_copy_status(copy_id, request.form["status"])
        flash("Status do exemplar atualizado.", "ok")
    except BusinessError as e:
        flash(str(e), "erro")
    return redirect(url_for("catalog.book_detail", book_id=request.form["book_id"]))


# ── Tela 2: painel do administrador ───────────────────────────
def _do(action):
    try:
        flash(action(), "ok")
    except BusinessError as e:
        flash(str(e), "erro")
    return redirect(url_for("admin.loans", visao=request.form.get("visao", "ativos")))


@admin_bp.get("/emprestimos")
@admin_required
def loans():
    view = request.args.get("visao", "ativos")
    view = view if view in VIEWS else "ativos"
    return render_template("admin_loans.html", view=view, **svc().loans.admin_overview(view))


@admin_bp.post("/emprestimos/<int:loan_id>/devolver")
@admin_required
def give_back(loan_id):
    def run():
        fine = svc().loans.return_loan(loan_id)
        return f"Devolução registrada. Multa gerada: {brl(fine)}." if fine else "Devolução registrada."
    return _do(run)


@admin_bp.post("/emprestimos/<int:loan_id>/multa")
@admin_required
def calc_fine(loan_id):
    return _do(lambda: f"Multa calculada e leitor avisado: {brl(svc().loans.assess_fine(loan_id))}.")


@admin_bp.post("/emprestimos/<int:loan_id>/renovacao/<action>")
@admin_required
def renewal(loan_id, action):
    if action not in ("aprovar", "recusar"):
        abort(404)

    def run():
        if action == "aprovar":
            svc().loans.approve_renewal(loan_id)
            return "Renovação aprovada."
        svc().loans.reject_renewal(loan_id)
        return "Renovação recusada."
    return _do(run)


@admin_bp.post("/multas/<int:fine_id>/pagar")
@admin_required
def pay_fine(fine_id):
    def run():
        svc().fines.pay(fine_id)
        return "Pagamento da multa registrado."
    return _do(run)


@admin_bp.post("/lembretes")
@admin_required
def reminders():
    return _do(lambda: f"{svc().loans.send_reminders()} lembrete(s) enviado(s).")
