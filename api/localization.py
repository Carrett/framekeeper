from flask import request


def text(spanish, english):
    preferred = request.headers.get("Accept-Language", "").split(",", 1)[0].lower()
    return spanish if preferred.startswith("es") else english
