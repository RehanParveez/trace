# Trace

Trace is a multi-tenant construction data intelligence platform designed to connect construction projects, drawings, BOQs, site photos, verification workflows, and project data in one controlled system.

The platform combines deterministic engineering and BIM/CAD processing with assistive AI capabilities. AI is used where it adds practical value—such as normalizing material descriptions, interpreting code-switched WhatsApp captions, and assisting with photo tagging—while engineering quantities, project data, costs, and approvals remain under human control.

# Table of Contents
Overview
What Trace Solves?
Core Principles
Core Workflow
Key Capabilities
BIM and CAD Strategy
WhatsApp Site-Photo Intelligence
AI Philosophy
Architecture
Technology Stack
Repository Structure
Multi-Tenancy and Security
Background Processing
Object Storage
Frontend Architecture
Backend Architecture
Database and Migration Strategy
Testing Strategy
Observability and Hardening
Development Environment
Roadmap
Engineering Guardrails
Project Status
License
Overview

Construction projects generate large amounts of fragmented information:

Drawings
BIM models
BOQs
Material descriptions
Site photographs
Project updates
Progress information
Verification records
Procurement-related information
Project and organization data

This information often exists across different tools and communication channels.

Trace is designed to provide a controlled workflow connecting this information while maintaining a clear distinction between:

Deterministic engineering data
AI-assisted interpretation
Human review and approval

The platform is designed as a multi-tenant SaaS application, with an additional deployment path for privacy-sensitive or enterprise environments.

What Trace Solves?

Trace is designed around a staged construction workflow:

Organization
     ↓
Projects
     ↓
Drawings / BIM
     ↓
BOQ
     ↓
Site Photos
     ↓
Verification
     ↓
Project Intelligence

The platform is intended to reduce fragmentation between project information and make construction data easier to review, search, verify, and act upon.

The system is not designed around replacing engineers or construction professionals with AI.

Instead:

AI assists. Deterministic systems calculate. Humans approve.

Core Principles
1. Workflow First

Development follows a staged workflow where every major phase should end in a usable and demonstrable product capability.

2. Backend Is Authoritative

The backend is the source of truth.

Neither the frontend nor an AI model can independently make an engineering result official.

3. AI Is Assistive

AI can interpret, normalize, classify, summarize, and suggest.

It cannot independently:

Approve BOQs
Approve engineering quantities
Change authoritative project state
Override human decisions
Turn a suggestion into an official value

4. Deterministic Engineering Where Possible

When a reliable engineering or geometric computation can be performed deterministically, the system should prefer that approach over an AI-generated guess.

This is particularly important for BIM/IFC quantity extraction.

5. Multi-Tenant From the Beginning

Organizations are treated as tenants from the first database migration.

Tenant isolation is not a future enhancement.

6. Defense-in-Depth Tenant Isolation

Trace uses two layers of tenant isolation:

Application-Level Organization Scoping
                 +
PostgreSQL Row-Level Security

Both layers are tested independently.

7. Human Approval

AI-generated or automatically extracted information remains visibly provisional until an authorized human reviews and approves it.

8. Privacy-Aware AI

AI processing of organization content is opt-in.

New organizations default to AI being disabled unless explicitly enabled.

Core Workflow

Trace is designed around several interconnected workflows.

Organization

An organization represents a construction company or other customer using the platform.

Organizations contain users, roles, projects, subscriptions, and organization-level settings.

Projects

Projects are the central operational container for construction data.

Projects connect:

Project members
Drawings
BOQs
Site photos
Verification data
Future project intelligence
Drawings and BOQs

Construction drawings can be uploaded and processed according to their supported format.

Where structured BIM data is available, Trace extracts traceable drawing elements and generates draft BOQ information.

The resulting BOQ remains subject to human review and approval.

Site Photos

Site engineers can send photographs through WhatsApp.

Trace receives the message, verifies the webhook, downloads the media, stores the image, and associates it with the appropriate project.

