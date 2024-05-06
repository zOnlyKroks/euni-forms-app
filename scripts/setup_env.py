#!/usr/bin/env python3

import argparse
import os
import random
import string

DEFAULT_ENV = {
    # Docker Host (Does this break on non-linux hosts?)
    "DOCKER_HOST_UID": os.getuid(),
    "DOCKER_HOST_GID": os.getgid(),
    # Python
    "PIP_INDEX_URL": "https://pypi.eveuniversity.org",
    # Alliance Auth
    "AA_DEBUG": True,
    "AA_SECRET_KEY": "",
    "AA_SITE_NAME": "E-Uni Local Dev",
    "AA_SITE_URL": "http://localhost:8000",
    # Alliance Auth DB
    "AA_DB_HOST": "mariadb",
    "AA_DB_NAME": "aauth",
    "AA_DB_USER": "aauth",
    "AA_DB_PASSWORD": "",
    "AA_DB_ROOT_PASSWORD": "",
    "AA_DB_CHARSET": "utf8mb4",
    # Alliance Auth Email
    "AA_EMAIL_HOST": "",
    "AA_EMAIL_PORT": 587,
    "AA_EMAIL_USER": "",
    "AA_EMAIL_PASSWORD": "",
    "AA_EMAIL_USE_TLS": True,
    "AA_EMAIL_DEFAULT_FROM": "",
    # Alliance Auth ESI SSO
    "ESI_SSO_CLIENT_ID": "",
    "ESI_SSO_CLIENT_SECRET": "",
    "ESI_USER_CONTACT_EMAIL": "",
}

PROJECT_ROOT = (
    os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + "/../") + "/"
)

DOTENV_SOURCE = ".env.example"
DOTENV_DEST = ".env"

INIT_SQL_SOURCE = "mysql/initdb.d/init.sql.example"
INIT_SQL_DEST = "mysql/initdb.d/init.sql"


def _gen_random_pass(len):
    chars = string.ascii_letters + string.digits

    return "".join(random.choice(chars) for i in range(len))


