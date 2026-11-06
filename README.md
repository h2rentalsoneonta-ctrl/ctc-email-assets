# ctc-email-assets

Public image host for Condominium Travel Club emails (Vacation Alerts, CTC-TRAVEL-001), served by GitHub Pages at
https://h2rentalsoneonta-ctrl.github.io/ctc-email-assets/

- `img/`: email images (16:9 JPEG). Never overwritten or deleted, so links in sent emails keep working.
- `requests/`: image requests written by the Vacation Alerts agent. Pushing one triggers
  `.github/workflows/generate-images.yml`, which generates the image with Cloudflare Workers AI
  (FLUX.1 schnell, free daily allocation), commits it to `img/`, and rebuilds Pages.
- `library.json`: the agent's photo library, so later cycles reuse images.

Setup (one time): add repository secrets `CF_ACCOUNT_ID` and `CF_API_TOKEN` (a Cloudflare API token with Workers AI access).
