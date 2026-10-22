# ADR-001: Frontend stack for the web-first phase — proposal

- Related issue: [#11 — Chốt stack và quy ước khởi chạy Frontend](https://github.com/nguyenthetai0012/SE2026---T06/issues/11)
- Requirements: [Dashboard requirements](../requirements/dashboard.md)
- Status: **PROPOSED — awaiting confirmation from all group members**
- Date: 2026-10-22
- Decision owner: APP-05 group

## Context

The agreed direction is to build the web app first and consider a desktop app later. The Dashboard requirements do not select a frontend framework, build tool, state-management library, API client, or desktop packaging tool. The group's experience with each option has not been recorded, so familiarity remains an input the group must confirm.

This ADR is a recommendation for discussion. It does not authorize adding application code or dependencies, and it does not make a final stack decision.

## Constraints confirmed from project documents

- The first deliverable is a web Dashboard.
- The Dashboard must support building overview, device list/status, sensor history, alerts, and loading/empty/error states.
- The UI must consume the agreed data contract and must not invent energy calculations, alert thresholds, or offline rules.
- Desktop packaging belongs to a later phase and is not required to implement the current Dashboard.
- No specific frontend stack has been approved in README or the Dashboard requirements.

## Options considered

| Option | Advantages for APP-05 | Trade-offs / open questions |
| --- | --- | --- |
| React + TypeScript + Vite | Vite provides an official React + TypeScript starter; TypeScript can help describe view models and API boundaries; the web build can be evaluated for a later desktop wrapper. | Group familiarity, required accessibility/testing choices, and project-specific commands still need confirmation. |
| Vue + TypeScript + Vite | Also supports a typed web application and can be built with Vite. | Group familiarity and preferred component patterns are unknown; no project advantage has been established yet. |
| Decide after a short group comparison | Avoids choosing a framework before learning team skills and course constraints. | Delays the frontend scaffold until the group records its choice. |

## Recommendation for group discussion

**Recommend React + TypeScript + Vite for the web phase**, provided the group confirms that at least one member can maintain it and that the course environment supports Node.js. This is a proposal, not an approved decision. The recommendation is based on the availability of an official Vite `react-ts` starter and on TypeScript's ability to make the frontend view-model boundary explicit; it is not based on an assumption that the team has already selected React.

Do not add the scaffold or dependencies until the group confirms the choice in this PR or in the related issue.

## Desktop compatibility

Keep the web UI in a browser-first frontend and keep desktop packaging as a separate future decision. If the group later needs a desktop application, compare a native webview wrapper such as Tauri with Electron after the web requirements, packaging needs, operating systems, and team skills are known. Neither Tauri nor Electron is selected by this ADR.

The current choice should avoid coupling the UI to browser-only services where practical, but it should not add an abstraction or desktop-specific dependency without a concrete requirement.

## Commands — proposed, not yet verified in this repository

If React + TypeScript + Vite is approved, the initial scaffold could use Vite's official `react-ts` template:

```sh
npm create vite@latest src/frontend -- --template react-ts
cd src/frontend
npm install
npm run dev
npm run build
```

These commands have **not** been run in this repository. Before closing Issue #11, verify the commands in the project environment, choose the package manager, and document the actual test/lint commands. Do not claim the scaffold or checks exist until they have been run.

Official references:

- [Vite: Getting Started and supported templates](https://vite.dev/guide/)
- [React: Using TypeScript](https://react.dev/learn/typescript)
- [Tauri: Frontend technologies](https://v2.tauri.app/start/frontend/)
- [Electron: Introduction](https://www.electronjs.org/docs/latest/)

## Decision record — open

The group must confirm or replace the recommendation and record:

- Chosen framework and language.
- Package manager and supported Node.js version.
- Actual development, build, test, and lint commands.
- Whether desktop remains in scope for a later phase; if yes, when to compare packaging options.
- Acknowledgment from the group that the choice is suitable for their skills and course environment.

Until these items are confirmed, this ADR remains **PROPOSED** and Issue #11 remains open.