def _parse_args():
    parser = argparse.ArgumentParser(description="E-Uni AA Dev Env Setup")

    # General
    parser.add_argument(
        "-i",
        "--interactive",
        default=False,
        action="store_true",
        help="Interactive Setup Mode",
    )

    parser.add_argument(
        "-w",
        "--overwrite",
        default=False,
        action="store_true",
        help="Force overwrite existing environment",
    )

    # Docker Host
    docker_parser = parser.add_argument_group("Docker Host")
    docker_parser.add_argument(
        "--docker-host-uid",
        metavar="UID",
        type=int,
        default=DEFAULT_ENV["DOCKER_HOST_UID"],
        help="User ID of the user from Docker Host",
    )

    docker_parser.add_argument(
        "--docker-host-gid",
        metavar="GID",
        type=int,
        default=DEFAULT_ENV["DOCKER_HOST_GID"],
        help="Group ID of the user from Docker Host",
    )

    # Python
    python_parser = parser.add_argument_group("Python/PIP")
    python_parser.add_argument(
        "--pip-index-url",
        metavar="PIP Index URL",
        type=str,
        default=DEFAULT_ENV["PIP_INDEX_URL"],
        help="URL of PyPi index to use",
    )

    # Alliance Auth
    aa_parser = parser.add_argument_group("Alliance Auth")
    aa_parser.add_argument(
        "--aa-debug",
        action="store_true",
        default=True,
        help="Alliance Auth Debug On",
    )
    aa_parser.add_argument(
        "--no-aa-debug",
        action="store_false",
        dest="aa_debug",
        help="Alliance Auth Debug Off",
    )
    aa_parser.add_argument(
        "--aa-secret-key",
        metavar="AA Secret Key",
        type=str,
        default=DEFAULT_ENV["AA_SECRET_KEY"],
        help="Alliance Auth Secret Key",
    )
    aa_parser.add_argument(
        "--aa-site-name",
        metavar="AA Site Name",
        type=str,
        default=DEFAULT_ENV["AA_SITE_NAME"],
        help="Alliance Auth Site Name",
    )
    aa_parser.add_argument(
        "--aa-site-url",
        metavar="AA Site URL",
        type=str,
        default=DEFAULT_ENV["AA_SITE_URL"],
        help="Alliance Auth Site URL",
    )

    # Alliance Auth DB
    db_parser = parser.add_argument_group("Alliance Auth Database")
    db_parser.add_argument(
        "--aa-db-host",
        metavar="Hostname",
        type=str,
        default=DEFAULT_ENV["AA_DB_HOST"],
        help="Alliance Auth Database Host",
    )

    db_parser.add_argument(
        "--aa-db-name",
        metavar="Database Name",
        type=str,
        default=DEFAULT_ENV["AA_DB_NAME"],
        help="Alliance Auth Database Name",
    )

    db_parser.add_argument(
        "--aa-db-user",
        metavar="User",
        type=str,
        default=DEFAULT_ENV["AA_DB_USER"],
        help="Alliance Auth Database User",
    )

    db_parser.add_argument(
        "--aa-db-password",
        metavar="Password",
        type=str,
        default=DEFAULT_ENV["AA_DB_PASSWORD"],
        help="Alliance Auth Database Password",
    )

    db_parser.add_argument(
        "--aa-db-root-password",
        metavar="Root Password",
        type=str,
        default=DEFAULT_ENV["AA_DB_ROOT_PASSWORD"],
        help="Alliance Auth Database Root Password",
    )

    db_parser.add_argument(
        "--aa-db-charset",
        metavar="Charset",
        type=str,
        default=DEFAULT_ENV["AA_DB_CHARSET"],
        help="Alliance Auth Database Character Set",
    )

    # Alliance Auth Email
    email_parser = parser.add_argument_group("Alliance Auth Email")
    email_parser.add_argument(
        "--aa-email-host",
        metavar="Hostname",
        type=str,
        default=DEFAULT_ENV["AA_EMAIL_HOST"],
        help="Alliance Auth Email Host",
    )

    email_parser.add_argument(
        "--aa-email-port",
        metavar="Port",
        type=int,
        default=DEFAULT_ENV["AA_EMAIL_PORT"],
        help="Alliance Auth Email Port",
    )

    email_parser.add_argument(
        "--aa-email-user",
        metavar="User",
        type=str,
        default=DEFAULT_ENV["AA_EMAIL_USER"],
        help="Alliance Auth Email User",
    )

    email_parser.add_argument(
        "--aa-email-password",
        metavar="Password",
        type=str,
        default=DEFAULT_ENV["AA_EMAIL_PASSWORD"],
        help="Alliance Auth Email Password",
    )

    email_parser.add_argument(
        "--aa-email-use_tls",
        metavar="True/False",
        type=bool,
        default=DEFAULT_ENV["AA_EMAIL_USE_TLS"],
        help="Alliance Auth Email Use TLS",
    )

    email_parser.add_argument(
        "--aa-email-default-from",
        metavar="Email",
        type=str,
        default=DEFAULT_ENV["AA_EMAIL_DEFAULT_FROM"],
        help="Alliance Auth Email Default From",
    )

    # ESI SSO
    esi_parser = parser.add_argument_group("ESI SSO")
    esi_parser.add_argument(
        "--esi-sso-client-id",
        metavar="Client ID",
        type=str,
        default=DEFAULT_ENV["ESI_SSO_CLIENT_ID"],
        help="ESI SSO Client ID",
    )

    esi_parser.add_argument(
        "--esi-sso-client-secret",
        metavar="Client Secret",
        type=str,
        default=DEFAULT_ENV["ESI_SSO_CLIENT_SECRET"],
        help="ESI SSO Client Secret",
    )

    esi_parser.add_argument(
        "--esi-user-contact-email",
        metavar="Contact Email",
        type=str,
        default=DEFAULT_ENV["ESI_USER_CONTACT_EMAIL"],
        help="ESI App Contact Email",
    )

    return parser.parse_args()


def _create_env_from_args(args):
    args_env = {}

    for key, value in vars(args).items():
        if key in ["interactive", "overwrite"]:
            continue

        # Remove excess or only whitespace from strings
        if isinstance(value, str):
            value = value.strip()

        args_env[key.upper()] = value

    return {**DEFAULT_ENV, **args_env}


def _is_env_default(env, name):
    return env[name] == DEFAULT_ENV[name]


def _handle_retry_input(prompt, expected_type, allow_empty=False):
    if expected_type not in [str, int, bool]:
        raise ValueError("type must be str, int, or bool types")

    while True:
        try:
            val = expected_type(input(prompt))
        except KeyboardInterrupt:
            print("\nInteractive Mode Aborted")
            exit()
        except ValueError:
            print(f"Invalid value, expected: {expected_type.__name__}")
            continue

        if isinstance(val, str):
            val = val.strip()

            if val != "" or allow_empty:
                break
        else:
            break

    return val