Where AI is enabled, captions and photographs can be analyzed to suggest project information and tags.

Verification

Later phases connect project progress claims with photographs and BOQ information to support verification workflows.

Key Capabilities

Planned platform capabilities include:

Multi-tenant organization management
User authentication
Organization roles and permissions
Project management
BIM/IFC ingestion
DWG/DXF assisted workflows
BOQ generation
BOQ review and approval
BOQ versioning
Optimistic locking for concurrent BOQ edits
WhatsApp site-photo ingestion
Site-photo storage and search
AI-assisted caption interpretation
Optional AI photo tagging
Material normalization
Material normalization caching
Project verification
Notifications
Audit logging
Subscription and usage management
Platform administration
Job queue monitoring
Excel/PDF exports
English/Urdu localization
RTL support
Optional on-premises deployment
BIM and CAD Strategy

Trace intentionally uses a tiered approach to construction drawing formats.

IFC — Primary MVP Format

IFC is the primary automated BIM input format.

The platform uses ifcopenshell for IFC processing.

The intended pipeline is:

IFC Upload
    ↓
Format Detection
    ↓
IFC Parsing
    ↓
Element Extraction
    ↓
Quantity Extraction
    ↓
Material Normalization
    ↓
Cross-Drawing Deduplication
    ↓
Draft BOQ
    ↓
Human Review
    ↓
Approval

Structured IFC data allows Trace to work with discrete BIM objects and associated quantities.

DWG / DXF — Assisted Tier

DWG/DXF processing is treated as an assisted workflow rather than pretending that arbitrary 2D CAD drawings contain the same semantic information as BIM.

The planned pipeline uses:

DWG
 ↓
ODA File Converter
 ↓
DXF
 ↓
ezdxf
 ↓
Geometry / Layer Information
 ↓
Assisted Measurement
RVT — Later Optional Integration

Native RVT parsing is not treated as an MVP capability.

The preferred workflow is:

Revit
  ↓
Export IFC
  ↓
Trace IFC Pipeline

An optional Autodesk Platform Services integration can be considered later for clients that cannot or will not export IFC.

That integration is intentionally positioned as a later, paid capability.

WhatsApp Site-Photo Intelligence

WhatsApp is an important operational interface because site engineers can already use it from construction locations without needing to interact with a complex web application for every photograph.

The intended workflow is:

Site Engineer
     ↓
WhatsApp Photo + Caption
     ↓
Meta WhatsApp Cloud API
     ↓
Webhook Verification
     ↓
Message Deduplication
     ↓
Priority Queue
     ↓
Media Download
     ↓
Object Storage
     ↓
Project Resolution
     ↓
Optional AI Processing
     ↓
Site Photo
     ↓
Web Gallery
Webhook Security

Incoming webhook requests must be verified using the appropriate WhatsApp signature mechanism before their contents are trusted.

Message Deduplication

WhatsApp webhook delivery is treated as retryable.

Every message uses its WhatsApp message ID as a deduplication key.

If the same message is delivered twice:

First delivery
    ↓
Process

Second delivery
    ↓
Already exists
    ↓
Acknowledge
    ↓
Do not process again

This prevents duplicate photos and unnecessary AI processing.

Priority Queue

WhatsApp media downloads use a dedicated high-priority Celery queue.

This prevents large BIM parsing operations from delaying time-sensitive media downloads.

AI Philosophy

Trace does not treat AI as the source of truth.

AI is used selectively for tasks where probabilistic interpretation is useful.

Examples include:

Material Normalization

Messy material descriptions can be normalized using:

Raw Material Text
       ↓
Cache Lookup
       ↓
Dictionary / Rule Match
       ↓
LLM Fallback
       ↓
Normalized Material

The deterministic and cached paths are preferred before calling an AI model.

WhatsApp Caption Interpretation

AI can assist in extracting structured information from natural-language captions, including:

Project
Location
Date
Notes

The detected information is shown as a suggestion and can be confirmed or edited.

Photo Tagging

