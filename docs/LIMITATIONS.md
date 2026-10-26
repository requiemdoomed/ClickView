# Limitations review

| Area | Improvement in 1.1 | Remaining constraint |
| --- | --- | --- |
| Accidental secret capture | App exclusions plus default-on common-key pattern guard | Foreground attribution is best effort. Browser tabs, arbitrary passwords, and all credential formats cannot be recognized. Manual entry/import intentionally bypass these capture filters. |
| Data recovery | Portable validated JSON backups; atomic desktop export and import transactions | Backups are manual and plaintext; no encrypted vault or automatic remote backup. Export is limited to 2,000 records / 10 MB. |
| Database failures | Explicit transactions, rollback, closed cursors, short network timeouts, paused capture on error | Database calls still run on the UI thread; an unavailable server may briefly stall the interface. This is a single-user utility, not a multi-user sync service. |
| Growing history | Count limits plus optional age retention and pinned exceptions | Search scans text; large pinned collections can be slower. Age deletion runs hourly, not continuously. |
| Browser storage | Failed writes roll back; corruption is preserved until explicit clear; cross-tab refresh | Browser quotas still apply. Closing tabs or clearing site data removes unsaved/unbacked-up data. Concurrent writes in different tabs can race. |
| Mobile | Responsive controls, editing, themes, backup transfer | Browser demo only; no background clipboard monitoring on Android/iOS. |
| Wayland | Safe refusal when foreground app identity is unavailable | Use manual entry. No claim of universal clipboard access. |
| macOS | System Events foreground checks and documented setup | Permission-dependent; Qt external clipboard-change timing can require returning to the app. |
| Platform validation | Offscreen Qt clipboard integration, browser checks, CI definitions | Real Windows/macOS sessions and a live MySQL server were not available for this release's local verification. |
| Data deletion | Clear-history confirmations and optional preservation of pins | Deletion does not guarantee secure erasure from backups, storage media, or database logs. |

ClipView is intended for useful everyday snippets, not confidential credentials. No machine-learning model is used. Its behavior can be inspected and reproduced through the source and included tests.
