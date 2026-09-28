import argparse
import os
import getpass
from pathlib import Path
from app import create_app, PH
from tamara.services.backups import backup, restore


def main():
    parser = argparse.ArgumentParser(description="Administración local de Tamara")
    parser.add_argument(
        "command",
        choices=["serve", "create-admin", "reset-password", "backup", "restore-backup"],
    )
    parser.add_argument("--user")
    parser.add_argument("--path")
    args = parser.parse_args()
    app = create_app()
    if args.command in ["create-admin", "reset-password"]:
        user = args.user or input("Usuario administrador: ").strip()
        if not user or len(user) > 100:
            raise SystemExit("Usuario inválido.")
        password = getpass.getpass("Contraseña nueva (mínimo 14 caracteres): ")
        if (
            len(password) < 14
            or len(password) > 1024
            or password != getpass.getpass("Repite la contraseña: ")
        ):
            raise SystemExit("Contraseña corta o confirmación distinta.")
        with app.db() as c:
            exists = c.execute("SELECT 1 FROM admins WHERE name=?", (user,)).fetchone()
            if args.command == "create-admin":
                if c.execute("SELECT 1 FROM admins").fetchone():
                    raise SystemExit(
                        "Ya existe un administrador. Usa reset-password para recuperar el acceso."
                    )
                c.execute("INSERT INTO admins VALUES(?,?)", (user, PH.hash(password)))
            else:
                if not exists:
                    raise SystemExit("El usuario no existe.")
                c.execute(
                    "UPDATE admins SET password=? WHERE name=?",
                    (PH.hash(password), user),
                )
                c.execute("DELETE FROM sessions WHERE user=?", (user,))
                c.execute("DELETE FROM attempts")
        print("Acceso actualizado. No se guardó la contraseña en texto plano.")
    elif args.command == "serve":
        from waitress import serve
        from urllib.parse import urlsplit

        origin = app.config["ORIGIN"]
        port = int(os.environ.get("PORT", urlsplit(origin).port or 8765))
        print("Tamara disponible en " + origin, flush=True)
        serve(
            app,
            host="127.0.0.1",
            port=port,
            threads=4,
            max_request_body_size=9 * 1024 * 1024,
        )
    else:
        if not args.path:
            raise SystemExit("Indica --path con una carpeta de copia de seguridad.")
        target = Path(args.path).resolve()
        data = app.config["DATA_DIR"]
        if target == data or data in target.parents or target in data.parents:
            raise SystemExit("La copia debe estar fuera de DATA_DIR y no contenerlo.")
        if args.command == "backup":
            backup(app, target)
            print(
                "Copia privada creada. Protégela: contiene el hash del administrador y los borradores."
            )
        else:
            if (
                not (target / "content.sqlite").is_file()
                or not (target / "uploads").is_dir()
            ):
                raise SystemExit("Copia incompleta.")
            if (
                input(
                    "Detén el servidor. Escribe RESTAURAR para reemplazar los datos: "
                )
                != "RESTAURAR"
            ):
                raise SystemExit("Cancelado.")
            restore(app, target)
            print("Datos restaurados; las sesiones anteriores fueron revocadas.")


if __name__ == "__main__":
    main()