Where enabled, a vision-capable model can suggest tags for construction photographs.

These tags remain subject to human confirmation.

AI Provider

The architecture supports a provider abstraction so the system can use:

Cloud AI providers
Ollama for on-premises deployments
Rule-based fallback behavior where appropriate

AI is disabled by default for new organizations.

Architecture

Trace follows a modular monorepo architecture.

                         React Frontend
                              │
                              │ HTTPS
                              ▼
                       Nginx / Caddy
                              │
                              ▼
                         FastAPI App
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
          PostgreSQL        Redis       Object Storage
               │              │              │
               │              │              │
               │              ▼              │
               │          Celery             │
               │              │              │
               │       ┌──────┴──────┐       │
               │       ▼             ▼       │
               │   WhatsApp         BIM      │
               │   Priority        Parsing   │
               │    Queue           Queue    │
               │       │             │       │
               │       └──────┬──────┘       │
               │              ▼              │
               │       AI / Processing       │
               │                             │
               └─────────────────────────────┘

The primary infrastructure components are:

PostgreSQL
Redis
FastAPI
Celery
Flower
S3-compatible object storage
React
Vite
Technology Stack
Layer	Technology
Backend	FastAPI
Language	Python 3.12
ORM	SQLAlchemy 2.0
Migrations	Alembic
Database	PostgreSQL 16
Cache / Broker	Redis 7
Background Jobs	Celery
Queue Monitoring	Flower
Object Storage	S3-compatible / MinIO
BIM	ifcopenshell
CAD	ezdxf + ODA File Converter
Frontend	React + Vite
State Management	Zustand
Server State	TanStack Query
Styling	Tailwind CSS
Localization	react-i18next
Charts	Recharts
IFC Web Components	@thatopen/components / web-ifc
Authentication	JWT access + refresh tokens
Rate Limiting	Redis-backed rate limiting
Testing — Backend	pytest + httpx
Testing — Frontend	Vitest + React Testing Library
E2E	Playwright
Error Tracking	Sentry
Reverse Proxy	Nginx / Caddy
Containers	Docker + Docker Compose
CI	GitHub Actions
Repository Structure

The project is organized as a monorepo:

Trace/
│
├── backend/
│
├── frontend/
│
├── infra/
│   ├── postgres/
│   │   └── init/
│   │       └── rls_policies.sql
│   │
│   └── nginx/
│       └── nginx.conf
│
├── docs/
│   └── architecture.md
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── docker-compose.onprem.yml
├── .env.example
├── .gitignore
└── README.md
Backend Architecture

The backend follows a domain-oriented modular structure.

backend/
└── app/
    ├── main.py
    │
    ├── core/
    │   ├── config.py
    │   ├── database.py
    │   ├── security.py
    │   ├── exceptions.py
    │   └── logging.py
    │
    ├── shared/
    │   ├── mixins.py
    │   ├── pagination.py
    │   ├── money.py
    │   ├── state_machine.py
    │   ├── idempotency.py
    │   └── storage.py
    │
    ├── dependencies/
    │   ├── auth.py
    │   ├── tenancy.py
    │   └── permissions.py
    │
    ├── modules/
    │   ├── identity/
    │   ├── organizations/
    │   ├── subscriptions/
    │   ├── projects/
    │   ├── drawings/
    │   ├── boq/
    │   ├── whatsapp/
    │   ├── photos/
    │   ├── verification/
    │   ├── ai_assistant/
    │   ├── billing/
    │   ├── audit/
    │   ├── notifications/
    │   ├── dashboard/
    │   └── platform_admin/
    │
    ├── workers/
    │   ├── celery_app.py
    │   ├── bim_ingestion.py
    │   └── whatsapp_ingestion.py
    │
    └── tests/

Each domain module follows the general pattern:

module/
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── router.py
├── permissions.py
└── tests/

The service layer contains domain behavior.

Repositories handle persistence.

Routers expose HTTP APIs.

Permissions define authorization boundaries.

Frontend Architecture

