# bmk's own supply-chain cooldown for its shared tool env: uv flags, regenerated from bmk's
# [tool.uv] on every release. `bmk install` deploys it beside the Makefile, which includes it.
# Do not edit; commit it with the Makefile.
BMK_COOLDOWN := --exclude-newer "7 days" --exclude-newer-package bmk=false --exclude-newer-package btx-lib-mail=false --exclude-newer-package lib-cli-exit-tools=false --exclude-newer-package lib-layered-config=false --exclude-newer-package lib-log-rich=false
