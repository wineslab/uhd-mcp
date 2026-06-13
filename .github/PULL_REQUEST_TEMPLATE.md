<!-- Thanks for contributing! Please fill out the sections below. -->

## Summary

<!-- What does this PR change and why? -->

## Related issues

<!-- e.g. Closes #123 -->

## How was this tested?

- [ ] `hatch -e dev run test`
- [ ] `hatch -e dev run lint`
- [ ] `hatch -e dev run type-check`
- [ ] Tested against real USRP hardware (describe setup below)

<!-- If hardware was involved, note the USRP model, UHD version, and what you ran. -->

## Checklist

- [ ] Changes follow the conventions in [CLAUDE.md](../CLAUDE.md) (TOON output, non-blocking long-running tools, stderr-only logging in stdio mode)
- [ ] If a tool signature changed, the DXT proxy (`src/usrp_proxy_dxt/manifest.json` and `server/index.js`) was updated to match
- [ ] Version bumped in all three places if releasing (`VERSION`, `src/uhd_mcp/__init__.py`, `src/usrp_proxy_dxt/manifest.json`)
- [ ] Docs updated where relevant
