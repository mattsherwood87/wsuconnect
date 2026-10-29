
.. _mysql_db:

MySQL Database
==============

A CoNNECT :term:`MySQL` database has been implemented on the master node to index files in each project's directory. This database and associated tools 
therein are local to the master node, so core nodes cannot query or update it. Different tables must be established
for each independent project, which can be developed using :doc:`this custom toolkit <../broad_analysis_tools/index>`.

MySQL can be accessed through the command line:

.. code-block:: shell-session

   $ mysql --login-path=client <database>
   
where <database> is replaced with the MySQL database. Currently, all projects are contained in a single database, "CoNNECT".

Each project will have two tables in the CoNNECT database: one main table containing all files except source files and one source table containing files within 
the BIDS sourcedata directory. The main table (referred to in the project's credentials as searchTable, see `credentials.json file <https://connect-tutorial.readthedocs.io/en/latest/support_tools/index.html#read-credentials-py>`_) contains the elements described 
in :numref:`mysql_data_table`. The sourcedata table contains the elements described in :numref:`mysql_sourcedata_table`. 

MySQL allows efficient queries of files contained within a project's directories. This will optimize file searching and data processing.
Hyphens (``-``) are not allowed in table names and are replaced with underscores (``_``).

.. _mysql_data_table:

.. list-table:: The main table for each project <searchTable>, as defined via the `credentials.json file <https://connect-tutorial.readthedocs.io/en/latest/support_tools/index.html#read-credentials-py>`_.
   :widths: 25 50 25
   :header-rows: 1

   * - **Column Name**
     - **Column Description**
     - **Char Size**
   * - fullpath
     - Full path to the local file, including filename and extension
     - 255
   * - filename
     - Filename and extension, excluding the path
     - 255
   * - basename
     - Filename, excluding extension and path. NULL if no basename
     - 255
   * - extension
     - Extension, excluding filename and path. NULL if no extension
     - 48

|
.. _mysql_sourcedata_table:

.. list-table:: The sourcedata table for each project <searchSourceTable>, as defined via the `credentials.json file <https://connect-tutorial.readthedocs.io/en/latest/support_tools/index.html#read-credentials-py>`_.
   :widths: 25 50 25
   :header-rows: 1

   * - **Column Name**
     - **Column Description**
     - **Char Size**
   * - fullpath
     - Full path to the local file, including filename and extension
     - 255
   * - filename
     - Filename and extension, excluding the path
     - 255


Helpful MySQL Commands
----------------------

These helpful commands can be executed on the master node:


Logging in to MySQL
^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session

   $ mysql --login-path=client <database>
    

Exiting MySQL
^^^^^^^^^^^^^

.. code-block:: shell-session

   mysql> exit;
  

Creating a New Database
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session

   mysql> CREATE DATABASE <database_name>;
  

Creating a New Table
^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session

   mysql> CREATE TABLE <table_name> (<column1_name> <data_type>, <column2_name> <data_type>);
  

List All Tables in Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session

   mysql> SHOW TABLES;
  

Retrieve All Columns from a Table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session 

   mysql> SELECT * FROM <table_name>;
  

Retrieve All Columns from a Table Matching a String
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session

   mysql> SELECT * FROM <table_name> WHERE <column> REGEXP '<search_string>';
  

Determine Last Update Time for a Table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell-session

   mysql> SELECT UPDATE_TIME FROM information_schema.tables WHERE TABLE_SCHEMA = '<database>' AND TABLE_NAME = '<table>';


