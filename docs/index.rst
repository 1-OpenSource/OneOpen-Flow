OneOpen Flow documentation
==========================

**OneOpen Flow** is an open-source visual workflow orchestration and validation
platform for the OneOpenSource ecosystem.

It automates complete technical workflows across browsers, CLI commands, REST
APIs, databases, files, and Docker — with first-class support for dynamic ASPX
and React applications.

Agentic AI systems authenticate with a **service account** (not a human user
login). See :doc:`service-accounts` and :doc:`agentic-admin-sso`.

.. note::

   This documentation is built with Sphinx using the classic
   `Read the Docs <https://docs.readthedocs.io/>`_ theme.

Quick start
-----------

.. code-block:: bash

   docker compose up --build
   docker compose exec backend python -m app.scripts.seed

Then open http://localhost:5173 and sign in with:

* Email: ``owner@oneopen.local``
* Password: ``ChangeMe123!``

Interactive API (Swagger): http://localhost:8000/docs

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   local-development
   architecture

.. toctree::
   :maxdepth: 2
   :caption: Workflows

   workflow-schema
   browser-locators
   aspx-support
   react-support
   auth-verification
   cli-agent
   workboard-integration

.. toctree::
   :maxdepth: 2
   :caption: Agentic AI & admin

   service-accounts
   agentic-admin-sso
   security

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
