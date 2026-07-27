black -l 120 app/ app-auth/
ruff check app/ app-auth/ --fix --line-length=120 --extend-select I