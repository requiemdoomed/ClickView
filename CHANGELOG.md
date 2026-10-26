# Changes

## 1.1.0

- Added text editing with collision checks and metadata preservation.
- Added validated, versioned JSON backups shared by desktop and browser.
- Added age-based desktop retention, keeping pinned snippets.
- Added desktop and browser light modes and newest/oldest sorting.
- Added a default-on guard for several common secret formats during desktop capture.
- Added browser character/line counts and selected-state accessibility attributes.
- Made database mutations transactional and closed cursors after every query.
- Fixed browser quota failures: rejected writes now restore the prior in-memory state.
- Preserved unreadable browser history until an explicit reset.
- Kept pinned browser snippets during clear unless explicitly included.
- Fixed the desktop category filter when a category itself is named “All categories”.
- Improved desktop error messages, paused capture after I/O failures, and removed horizontal list scrolling.
- Expanded regression checks and added a browser CI job.

## 1.0.0

Initial desktop clipboard history and responsive browser demo.
