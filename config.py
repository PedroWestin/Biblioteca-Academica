import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("BIBLIOTECA_DB", os.path.join(BASE_DIR, "biblioteca.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
