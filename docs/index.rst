:root-doc: index

OneOpen Flow documentation
==========================

**OneOpen Flow** is an open-source visual workflow orchestration and validation
platform for the OneOpenSource ecosystem.

It automates complete technical workflows across browsers, CLI commands, REST
APIs, databases, files, and Docker — with first-class support for dynamic ASPX
and React applications.

.. grid:: 2
   :gutter: 2

   .. grid-item-card:: Architecture
      :link: architecture
      :link-type: doc

      System components, execution model, and design principles.

   .. grid-item-card:: Local development
      :link: local-development
      :link-type: doc

      Docker Compose, local setup, environment variables, and tests.

   .. grid-item-card:: Workflow schema
      :link: workflow-schema
      :link-type: doc

      Versioned JSON definitions, variables, and validation rules.

   .. grid-item-card:: Security
      :link: security
      :link-type: doc

      Permissions, secrets, CLI isolation, and audit logging.

Quick start
-----------

.. code-block:: bash

   docker compose up --build
   docker compose exec backend python -m app.scripts.seed

Then open http://localhost:5173 and sign in with:

* Email: ``owner@oneopen.local``
* Password: ``ChangeMe123!``

.. toctree::
   :maxdepth: 2
   :caption: Guides

   architecture
   local-development
   workflow-schema
   browser-locators
   aspx-support
   react-support
   auth-verification
   cli-agent
   security
   workboard-integration

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api/index
   modules/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
