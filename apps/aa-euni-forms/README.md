# aa-euni-forms

A native **forms / surveys** app for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth),
built for EVE University to replace the patchwork of Google Forms + Sheets + Discord-posting
scripts.

## Why

- **Verified identity for free.** Every Auth account is EVE-SSO-verified and has all of the
  user's characters linked to it. Forms can offer a picker of the submitter's *actually
  verified* alts — no more "this is my alt, trust me bro".
- **Access by role, not by email list.** Who can fill a form and who can read responses is
  controlled by Django **Groups** (the roles Auth already uses). Leavers lose access
  automatically — nothing to maintain per-form.
- **Results stay in Auth.** Reviewers read responses in-app and export CSV. Auth's built-in
  notification system pings them on submission (a synchronous DB write — no Celery, nothing to
  fail silently like the old Discord scripts).
- **Consistent branding for free** — extends Auth's themed base template.

## Features

- Directors (anyone with the `manage_forms` permission) build forms in the Auth UI.
- Field types: short text, long text, single-choice, multiple-choice, number, date, yes/no,
  and a **verified EVE character picker**.
- Per-form access control: `restricted_groups` (who can fill) and `viewer_groups` (who can read
  responses). Empty `restricted_groups` ⇒ any logged-in user may fill.
- Form lifecycle: Draft → Open → Closed. Only Open forms accept submissions.
- Always-attributed responses (submitting account + main character, snapshotted at submit time).
- Response list + CSV export for viewers. Bell notification to viewers on submission.

## Permissions

| Permission | Grants |
|------------|--------|
| `euniforms.basic_access` | See the Forms menu and fill forms you're eligible for. Grant to your Member/Student group. |
| `euniforms.manage_forms` | Create, edit and delete forms, and view all responses. Grant to Directors. |

Per-form `viewer_groups` additionally grant response-viewing for that one form without
`manage_forms`.

## Installation (production)

Each release is published to **GitHub Releases** with the built wheel + sdist
attached. Install a specific version straight from the git tag:

```bash
pip install "aa-euni-forms @ git+https://github.com/EVE-University/aa-euni-forms@v0.1.0"
```

(or download the `.whl` asset from the release and `pip install` it.)

Then add `"euniforms"` to `INSTALLED_APPS` in your auth settings and run:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Restart Auth (and Celery), then grant the permissions: `euniforms.basic_access`
to your member group and `euniforms.manage_forms` to Directors.

This package is developed in the [euni-aa-dev](https://github.com/EVE-University/euni-aa-dev)
Docker dev environment — see that repo for the editable-install dev workflow.

## Releasing

Releases are cut by a **manual** GitHub Actions workflow
(`.github/workflows/release.yml`) — nothing publishes automatically on push.

1. Go to **Actions → Release → Run workflow**.
2. Enter the new version (e.g. `0.1.1`, without the leading `v`) and run it.

The workflow then:

- bumps `__version__` in `euniforms/__init__.py` and commits it to `main`,
- creates and pushes the `v<version>` tag,
- builds and validates the sdist + wheel,
- publishes a GitHub Release for that tag with auto-generated notes and the
  build attached as assets.

It refuses to run if the tag already exists, so pick a fresh version each time.
Because it pushes the version-bump commit directly to `main`, `main` must allow
the `github-actions` bot to push (relax branch protection or supply a PAT if
your `main` is protected).
