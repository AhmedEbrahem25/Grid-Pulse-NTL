# Grid Pulse — Comprehensive Project Analysis, Hackathon Build Plan & Production Roadmap

## TL;DR
- **Grid Pulse (GridPulse) is a full-stack, IoT-based energy-grid monitoring and management platform** built by Youssef Ammari (Angular 19 frontend + Spring Boot 3.4.5 / GraphQL / PostgreSQL backend) that provides real-time device monitoring, interactive maps, battery/inverter/meter analytics, alerting, fleet management, and role-based access control — deployed on Vercel (frontend) + Railway (backend/DB).
- **For the hackathon**, the winning move is to demo the existing hosted app's "aha" flow — live map of devices → drill into a battery's State of Health/State of Charge → trigger an alert — using seeded fake data and a 90-second scripted demo; do NOT try to build real IoT hardware integration in 24–48h.
- **For production**, the biggest gaps are real device ingestion (the MQTT client is currently a stub), time-series storage (Postgres alone won't scale for high-frequency telemetry), GraphQL subscriptions for true real-time, secrets/security hardening, and a managed cloud database with HA — a phased roadmap is below.

## Key Findings

**What Grid Pulse actually is.** The Notion page at the provided URL is a client-side-rendered Notion SPA that serves only a JavaScript shell to scrapers, so its rendered prose could not be extracted directly. However, the project is unambiguously identifiable: it is **GridPulse**, a public portfolio project by **Youssef Ammari** (GitHub `Ammari-Youssef/GridPulse`, live at `gridpulse-green.vercel.app`, released v1.0.0 on Jan 14, 2026, ~687 commits). Its own description: "Full Stack Java/Angular Application for an IoT-based energy monitoring solution designed to optimize and manage smart electrical networks and residential power usage. Built with Spring Boot, GraphQL, and PostgreSQL, it ensures scalability, security, and precise, auditable data tracking." All technical detail below is drawn from the repository's README, ARCHITECTURE.md, API.md, DEPLOYMENT.md, docker-compose.yml, backend source tree, and GraphQL schema.

**It is more sophisticated than a typical demo.** The backend models real distributed-energy-resource (DER) domains: **Devices**, **BMS** (Battery Management System), **Meter**, **Inverter** with **SunSpec**-aligned sub-models (InvCommon, InvNameplate, InvSettings), **Fleet**, **Message** (device telemetry/alerts), **SecurityKey** (encryption keys), and **User**. It even includes a cybersecurity dimension: an **IDS (Intrusion Detection System) payload** type and **AttackType** enum in the message-parsing layer, plus per-device SecurityKey encryption — reflecting real smart-grid threat models. There is an MQTT config present but it ships as a **StubMqttClient** (i.e., ingestion is simulated/seeded, not live).

**Architecture is a clean monolith.** Client (Angular SPA) → Spring Boot GraphQL API → PostgreSQL, with JWT auth. Design decisions explicitly documented: monolithic architecture, GraphQL for flexible fetching, Liquibase for DB versioning, Docker for consistent environments. Every domain entity has a paired `*History` entity/table — an auditable change-tracking pattern ("precise, auditable data tracking").

## Details

### 1. Project Overview

| Aspect | Detail |
|---|---|
| **Name** | Grid Pulse / GridPulse. Tagline in repo: "Real-time IoT monitoring platform for smart grid infrastructure." |
| **Purpose** | Monitor and manage smart electrical networks and residential/commercial power assets (batteries, inverters, meters) in real time; optimize energy use and surface faults/alerts. |
| **Problem solved** | Grid operators, energy asset owners, and prosumers lack a unified, real-time view of distributed energy resources (DERs). As renewables and battery storage proliferate, operators face grid congestion, voltage instability, intermittency, and cyber-threats. GridPulse centralizes device status, analytics, and alerts. |
| **Target users** | Energy providers / utilities, commercial-and-industrial (C&I) asset operators, fleet managers of distributed assets, and (per the description) residential power users. Personas: Grid Operator/Admin, Fleet Manager, Analyst, End-user/Prosumer. |
| **Value proposition** | Single pane of glass for real-time device health, geospatial visualization, historical analytics, configurable alerting, and role-based multi-tenant management — with an auditable data trail and security-first design. |
| **Core concept** | Devices report telemetry (BMS/meter/inverter payloads); the platform stores current + historical state, renders it on dashboards and maps, computes analytics (SOC/SOH, power dispatched, energy consumed/produced), and raises severity-ranked alerts. |
| **Vision** | Evolve from monitoring toward optimization and grid automation — the broader industry trend of a digital "nerve center" for the grid using sensors, analytics, and AI. |

This sits in a large, fast-growing market. Research Nester puts the energy management software market at "over USD 16.9 billion in 2025... estimated to reach USD 40.5 billion by the end of 2035, expanding at a CAGR of 10.2%," and Precedence Research cites USD 12.60B (2025) → USD 44.31B (2035) at a 13.40% CAGR. Software dominates: per Research Nester, "The software platform sub-segment... is anticipated to garner the highest share of 74.8% in the energy management software market by the end of 2035." The DERMS (distributed energy resource management systems) segment is growing especially fast — Grand View Research values DERMS at ~USD 780M in 2025 → USD 2,756M by 2033 at a 16.7% CAGR, noting "the software segment held the highest market share of over 68% in 2025" with grid optimization & stability the top application (~30%). Grid monitoring/optimization is the dominant application area. This validates the problem space (though GridPulse today is a monitoring platform, not yet a full DERMS with control/optimization).

### 2. Technical Architecture

**Documented system design (from ARCHITECTURE.md):**
```
Client → Angular SPA → Spring Boot GraphQL API → PostgreSQL
                                   └→ JWT Tokens (auth)
```
Key design decisions: monolithic architecture; GraphQL for flexible data fetching; Liquibase for DB versioning; Docker for consistent environments.

**Tech stack (verbatim from repo):**

| Layer | Technology |
|---|---|
| **Frontend** | Angular 19 (standalone components), Angular Material, TailwindCSS 4, Apollo GraphQL (apollo-angular ^13, @apollo/client ^4), Leaflet ^1.9.4 + markercluster (maps), RxJS ~7.8, TypeScript 5.7 |
| **Backend** | Spring Boot 3.4.5, Spring Security + JWT (jjwt), Spring Data JPA, Spring GraphQL, Spring Boot Actuator |
| **Database** | PostgreSQL 16, Liquibase migrations (`db.changelog-master.xml` + per-domain changelogs) |
| **Auth** | JWT access + refresh tokens; tokens stored in memory (not localStorage); `JwtAuthFilter` validates each request; role-based (ADMIN/USER) |
| **DevOps/Quality** | Docker & Docker Compose, GitHub Actions CI/CD, JUnit 5 + Mockito, Testcontainers (Postgres integration tests), JaCoCo (coverage), SonarQube (static analysis) |
| **Build** | Maven (backend), Angular CLI/npm (frontend) |
| **Hosting** | Backend + PostgreSQL on Railway; frontend on Vercel |

**API design.** Schema-first **GraphQL** exposed at `/graphql`, with GraphiQL at `/graphiql`; introspectable/self-documenting. Custom `UUID` scalar for IDs. Schemas are modularized under `resources/graphql/` per domain (auth, device, bms, meter, inverter, inv_common, inv_nameplate, inv_settings, fleet, message, security_key, user), each with input/types/enum/schema (queries+mutations)/pagination folders. Both **offset-based** and **cursor-based (Connection/Edge/PageInfo)** pagination are implemented.

**Data model (confirmed fields from API.md example query + backend source):**
- **Device**: `id, name, model, serialNumber, manufacturer, status, lastSeen`, plus nested `bms`, `meter` (and inverter). Enum `DeviceStatus`. Has `DeviceStats` DTO and `DeviceHistory`.
- **BMS**: `id, temperature, soc` (state of charge), `voltage, soh` (state of health), `cycles, batteryChemistry`. Enums `BatteryChemistry`, `BatteryHealthStatus`.
- **Meter**: `id, powerDispatched, energyConsumed, energyProduced`.
- **Inverter (SunSpec-aligned)**: base `SunSpecModelEntity`; sub-entities `InvCommon`, `InvNameplate` (enum `DerType`), `InvSettings` (enums `ClcTotVaMethod`, `ConnPhase`, `VarAction`).
- **Message (telemetry/alerts)**: enums `MessageFormat, MessagePriority, MessageStatus, MessageType, Severity`; typed payloads `BmsPayload, HeartbeatPayload, IdsPayload, InverterPayload, MeterPayload, SoftwarePayload, SystemPayload`; payload enums `AttackType, SoftwareMessageUpdateStatus, SoftwarePackageType`; a `MessagePayloadParser` + `SeverityInterpreter`.
- **SecurityKey**: enums `KeySource, KeyStatus, SecurityType`; `EncryptionService`.
- **User**: `Role` enum; `UserHistory`.
- **Auditing**: every domain has a `*History` entity + repository (base classes `BaseHistoryEntity`, `BaseHistoryRepository`) and `ApplicationAuditAware` — a full change-audit trail.
- **Seeding**: a `DatabaseSeeder` with per-entity Fakers (BmsFaker, DeviceFaker, etc.) generates demo data — critical for the hackathon demo.

**Domain-specific (energy) technical considerations.** The project already reflects grid-monitoring best practices: real-time device status, geospatial mapping with clustering, time-oriented history tables, severity-based alerting, and SunSpec inverter modeling. Per the SunSpec Alliance, "SunSpec Modbus [is] a default communication and interoperability standard specified in IEEE 1547-2018" — one of three approved interfaces (alongside IEEE 2030.5 and IEEE 1815); the newer 700-series (models 701–712) DER models supersede the 100-series introduced in 2009. In classic register maps, Model 103 = three-phase inverter metering, Model 120 = battery/storage, and models 120–126 map advanced grid-support functions (recommended polling 1–5s). Battery monitoring centers on SOC/SOH/temperature/voltage/cycles — exactly GridPulse's BMS fields — which are the standard inputs for predictive maintenance (forecasting capacity fade before an SOH threshold breach).

**Current constraint:** ingestion is a **StubMqttClient** — the system does not yet consume live device telemetry; data is seeded. Real-time UI updates rely on GraphQL queries/polling; **GraphQL subscriptions (WebSocket) are not yet part of the stack**.

### 3. Features

**Implemented (from README/frontend):**
- Real-time device monitoring (live status + metrics, quick-stat cards)
- Interactive Leaflet maps with geolocation + marker clustering + filtering
- Device management (CRUD, pagination, sorting, search; BMS/Meter/Inverter detail views)
- Advanced analytics (historical charts, device comparison/selector, battery SOH & power-dispatch metrics, consumption/production stats, export)
- Alert management (severity-based filtering, alert detail, acknowledgment/resolution tracking, notification center)
- Fleet management (organize devices into fleets, device assignment, location-based grouping, pagination)
- User management (role-based ADMIN/USER, profile & security settings)
- Secure JWT auth with refresh tokens; responsive/mobile-friendly UI
- GraphQL API; version-controlled DB migrations

**MVP (hackathon) vs Production mapping:**

| Feature | Hackathon MVP | Production |
|---|---|---|
| Auth (JWT, roles) | ✅ demo login | ✅ + MFA, SSO, refresh rotation |
| Device list + detail | ✅ | ✅ + bulk ops |
| Live map | ✅ (seeded) | ✅ (real geodata) |
| Analytics charts | ✅ (historical seed) | ✅ (real time-series) |
| Alerts | ✅ (seeded + manual trigger) | ✅ (rules engine, notifications) |
| Real device ingestion (MQTT) | ❌ stub/seed | ✅ real broker + pipeline |
| GraphQL subscriptions | ❌ (poll) | ✅ WebSocket push |
| Predictive analytics/AI | ❌ | ✅ (SOH forecasting, anomaly detection) |
| Multi-tenancy/billing | ❌ | ✅ |

### 4. Hackathon Build Plan (24–48h)

**Strategy: don't rebuild — leverage.** GridPulse already exists and is deployed. If this is your project, the hackathon deliverable is a *crisp demo + a compelling narrative*, not net-new plumbing. If you're rebuilding from scratch under time pressure, use a faster-to-ship stack than the production one.

**Recommended fast-delivery stack (if building fresh):**
- Frontend: Next.js/React or Angular + a component library (Material/shadcn) + Leaflet or Mapbox for maps + Recharts/Chart.js.
- Backend: a single service — **Node/NestJS or Spring Boot** — but expose REST or a thin GraphQL; skip microservices.
- DB: PostgreSQL (Supabase or Railway one-click) with **seeded fake data** (Faker) — do not wait on real hardware.
- Real-time: fake it convincingly with polling or a simple WebSocket that replays seeded telemetry on a timer.
- Deploy: Vercel (frontend) + Railway/Render (backend+DB) — both give instant HTTPS.

**Prioritized scope (finishable "aha"):** (1) login → (2) dashboard with map of devices → (3) click a device → see BMS SOC/SOH gauge trending → (4) an alert fires (e.g., SOH below threshold or a simulated intrusion/`IdsPayload`) → (5) acknowledge it. That single path is the whole demo.

**Timeline / milestones (48h):**
- H0–2: Read the rubric first; lock the 90-second demo script; wireframe the one flow.
- H2–8: Data model + seed script; auth skeleton; deploy a "hello world" to prod URL early.
- H8–20: Dashboard + map + device detail wired to seeded data.
- H20–32: Analytics charts + alert trigger + acknowledge.
- H32–40: Polish UI, mobile, error/empty states; hard-code/mock any flaky calls.
- H40–46: Rehearse demo out loud, time it, pre-fill forms, remove stall points.
- H46–48: Buffer for the inevitable.

**Division of work (a balanced 3–4 person team beats 4 backend engineers):** 1 frontend, 1 backend/infra, 1 presenter/PM who owns the pitch+slides+demo script, 1 generalist to integrate/debug.

**Demo & pitch guidance (from judges' consensus):** spend ~30% on the problem (make judges *feel* the pain — cite a specific operator losing visibility into a failing battery), 70% on solution+demo. Lead with the live demo, not a startup pitch. Judges decide in the first 2 hours (scope) and the last 3 minutes (pitch). A judge must grasp what it does in <30s and see the "wow" in the first minute. Mock everything that can stall; pre-seed data; run the demo on the deployed URL with a fallback video. Read the specific rubric and tailor to it (innovation vs viability weighting changes what you emphasize). Grid/energy + a cybersecurity angle (the IDS feature) is a strong, memorable differentiator.

### 5. Production Plan

**Phase 0 — Harden what exists (weeks 1–4).**
- Secrets: rotate the demo credentials and any committed defaults; generate a strong `JWT_SECRET_KEY` (openssl rand base64 64), move all secrets to a manager (Railway variables / AWS Secrets Manager / Doppler).
- Security: enable refresh-token rotation, lock down CORS to the frontend domain, disable GraphQL introspection in prod, add query depth/complexity limits + rate limiting (protect against expensive/abusive GraphQL queries), field-level authorization.
- Observability: wire Actuator + Prometheus + Grafana; centralized logs (ELK/Loki); error tracking (Sentry).
- CI/CD: the GitHub Actions pipeline runs tests on PR and auto-deploys to Railway/Vercel on merge to master — add SonarQube gates, JaCoCo coverage thresholds, and Testcontainers integration tests as required checks; add a rollback runbook (Railway redeploy / Vercel promote).

**Phase 1 — Real ingestion & real-time (weeks 4–12).**
- Replace `StubMqttClient` with a real MQTT broker (EMQX, Mosquitto, or HiveMQ). Devices publish telemetry → broker → ingestion service. MQTT v5.0 is an OASIS Standard ratified 07 March 2019 (and ISO/IEC 20922), the de-facto device-to-cloud protocol.
- Add a **time-series store** for high-frequency telemetry. Postgres alone won't scale to thousands of readings/sec. Best fit given the Postgres/SQL investment: **TimescaleDB** (a PostgreSQL extension — keeps SQL, adds hypertables, compression, high-cardinality performance, retention/downsampling). Alternative: InfluxDB for raw ingestion throughput. Keep relational metadata (devices, users, fleets) in Postgres; put telemetry in the time-series store.
- Add **GraphQL subscriptions over WebSocket** (graphql-ws) backed by a pub/sub (Redis) so dashboards get true push updates instead of polling; consider SSE as a lighter alternative for one-way streams.
- Buffering: use the broker's on-disk buffer + a rule engine to filter/enrich telemetry before storage.

**Phase 2 — Scale & reliability (months 3–6).**
- Database: move to a **managed Postgres with HA/failover, PITR, and read replicas** for production (RDS/Aurora, Cloud SQL, DigitalOcean Managed PG, Supabase, or Neon). Railway describes its databases as "unmanaged" — single-node by default, with HA requiring explicit setup (now offered via a Patroni-backed HA conversion) — and its managed Postgres can cost more than RDS at comparable specs: per NoahOps' 2026 comparison, "AWS RDS $57.59/month | Railway $87.82/month" for 2 vCPU/4GB/50GB ("RDS is 34% cheaper"), and NoahOps notes Railway "has no VPC isolation." Railway is fine for dev, weak for production data you care about.
- App tier: horizontal scaling behind a load balancer with autoscaling; add Redis caching (and DataLoader batching to kill GraphQL N+1 queries).
- Consider extracting the ingestion pipeline into its own service (the monolith stays for the API) if telemetry volume dwarfs API traffic.

**Phase 3 — Intelligence & product depth (months 6–12).**
- Predictive maintenance: SOH trajectory forecasting, capacity-fade and thermal-anomaly detection, voltage-imbalance flags — turning monitoring into optimization.
- Grid automation / DER control (write-path to inverters via SunSpec advanced grid-support models), demand response, EV-charging load management — moving toward a full DERMS.
- Multi-tenancy, billing, and white-label dashboards.

**Cost considerations.** Hackathon/MVP: ~$0–40/mo on Railway+Vercel (Railway Hobby $5 incl. $5 usage; small Postgres ~$10–40/mo). Growing production with managed DB + broker + monitoring realistically moves to low-hundreds/mo and scales with telemetry volume and egress. Watch AWS "hidden" costs (NAT gateway, egress, Multi-AZ) if you migrate.

### 6. Product & Business Aspects

**Personas & journeys.**
- *Grid Operator/Admin*: logs in → dashboard/map → spots a red device → drills into BMS/inverter → acknowledges alert → assigns to fleet/tech. (Core loop today.)
- *Fleet Manager*: organizes devices into fleets, tracks fleet-level KPIs, plans maintenance from SOH trends.
- *Analyst*: uses analytics/device comparison + export for reporting and forecasting.
- *Prosumer/residential*: monitors own solar+battery production/consumption.

**Business model options.** B2B SaaS subscription per device/asset or per site (the dominant EMS/DERMS model); tiered by features (monitoring → analytics → predictive → control); Energy-as-a-Service / no-hardware bundles (an emerging pivot in EMS, recasting capex as opex); usage/telemetry-volume pricing; enterprise/utility licensing with SLAs.

**Go-to-market.** Start where interoperability is cheap and value is fast: C&I battery-storage operators and solar installers (SunSpec-compatible fleets), then utilities/aggregators. Lead with fast time-to-value (cloud, no hardware to sell) and the security/audit angle. The market backdrop is favorable — grid modernization, renewables, and net-zero mandates are driving EMS/DERMS demand at double-digit CAGRs.

**Competitive landscape.** Incumbents: Siemens, Schneider Electric (EcoStruxure / One Digital Grid Platform), GE Vernova, ABB, Hitachi Energy, Honeywell, C3 AI. DERMS/VPP challengers and startups exist across grid optimization, VPP, and EV-charging niches. GridPulse's realistic wedge is a modern, developer-friendly, security-aware monitoring layer for mid-market asset operators underserved by heavyweight incumbents — not head-to-head with utility-scale SCADA/ADMS on day one.

### 7. Risks & Considerations

| Risk | Impact | Mitigation |
|---|---|---|
| **Ingestion is stubbed** (no live MQTT) | Not production-real; demo could be mistaken for vaporware | Be honest it's seeded; prioritize real MQTT + time-series in Phase 1 |
| **Postgres for time-series** | Won't scale to high-frequency telemetry; slow queries | Adopt TimescaleDB/InfluxDB; retention + downsampling policies |
| **No real-time push** (polling) | Laggy dashboards at scale | GraphQL subscriptions (graphql-ws) + Redis pub/sub, or SSE |
| **Secrets / default creds** in a public portfolio repo | Account compromise | Rotate all creds, secrets manager, no defaults in prod |
| **GraphQL abuse** (deep/expensive queries) | DoS, data exposure | Depth/complexity limits, rate limiting, disable introspection, field auth |
| **Smart-meter data is personal data** (GDPR/CCPA) | Legal/privacy exposure — usage patterns reveal occupancy/behavior | Lawful basis, purpose limitation, encryption at rest/in transit, anonymization/aggregation, DPIA, right-to-erasure handling |
| **OT/grid cyber-threats** | Critical-infrastructure attacks (false data injection, DoS, rogue devices) | The IDS/AttackType feature is a start; align to IEC 62443 (zones/conduits, IDS/IPS, key rotation) & NIST SP 800-82; per-device SecurityKey encryption; network segmentation |
| **Single-node DB, monolith** | Availability/scaling limits | Managed HA Postgres w/ failover + PITR; horizontal app scaling + LB |
| **Vendor lock-in / cost creep** (Railway at scale) | Rising bills, limited VPC/compliance | Plan migration path to hyperscaler managed services when compliance/scale demands |

## Recommendations

**Immediate (this week / for the hackathon):**
1. Lock the single demo flow (login → map → device → SOC/SOH → alert → acknowledge) and write the 90-second script *before* touching code; rehearse timed, with a fallback recording.
2. Ensure the seeded dataset makes the map and charts look full and realistic; pre-create the demo account; pre-fill forms; mock any flaky call.
3. Lead the pitch with the problem (a specific operator blind to a failing battery) and the security angle (intrusion detection on grid devices) — memorable differentiators.

**Short term (0–4 weeks post-hackathon):** rotate secrets, disable introspection in prod, add rate/complexity limits and CORS lockdown; stand up Prometheus/Grafana + Sentry; enforce coverage/SonarQube gates in CI.

**Mid term (1–3 months):** implement real MQTT ingestion + TimescaleDB for telemetry + GraphQL subscriptions for real-time; move to a managed HA Postgres for the relational store.

**Long term (3–12 months):** add predictive maintenance (SOH forecasting/anomaly detection), then DER control/automation and multi-tenancy/billing to move up-market from monitoring toward DERMS.

**Benchmarks that change the plan:** if sustained telemetry exceeds a few hundred writes/sec or dashboards feel laggy → prioritize time-series DB + subscriptions now. If you onboard a paying customer or handle real personal/meter data → GDPR/DPIA, managed HA DB, and IEC 62443 alignment become non-negotiable. If Railway DB spend approaches RDS-equivalent or you hit a compliance/VPC wall → migrate to a hyperscaler managed database.

## Caveats
- **The Notion page's own rendered text could not be scraped** (it is a JavaScript-only Notion SPA; automated fetches return only the app shell). This analysis is built from the definitively-matching public GitHub repository, live site, and documentation by the same author (Youssef Ammari), which share the identical name, description, and `gridpulse-green.vercel.app` URL. If the Notion page contains additional prose (e.g., a written vision, roadmap, or slide content) not reflected in the repo, that specific narrative is not captured here.
- Some deep schema files (individual `.graphqls` field types, exact message-payload JSON) could not be fetched directly due to GitHub bot restrictions; field lists come from the repo's own API.md example query and the backend source tree, which are reliable but not exhaustive on scalar types.
- Market-size figures vary widely by analyst firm and are forward-looking projections, not guarantees; they are used here to characterize the opportunity, not to value this specific project.
- "GridPulse" is also used by unrelated entities (a Slovenian company gridpulse.com, a Solana energy-trading token gridpluse.org); these are **not** this project.
