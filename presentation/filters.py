from datetime import date

PROFILE_LABELS = {"ALUNO": "Aluno", "PROFESSOR": "Professor", "ADMIN": "Bibliotecário"}


def br_date(value):
    if not value:
        return "—"
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    return value.strftime("%d/%m/%Y")


def brl(value):
    return "R$ " + f"{value or 0:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def hue(text):
    """Matiz estável por categoria para as capas geradas em CSS."""
    return sum(map(ord, text or "")) * 37 % 360


def register(app):
    app.jinja_env.filters.update(br_date=br_date, brl=brl, hue=hue, profile=lambda p: PROFILE_LABELS.get(p, p))
