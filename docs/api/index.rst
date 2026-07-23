API reference
=============

HTTP endpoints exposed by the OneOpen Flow FastAPI backend.

Base URL
--------

Local development uses ``http://localhost:8000``. All application routes are
prefixed with ``/api`` unless noted otherwise.

Interactive OpenAPI
-------------------

* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc

Authentication
--------------

.. important::

   Agentic AI should use a **service account**
   (``POST /api/admin/service-accounts``), not a human password login.
   See :doc:`../service-accounts`.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``GET``
     - ``/api/auth/setup-status``
     - Whether an owner account still needs to be created
   * - ``POST``
     - ``/api/auth/register``
     - Register a user (first user becomes owner)
   * - ``POST``
     - ``/api/auth/login``
     - Obtain a JWT access token (humans)
   * - ``GET``
     - ``/api/auth/me``
     - Current authenticated user
   * - ``GET``
     - ``/api/auth/sso/config``
     - Public SSO availability
   * - ``GET``
     - ``/api/auth/sso/authorize``
     - Start OIDC login
   * - ``GET``
     - ``/api/auth/sso/callback``
     - OIDC callback

Agentic & exposed workflows
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``GET``
     - ``/api/agentic/catalog``
     - Tool catalog for Agentic AI
   * - ``PUT``
     - ``/api/workflows/{id}/expose``
     - Publish / unpublish workflow for agents
   * - ``GET``
     - ``/api/exposed/workflows``
     - List exposed workflows
   * - ``GET``
     - ``/api/exposed/workflows/{slug}``
     - Schema + invoke path
   * - ``POST``
     - ``/api/exposed/workflows/{slug}/invoke``
     - Start run by slug

Admin (RBAC, SSO, service accounts)
-----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``GET``
     - ``/api/admin/users``
     - List users
   * - ``PATCH``
     - ``/api/admin/users/{id}``
     - Update role / active
   * - ``GET``
     - ``/api/admin/permissions``
     - Role → permission matrix
   * - ``POST``
     - ``/api/admin/invites``
     - Invite user
   * - ``GET`` / ``PUT``
     - ``/api/admin/sso``
     - OIDC settings
   * - ``GET``
     - ``/api/admin/service-accounts``
     - List service accounts
   * - ``POST``
     - ``/api/admin/service-accounts``
     - Create service account + client secret
   * - ``DELETE``
     - ``/api/admin/service-accounts/{id}``
     - Revoke service account

Workflows
---------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``POST``
     - ``/api/workflows``
     - Create a workflow
   * - ``GET``
     - ``/api/workflows``
     - List workflows
   * - ``GET``
     - ``/api/workflows/{id}``
     - Get workflow + definition
   * - ``PUT``
     - ``/api/workflows/{id}``
     - Update workflow (new version when definition changes)
   * - ``DELETE``
     - ``/api/workflows/{id}``
     - Soft-delete workflow
   * - ``POST``
     - ``/api/workflows/{id}/validate``
     - Validate graph structure
   * - ``POST``
     - ``/api/workflows/{id}/run``
     - Execute workflow
   * - ``POST``
     - ``/api/workflows/{id}/clone``
     - Clone workflow
   * - ``POST``
     - ``/api/workflows/import``
     - Import workflow JSON
   * - ``GET``
     - ``/api/workflows/{id}/export``
     - Export workflow JSON (secrets redacted)

Runs
----

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``GET``
     - ``/api/runs``
     - List runs
   * - ``GET``
     - ``/api/runs/{id}``
     - Run details, node results, artifacts
   * - ``POST``
     - ``/api/runs/{id}/cancel``
     - Cancel an in-flight run
   * - ``POST``
     - ``/api/runs/{id}/retry``
     - Rerun from the beginning
   * - ``POST``
     - ``/api/runs/{id}/retry-from-node``
     - Resume/retry from a failed node
   * - ``POST``
     - ``/api/runs/{id}/provide-input``
     - Human-in-the-loop OTP / input
   * - ``GET``
     - ``/api/runs/{id}/events``
     - Server-Sent Events live stream
   * - ``GET``
     - ``/api/runs/{id}/evidence``
     - Download evidence ZIP
   * - ``POST``
     - ``/api/runs/{id}/create-work-item``
     - Create a linked Workboard defect

Agents, secrets, environments
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``POST``
     - ``/api/agents/register``
     - Register browser or CLI agent
   * - ``POST``
     - ``/api/agents/heartbeat``
     - Agent heartbeat
   * - ``POST``
     - ``/api/agents/{id}/claim-job``
     - Claim next matching job
   * - ``POST``
     - ``/api/agents/{id}/complete-job``
     - Complete a claimed job
   * - ``GET``
     - ``/api/agents``
     - List agents
   * - ``PATCH``
     - ``/api/agents/{id}``
     - Enable / update agent
   * - ``POST``
     - ``/api/secrets``
     - Store encrypted secret
   * - ``GET``
     - ``/api/secrets``
     - List secret metadata (no values)
   * - ``PUT``
     - ``/api/secrets/{id}``
     - Rotate secret
   * - ``DELETE``
     - ``/api/secrets/{id}``
     - Soft-delete secret
   * - ``POST``
     - ``/api/environments``
     - Create environment
   * - ``GET``
     - ``/api/environments``
     - List environments
   * - ``PUT``
     - ``/api/environments/{id}``
     - Update environment
   * - ``DELETE``
     - ``/api/environments/{id}``
     - Delete environment

Triggers
--------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Method
     - Path
     - Description
   * - ``POST``
     - ``/api/triggers/webhook``
     - REST/webhook workflow trigger
   * - ``POST``
     - ``/api/triggers/workboard-status``
     - Auto-retest when Workboard status changes
