# Instructions for Coding Agents

This repo includes a Home Assistant integration and a CLI tool. If you are an
automated coding agent, follow these rules when making changes.

## Must Follow

- Always update documentation when code changes alter behavior, outputs, or
  configuration. At minimum, review and update:
  - `README.md`
  - `QUICKSTART.md`
  - `CLI.md`
  - `ENERGY_DASHBOARD_SETUP.md` (if energy/sensor behavior changes)
- Keep secrets out of commits. Use `solark_secrets.template.json` for examples
  and never commit `solark_secrets.json`.
- Prefer small, focused edits; avoid unrelated formatting changes.
- If you change CLI flags or output structure, update `CLI.md` in the same PR.
- If you change sensor names/units/behavior, update README tables and quick
  start instructions.

## Helpful Context

- CLI entry point: `python -m solark_cli`
- Integration code: `custom_components/solark/`
- Template secrets file: `solark_secrets.template.json`

## Quality Checks (Optional but Recommended)

- Run the CLI against a test secrets file when changing CLI behavior.
- Validate Home Assistant config flow and sensor parsing when touching those
  modules.

## Deploying to Home Assistant via HACS

**Important:** Only install and restart when explicitly asked by the user.

After committing and pushing changes, the user can request installation via HACS:

1. Commit and push: `git add -A && git commit -m "message" && git push`
2. Get the **full** commit hash: `git rev-parse HEAD`
3. **Wait at least 10 seconds** after pushing before installing (GitHub needs
   time to make the commit available)
4. Use MCP tools to install:
   ```
   mcp__homeassistant__ha_call_service(
       domain="update",
       service="install",
       entity_id="update.solark_cloud_update",
       data={"version": "b2b257bfull40charhashhere"}
   )
   ```
5. The update entity is `update.solark_cloud_update`
6. After install, a Home Assistant restart is required (only when user asks)

To check available updates first:
```
mcp__homeassistant__ha_get_updates()
```
