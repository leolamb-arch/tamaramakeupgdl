import os
import sys


def reset_access():
    password = os.environ.get("TAMARA_RESET_PASSWORD", "")
    if not password:
        print("Recuperación desactivada.")
        return

    user = os.environ.get("TAMARA_ADMIN_USER", "").strip()
    if not user or len(user) > 100:
        raise SystemExit("Revisa TAMARA_ADMIN_USER.")

    if not 14 <= len(password) <= 1024:
        raise SystemExit(
            "La contraseña nueva debe tener entre 14 y 1024 caracteres."
        )

    if not os.environ.get("DATABASE_URL", "").strip():
        raise SystemExit("Falta DATABASE_URL. No se cambió la contraseña.")

    from app import create_app, PH
    from argon2.exceptions import VerificationError, InvalidHashError

    # Evita crear otra cuenta durante la recuperación.
    previous = {
        key: os.environ.pop(key, None)
        for key in ("TAMARA_ADMIN_USER", "TAMARA_ADMIN_PASSWORD")
    }
    try:
        app = create_app()
    finally:
        for key, value in previous.items():
            if value is not None:
                os.environ[key] = value

    if not app.config.get("DATABASE_URL"):
        raise SystemExit(
            "Esta versión todavía usa SQLite. Recuperación cancelada."
        )

    with app.db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT password FROM admins WHERE name=?",
            (user,),
        ).fetchone()

        if row is None:
            raise SystemExit(
                "Ese usuario no existe en esta base. No se cambió ninguna cuenta."
            )

        try:
            already_set = PH.verify(row["password"], password)
        except (VerificationError, InvalidHashError):
            already_set = False

        if not already_set:
            connection.execute(
                "UPDATE admins SET password=? WHERE name=?",
                (PH.hash(password), user),
            )
            connection.execute(
                "DELETE FROM sessions WHERE user=?",
                (user,),
            )
            connection.execute("DELETE FROM attempts")

    print(
        "Acceso recuperado. Elimina TAMARA_RESET_PASSWORD "
        "después de comprobar que puedes entrar."
    )


if __name__ == "__main__":
    try:
        reset_access()
    except Exception:
        print(
            "No se pudo recuperar el acceso. "
            "Revisa la conexión y la versión desplegada.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