def _handle_interactive(env):
    env = env.copy()

    print(
        "Interactive mode will prompt you to enter values for the important environment settings."
    )
    print(
        "You can just press enter on settings with a default noted inside [] brackets to use the default."
    )
    print(
        "Some settings which have reasonable defaults cannot be set here and must be included via command line options."
    )
    print("To exit interactive mode press Ctrl-C at any time.")

    if _is_env_default(env, "AA_SITE_NAME"):
        val = _handle_retry_input(
            f"Site Name [{env['AA_SITE_NAME']}]: ",
            str,
            True,
        )

        if val != "":
            env["AA_SITE_NAME"] = val

    # This does not verify if the URL is valid.
    if _is_env_default(env, "AA_SITE_URL"):
        val = _handle_retry_input(
            f"Site URL [{env['AA_SITE_URL']}]: ",
            str,
            True,
        )

        if val != "":
            env["AA_SITE_URL"] = val

    if _is_env_default(env, "AA_SECRET_KEY"):
        val = _handle_retry_input(f"Secret Key [Random Password]: ", str, True)

        if val == "":
            val = _gen_random_pass(24)

        env["AA_SECRET_KEY"] = val

    if _is_env_default(env, "AA_DB_HOST"):
        val = _handle_retry_input(
            f"DB Hostname [{env['AA_DB_HOST']}]: ",
            str,
            True,
        )
        if val != "":
            env["AA_DB_HOST"] = val

    if _is_env_default(env, "AA_DB_USER"):
        val = _handle_retry_input(
            f"DB Username [{env['AA_DB_USER']}]: ",
            str,
            True,
        )
        if val != "":
            env["AA_DB_USER"] = val

    if _is_env_default(env, "AA_DB_PASSWORD"):
        val = _handle_retry_input(f"DB Password [Random Password]: ", str, True)

        if val == "":
            val = _gen_random_pass(24)

        env["AA_DB_PASSWORD"] = val

    if _is_env_default(env, "AA_DB_ROOT_PASSWORD"):
        val = _handle_retry_input(f"DB Root Password [Random Password]: ", str, True)

        if val == "":
            val = _gen_random_pass(24)

        env["AA_DB_ROOT_PASSWORD"] = val

    print(
        """Alliance Auth requires an ESI Developer Application to be created through CCP's third party developer portal.

You can create a new application via: https://developers.eveonline.com/applications/create

This step is not optional.          
"""
    )

    if _is_env_default(env, "ESI_SSO_CLIENT_ID"):
        env["ESI_SSO_CLIENT_ID"] = _handle_retry_input(
            "ESI SSO Client ID [REQUIRED]: ", str
        )

    if _is_env_default(env, "ESI_SSO_CLIENT_SECRET"):
        env["ESI_SSO_CLIENT_SECRET"] = _handle_retry_input(
            "ESI SSO Client Secret [REQUIRED]: ", str
        )

    print(
        "You must supply a valid email for CCP to contact you, otherwise you risk being IP banned from ESI."
    )
    if _is_env_default(env, "ESI_USER_CONTACT_EMAIL"):
        env["ESI_USER_CONTACT_EMAIL"] = _handle_retry_input(
            "ESI User Contact Email [REQUIRED]: ", str
        )

    return env


# This method doesn't check the email settings, or fully validate the contents of settings.
def _validate_env(env):
    valid = True

    # AA
    if env["AA_DEBUG"] not in [True, False]:
        print("AA_DEBUG must be True or False")
        valid = False

    if env["AA_SECRET_KEY"] == "":
        print("AA_SECRET_KEY must not be empty")
        valid = False

    if env["AA_SITE_NAME"] == "":
        print("AA_SITE_NAME must not be empty")
        valid = False

    if env["AA_SITE_URL"] == "":
        print("AA_SITE_URL must not be empty")
        valid = False

    # DB
    if env["AA_DB_HOST"] == "":
        print("AA_DB_HOST must not be empty")
        valid = False

    if env["AA_DB_NAME"] == "":
        print("AA_DB_NAME must not be empty")
        valid = False

    if env["AA_DB_USER"] == "":
        print("AA_DB_USER must not be empty")
        valid = False

    if env["AA_DB_PASSWORD"] == "":
        print("AA_DB_PASSWORD must not be empty")
        valid = False

    if env["AA_DB_ROOT_PASSWORD"] == "":
        print("AA_DB_ROOT_PASSWORD must not be empty")
        valid = False

    if env["AA_DB_CHARSET"] == "":
        print("AA_DB_CHARSET must not be empty")
        valid = False

    # ESI SSO
    if env["ESI_SSO_CLIENT_ID"] == "":
        print("ESI_SSO_CLIENT_ID must not be empty")
        valid = False

    if env["ESI_SSO_CLIENT_SECRET"] == "":
        print("ESI_SSO_CLIENT_SECRET must not be empty")
        valid = False

    if env["ESI_USER_CONTACT_EMAIL"] == "":
        print("ESI_USER_CONTACT_EMAIL must not be empty")
        valid = False

    return valid


