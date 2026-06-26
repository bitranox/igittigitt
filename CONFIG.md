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

Value coercion: `"true"`/`"false"` -> bool, `"null"`/`"none"` -> None, numeric strings -> int/float.

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

### `[lib_log_rich]`

Logging configuration (console level/theme, journald/eventlog/Graylog backends, queueing,
scrubbing, payload limits). Each key is documented inline in `90-logging.toml`. Common ones:

| Key                                   | Example               | Meaning                                |
|---------------------------------------|-----------------------|----------------------------------------|
| `console_level`                       | `DEBUG`               | Minimum level shown on the console.    |
| `console_theme`                       | `dark`                | Console colour theme.                  |
| `enable_journald`                     | `true`                | Also emit to systemd-journald (Linux). |
| `enable_graylog` / `graylog_endpoint` | `true` / `host:12201` | Ship logs to Graylog (GELF).           |

```bash
igittigitt --set lib_log_rich.console_level=DEBUG info
IGITTIGITT___LIB_LOG_RICH__CONSOLE_LEVEL=DEBUG igittigitt info
```
