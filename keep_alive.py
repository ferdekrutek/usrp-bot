"""
keep_alive.py

Render (na darmowym planie Web Service) wymaga, zeby proces nasluchiwal
na porcie HTTP - inaczej uzna deployment za nieudany. Ten maly serwer
Flask spelnia ten wymog i jednoczesnie daje adres, ktory mozna pingowac
(np. UptimeRobotem co 5 minut), zeby bot nie usypial po 15 minutach
bezczynnosci na darmowym planie.

Jesli hostujesz bota na platnym planie Render jako "Background Worker",
ten plik jest zbedny (worker nie wymaga nasluchiwania na porcie).
"""

import os
import threading

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot dziala."


def _run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def run_keep_alive():
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
