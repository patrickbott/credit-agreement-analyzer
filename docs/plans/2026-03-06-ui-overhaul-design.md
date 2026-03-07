# UI Overhaul Design Document

**Goal:** Transform the credit agreement analyzer from a basic Streamlit tool into a polished, premium internal banking application for RBC's leveraged finance group.

**Aesthetic:** "Refined Financial" — modern SaaS polish (Linear, Stripe Dashboard) meets institutional finance credibility. Clean but data-dense. RBC-branded.

**Users:** Investment banking analysts in leveraged finance who need to quickly extract deal terms from credit agreements to advise on debt structuring.

## Design Decisions

### Typography
- **Headings:** DM Sans (geometric, modern, distinctive)
- **Body:** Source Sans 3 (highly readable at density)
- Both available on Google Fonts

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| Navy Deep | #001A3E | Sidebar background, primary dark |
| RBC Blue | #0051A5 | Primary actions, links, accents |
| RBC Blue Light | #E8F0FE | Subtle blue backgrounds |
| Gold | #C8A000 | Key accents, active states (muted from #FFCC00) |
| Gold Bright | #D4AF37 | Metallic gold for premium touches |
| Ink | #0F1A2E | Primary text |
| Muted | #64748B | Secondary text, captions |
| Surface | #FFFFFF | Card backgrounds |
| Surface Alt | #F8FAFC | Alternate surface |
| Background | #F1F5F9 | Page background |
| Border | #E2E8F0 | Card borders |
| Success | #059669 / #ECFDF5 | HIGH confidence |
| Warning | #D97706 / #FFFBEB | MEDIUM confidence |
| Danger | #DC2626 / #FEF2F2 | LOW confidence |

### Layout Changes
- Sidebar: deeper navy, better section hierarchy, gold accent lines
- Cards: refined shadows, subtle hover transitions, glass-morphism-lite
- Tabs: cleaner with animated gold underline indicator
- Report sections: left accent borders, collapsible, better spacing
- Buttons: refined rounded corners, gold accent on primary
- Empty states: clear CTAs with visual hierarchy

### New Features
1. **Definitions Browser** — 4th tab exposing the existing DefinitionsIndex with search
2. **Copy-to-Clipboard** — JS-based copy button on report sections and Q&A answers
3. **Report Quick-Nav** — Sticky TOC with anchor links for generated reports

### Intentional Omissions
- No multi-document comparison (too complex for this scope)
- No dark mode
- No saved workspaces / persistent sessions
- No PowerPoint/Word export (PDF export exists)