The frontend is organized by product domain rather than by technical type alone.

The planned structure is:

frontend/
└── src/
    ├── modules/
    │   ├── identity/
    │   ├── organizations/
    │   ├── subscriptions/
    │   ├── projects/
    │   ├── drawings/
    │   ├── boq/
    │   ├── whatsapp/
    │   ├── photos/
    │   ├── verification/
    │   ├── dashboard/
    │   ├── billing/
    │   ├── notifications/
    │   ├── settings/
    │   │   └── ai-settings/
    │   └── platform-admin/
    │
    ├── shared/
    │   ├── api/
    │   ├── components/
    │   ├── hooks/
    │   ├── utils/
    │   └── ...
    │
    ├── stores/
    ├── app/
    └── main.tsx

Frontend modules will be developed alongside their corresponding backend modules.

The intended development model is:

Backend Module
      ↓
API Contract
      ↓
Frontend API Layer
      ↓
Frontend Types
      ↓
TanStack Query Hooks
      ↓
Components / Pages
      ↓
Integration
      ↓
Module Complete

This prevents the backend and frontend from becoming two disconnected projects.

The detailed visual design system and final UI/UX direction will be established before the application modules are implemented.

Multi-Tenancy and Security

Tenant isolation is one of the most important architectural requirements in Trace.

Every organization-owned record carries an organization_id.

The system protects tenant boundaries at two levels.

Application Layer

The FastAPI application establishes the current organization and scopes database access accordingly.

Database Layer

PostgreSQL Row-Level Security provides a second, database-enforced boundary.

Conceptually:

Application
    ↓
Current Organization
    ↓
SET LOCAL app.current_org_id
    ↓
PostgreSQL RLS
    ↓
organization_id = current organization

Tables use:

ENABLE ROW LEVEL SECURITY

and:

FORCE ROW LEVEL SECURITY

The architecture also separates database roles:

trace_migrations
    ↓
Alembic / table ownership

trace_runtime
    ↓
FastAPI / Celery
    ↓
RLS enforced

This prevents the runtime application role from bypassing tenant isolation through table ownership.

Tenant isolation is tested at both layers independently.

Authentication and Authorization

trace uses:

JWT access tokens
Refresh tokens
Organization-scoped authorization
Role-based permissions
Project-level permission scopes where required
A separate platform-admin role

Organization users and platform administrators are treated as separate authorization domains.

The frontend does not determine whether an operation is allowed.

The backend always enforces permissions.

Background Processing

Background jobs are handled using Celery and Redis.

Trace uses separate queues for workloads with different operational characteristics.

WhatsApp Priority Queue
whatsapp_priority

Used for time-sensitive WhatsApp media downloads and related processing.

BIM Parsing Queue
bim_parsing

Used for CPU/memory-intensive BIM/CAD processing.

BIM parsing tasks use time limits to prevent pathological files from occupying workers indefinitely.

Celery's process-based worker model also provides useful isolation for potentially unstable native geometry-processing libraries.

Queue Observability

Flower is included as part of the development infrastructure.

It provides visibility into:

Queue depth
Task execution
Task failures
Task duration
Worker state

Later, this information feeds a platform-admin job-health view.

Object Storage

Construction photographs, drawings, and generated exports are stored outside PostgreSQL using S3-compatible object storage.

Development

MinIO is used locally.

Production

The architecture supports S3-compatible providers such as:

Amazon S3
Cloudflare R2
Other compatible object-storage services

Objects are organized with tenant and project context.

A conceptual photo path is:

/{organization_id}/{project_id}/{yyyy-mm-dd}/{photo_id}

Object-storage lifecycle policies are planned so that long-lived photo data does not accumulate indefinitely on expensive hot storage.

Database and Migration Strategy

Database changes are managed through Alembic.

The architecture uses domain-oriented migrations.

# Important domain protections include:

BOQ Optimistic Locking

BOQ items use a version field.

Concurrent edits use optimistic locking so that a stale update produces a concurrency error rather than silently overwriting another user's work.