def _write_env(env, overwrite=False):
    # Check to see if the environment is already setup if force=False
    if not overwrite:
        if os.path.exists(PROJECT_ROOT + DOTENV_DEST):
            print(
                "The .env file already exists in your environment. Please delete it or use --overwrite flag to overwrite."
            )
            exit()
        if os.path.exists(PROJECT_ROOT + INIT_SQL_DEST):
            print(
                "The mysql/initdb.d/init.sql file already exists in you're environment. Please delete it or use --overwrite flag to overwrite."
            )
            exit()

    # Write out .env
    with open(PROJECT_ROOT + DOTENV_SOURCE, "r", encoding="utf-8") as in_file, open(
        PROJECT_ROOT + DOTENV_DEST, "w", encoding="utf-8"
    ) as out_file:
        content = in_file.read()

        for key, value in env.items():
            placeholder = "%" + key + "%"
            if isinstance(value, int):
                out_value = str(value)
            elif isinstance(value, bool):
                out_value = "'" + {str(bool)} + "'"
            elif isinstance(value, str):
                # This isn't completely safe... or foolproof, but hey, no externals.
                # Naturally this likely has issues in Windows environments.
                if "'" in value:
                    out_value = (
                        '"'
                        + value.replace("\\", "\\\\")
                        .replace('"', '\\"')
                        .replace("$", "\\$")
                        + '"'
                    )
                else:
                    out_value = "'" + value + "'"
            else:
                print(f"{key}: Unknown Type: {type(value)}")

            content = content.replace(placeholder, out_value)

        out_file.write(content)

    # Write out init.sql
    with open(PROJECT_ROOT + INIT_SQL_SOURCE, "r", encoding="utf-8") as in_file, open(
        PROJECT_ROOT + INIT_SQL_DEST, "w", encoding="utf-8"
    ) as out_file:
        content = in_file.read()

        out_user = (
            "'" + env["AA_DB_USER"].replace("\\", "\\\\").replace("'", "\\'") + "'"
        )
        out_pass = (
            "'" + env["AA_DB_PASSWORD"].replace("\\", "\\\\").replace("'", "\\'") + "'"
        )
        out_name = "`" + env["AA_DB_NAME"].replace("`", "``") + "`"
        out_charset = "`" + env["AA_DB_CHARSET"].replace("`", "``") + "`"

        content = content.replace("%AA_DB_USER%", out_user)
        content = content.replace("%AA_DB_PASSWORD%", out_pass)
        content = content.replace("%AA_DB_NAME%", out_name)
        content = content.replace("%AA_DB_CHARSET%", out_charset)

        out_file.write(content)


def _print_env_summary(env):
    print("\n\nEnvironment Settings Summary\n")

    print(f"Docker UID:GID: {env['DOCKER_HOST_UID']}:{env['DOCKER_HOST_GID']}")
    print("-----")
    print(f"Site Name: {env['AA_SITE_NAME']}")
    print(f"Site URL: {env['AA_SITE_URL']}")
    print(f"Secret Key: {env['AA_SECRET_KEY']}")
    print("-----")
    print(f"DB Host: {env['AA_DB_HOST']}")
    print(f"DB Name: {env['AA_DB_NAME']}")
    print(f"DB User: {env['AA_DB_USER']}")
    print(f"DB Password: {env['AA_DB_PASSWORD']}")
    print(f"DB Root Password: {env['AA_DB_ROOT_PASSWORD']}")
    print("-----")
    print(f"ESI Client ID: {env['ESI_SSO_CLIENT_ID']}")
    print(f"ESI Client Secret: {env['ESI_SSO_CLIENT_SECRET']}")
    print(f"ESI User Contact: {env['ESI_USER_CONTACT_EMAIL']}")
    print("\n\n")


def _main():
    args = _parse_args()

    env = _create_env_from_args(args)

    if args.interactive:
        env = _handle_interactive(env)

    if _validate_env(env):
        _print_env_summary(env)

        _write_env(env, args.overwrite)
    else:
        print("Environment settings failed validation, exiting.")


if __name__ == "__main__":
    _main()
