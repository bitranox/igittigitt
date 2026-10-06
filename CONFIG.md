# Configuration

igittigitt is configured with [lib_layered_config](https://github.com/bitranox/lib_layered_config).
Settings are merged from several layers; later layers win:

```
bundled defaults -> app -> host -> user -> .env file -> environment variables -> --set
```

- **Inspect** the merged result (with provenance for each value): `igittigitt config`
- **Deploy** editable copies into the standard config directories: `igittigitt config-deploy`
- **Examples** to copy and edit: `igittigitt config-generate-examples`

## Where config files live

| Layer | Linux                                            | macOS                                                        |
|-------|--------------------------------------------------|--------------------------------------------------------------|
| app   | `/etc/xdg/igittigitt/config.*` (+ `config.d/*`)  | `/Library/Application Support/bitranox/igittigitt/config.*`  |
| user  | `~/.config/igittigitt/config.*` (+ `config.d/*`) | `~/Library/Application Support/bitranox/igittigitt/config.*` |

`.env` files (`SECTION__KEY=value`, found by searching upward from the working directory)
and environment variables (`IGITTIGITT___SECTION__KEY=value`) override the files. A single
value can be overridden per run with `--set SECTION.KEY=VALUE`.

Value coercion (in `.env` and the environment alike): an unquoted `true`/`false` -> bool,
`null`/`none` -> None, a number -> int/float only when it converts back to the same text (`007`
stays text), and a JSON array or object is parsed. Quote a `.env` value to keep it as text. A
list or table is that JSON written unquoted in `.env` (quoted for the shell in the environment),
or one key per entry (`LIB_LOG_RICH__SCRUB_PATTERNS__API_KEY=.+`); a comma-separated value is ONE
string, not a list.

A configuration file that cannot be loaded (invalid TOML, not UTF-8, unreadable) does not stop
every command. `config`, `check` and `filter`, which read the configuration, refuse with exit 78
and one line naming the file (`--traceback` adds the loader's traceback); `info`,
`config-deploy` (the command that replaces the broken file), `config-generate-examples` and
`--help` still run. A malformed or conflicting `--set` and an invalid `--profile` name are usage
errors (exit 2) for every command, whether or not the configuration loads.

## Settings reference

The authoritative, fully-commented reference is the set of bundled TOML files (one key per
documented block); `config-deploy` / `config-generate-examples` write them out:

- `defaultconfig.d/50-performance.toml` - the `[performance]` engine/CLI tuning knobs.
- `defaultconfig.d/90-logging.toml` - the `[lib_log_rich]` logging settings.
- `defaultconfig.d/40-layered-config.toml` - config-deploy permission defaults.

### `[performance]`

Only affects speed and cache memory, never which paths match. All defaults keep memory
bounded and were chosen by measurement.

| Key                 | Default   | Meaning                                                                                                               |
|---------------------|-----------|-----------------------------------------------------------------------------------------------------------------------|
| `dir_cache_max`     | `8192`    | Directory-decision LRU capacity per parser (`0` disables). Main speed-up on trees; memory `O(this)`, not `O(#files)`. |
| `pattern_cache_max` | `4096`    | Process-wide compiled-regex cache capacity (keyed by distinct pattern).                                               |
| `stdin_chunk_bytes` | `65536`   | Stdin read granularity for the streaming commands.                                                                    |
| `max_token_bytes`   | `1048576` | Per-token safety bound; a separator-less token larger than this is rejected, not buffered unbounded.                  |

```bash
igittigitt --set performance.dir_cache_max=32768 filter -C repo
IGITTIGITT___PERFORMANCE__MAX_TOKEN_BYTES=4096 igittigitt check -C repo --stdin < paths
```

### `[lib_layered_config.default_permissions]`

The Unix modes `config-deploy` gives the directories and files it writes (POSIX only), per layer:
`app_directory`/`app_file`, `host_directory`/`host_file`, `user_directory`/`user_file`, and
`enabled`. Built-in modes are 755/644 for app and host, 700/600 for user.

`config-deploy` decides none of this itself: it passes its options and any `--set` of this
section to lib_layered_config, which applies each target's own layer modes. The library reads the
section from the bundled defaults, the configuration files this deploy does not overwrite and the
environment, with the `--set` values laid over them. It never reads `.env` for it (neither one
found from the working directory nor an explicit `--env-file`), so a `.env` can neither change a
deployed mode nor block a deploy. `--dir-mode`/`--file-mode` override the configured modes for
every target. Without `--permissions`/`--no-permissions`, `enabled` decides; `enabled = false`
behaves like `--no-permissions`, and `--permissions` sets the modes anyway. `--no-permissions`
cannot be combined with a mode option (exit 2).

A mode is a plain octal STRING (`"0o750"`, `"750"`) inside 0..0o7777, never setuid/setgid/sticky,
group or world write, an execute bit on a file, or less than owner rwx (directory) / rw (file).
A bare integer is refused because TOML, the environment and `--set` all read `400` as the DECIMAL
number 400, which is `0o620`. Quote it in TOML (`user_file = "640"`); in an environment variable
or `--set` use the `0o` prefix (`0o640`). `enabled` must be a real boolean; `"no"`, `"off"`, `0`
or `1` are refused. An unknown key is refused rather than ignored. `--dir-mode`/`--file-mode`
follow the same rules and are refused as a usage error (exit 2). Any refused setting stops
`config-deploy` before it writes anything, with exit 78, one line per problem naming the key and
where it was set, and a hint, for example:

```text
Error: lib_layered_config.default_permissions.user_file: a bare integer is read as decimal (400 = 0o620); write the mode as an octal string: "0o640" (quoted) in a file, 0o640 in the environment or a runtime override (such as an application's --set) (source: env)
Hint: to deploy anyway, pass both --dir-mode and --file-mode (the built-in modes are 700 and 600 for user, 755 and 644 for app and host); --no-permissions also deploys, but leaves every mode to the umask, which can make a user file that holds secrets readable by other accounts.
```

A refused `--set` of the section names `(source: override)` and has no hint, since no option gets
past it: fix or drop the `--set`. The files a deploy writes are never read for it, so
`config-deploy --force` replaces a destination that carries a bad value, or does not parse at all,
without further options.

### `[lib_log_rich]`

Logging configuration (console level/theme, journald/eventlog/Graylog backends, queueing,
scrubbing, payload limits). Each key is documented inline in `90-logging.toml`. Common ones:

| Key                                   | Example                    | Meaning                                |
|---------------------------------------|----------------------------|----------------------------------------|
| `console_level`                       | `DEBUG`                    | Minimum level shown on the console.    |
| `console_theme`                       | `dark`                     | Console colour theme.                  |
| `enable_journald`                     | `true`                     | Also emit to systemd-journald (Linux). |
| `enable_graylog` / `graylog_endpoint` | `true` / `["host", 12201]` | Ship logs to Graylog (GELF).           |

```bash
igittigitt --set lib_log_rich.console_level=DEBUG info
IGITTIGITT___LIB_LOG_RICH__CONSOLE_LEVEL=DEBUG igittigitt info
```

lib_log_rich also reads its own `LOG_*` variables. Logging takes those, and only those, from a
`.env`: from `--env-file` when given, otherwise from the nearest `.env` from the working directory
up to the project root, never replacing a variable that is already set. No other `.env` line
reaches the process environment.

A `[lib_log_rich]` value or `LOG_*` variable lib_log_rich refuses (a wrong type, its own range
checks such as `queue_maxsize = 0`, or an unknown level such as `LOG_CONSOLE_LEVEL=bogus`) is a
configuration failure like a broken file: logging starts with its defaults, `config`, `check` and
`filter` exit 78, and the other commands run. A refused `[lib_log_rich]` value leaves every valid
`LOG_*` variable in force; only a refused `LOG_*` variable makes logging start without all of them.
A problem the type check of the section finds gets one `Error:` line naming the key, never its
value; a value only lib_log_rich itself refuses is reported in lib_log_rich's own words
(`Error: lib_log_rich: Unknown log level: 'bogus'`), which may name neither the setting nor where
it was set.
