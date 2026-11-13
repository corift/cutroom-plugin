# Cutroom for Claude Code

Edit talking-head videos with Claude Code and review them at https://cutroom.so.

```
claude plugin marketplace add corift/cutroom-plugin
claude plugin install cutroom@cutroom
```

Then start Claude Code, run `/mcp` to sign in to **cutroom**, and ask Claude to "set up Cutroom".

## Updating

Cutroom checks for a new version when a session starts and installs it in the background. Restart Claude Code to use it. To update by hand:

```
claude plugin marketplace update cutroom
claude plugin update cutroom@cutroom
```

Set `CUTROOM_AUTO_UPDATE=0` to turn the automatic check off. What changed in each version: https://github.com/corift/cutroom-plugin/commits/main