Idempotency

Retry-prone POST operations can use idempotency keys.

For example:

Upload Drawing
      ↓
Idempotency-Key
      ↓
Already processed?
   ↙       ↘
 YES        NO
  ↓          ↓
Return     Process
existing   request
response

This prevents duplicate records caused by network retries or repeated requests.

Material Normalization Cache

Repeated material strings can use a shared normalization cache.

The cache is designed to avoid repeatedly paying for AI normalization of the same material description.

Testing Strategy

Testing is treated as part of the architecture rather than something added after implementation.

Unit Tests

Using pytest for:

BIM parsing
Material normalization
State machines
Permission helpers
Cache behavior
Domain services
Integration Tests

Using pytest, httpx, and a test PostgreSQL database for:

API behavior
Service/repository integration
Database constraints
Realistic IFC fixtures
Tenant Isolation Tests

Tenant isolation is tested twice:

Through the application layer
Directly against PostgreSQL using the runtime database role

This verifies that RLS independently protects the tenant boundary.

WhatsApp Tests

Tests cover:

Signature verification
Invalid webhook rejection
Duplicate wa_message_id
Duplicate processing prevention
Single photo creation
Single AI invocation
Idempotency Tests

Repeated requests using the same idempotency key and request body must return the original result instead of creating duplicate records.

Optimistic Locking Tests

A stale BOQ version must produce a concurrency error rather than silently overwriting another update.

AI Robustness

Tests cover:

Invalid model responses
Retry behavior
Fallback behavior
Malformed BIM input
Graceful task failure
End-to-End Tests

Playwright is planned for later complete workflows such as:

Upload IFC
    ↓
Parse
    ↓
Review
    ↓
Approve
    ↓
Export

and:

Connect WhatsApp
    ↓
Send Photo
    ↓
Process
    ↓
Photo Appears in Gallery
Observability and Hardening

The platform is designed with operational visibility from the beginning.

Planned capabilities include:

Structured JSON logging
Request IDs
Organization IDs in logs
Error tracking
Sentry integration
Queue monitoring
Rate limiting
Webhook signature validation
Upload validation
Append-only audit logging
Backup and restore procedures
Data export/deletion tooling
Object-storage lifecycle management
Usage quotas

Sensitive configuration is provided through environment variables and should not be committed to the repository.

Development Environment

The development environment is containerized with Docker Compose.

The planned development services are:

PostgreSQL
Redis
MinIO
FastAPI
Celery — WhatsApp priority worker
Celery — BIM worker
Flower
React / Vite

The development architecture intentionally keeps infrastructure close to the production architecture so that local development does not depend on a substantially different system.

Environment Configuration

Environment configuration is provided through .env.

Important categories include:

Application
Database
Redis / Celery
Object Storage
Authentication
AI
WhatsApp
Rate Limiting
Billing
Localization
Frontend

Secrets must never be committed to Git.

A .env.example file documents the expected configuration without containing production credentials.

Deployment Model

Trace is designed primarily as a SaaS platform while keeping an on-premises deployment path available for enterprise and privacy-sensitive customers.

SaaS

The default deployment model.

On-Premises

A Docker-based deployment can be provided for organizations requiring greater control over infrastructure and AI processing.

The architecture allows the AI provider to be switched so that on-premises installations can use Ollama instead of a cloud AI provider.

Localization

The platform is designed with localization from the beginning.

Initial supported languages:

English
Urdu

The frontend uses react-i18next.

Urdu support includes RTL layout switching.

Default regional configuration:

Locale: en
Supported: en, ur
Currency: PKR
Timezone: Asia/Karachi
Billing and Subscriptions

Billing is designed around organization-level subscriptions and usage.

The initial B2B approach supports manual invoicing.

The architecture also allows configurable payment providers for future self-service billing.

Planned configuration supports:

manual
safepay
payfast

Billing and payment functionality is intentionally separated from the core project workflow so that payment-provider changes do not affect the rest of the application.