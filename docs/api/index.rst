API reference
=============

HTTP endpoints exposed by the OneOpen Flow FastAPI backend.

Base URL
--------

Local development uses ``http://localhost:8000``. All application routes are
prefixed with ``/api`` unless noted otherwise.

Authentication
--------------

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
     - Obtain a JWT access token
   * - ``GET``
     - ``/api/auth/me``
     - Current authenticated user

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
   * - ``POST``
     - ``/api/secrets``
     - Store encrypted secret
   * - ``GET``
     - ``/api/secrets``
     - List secret metadata (no values)
   * - ``DELETE``
     - ``/api/secrets/{id}``
     - Soft-delete secret
   * - ``POST``
     - ``/api/environments``
     - Create environment
   * - ``GET``
     - ``/api/environments``
     - List environments

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

Interactive OpenAPI
-------------------

When the backend is running, browse:

* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc
