Learning Sequences
------------------

This package creates a ModuleStore-independent representation of learning
sequences (a.k.a. "subsections" in Studio), as well as how they are put together
into courses. It is intended to serve Course Outline and Sequence metadata
requests to end users though the LMS, though it is also available to the Studio
process for pushing data into the system.

Direction: Keep
===============

This package is being actively developed.

Usage
=====

* You may make foreign keys to learning_sequence models from your own app.
* Otherwise, you should only ever import from the top level
openedx.djangoapps.content.learning_sequences.api package. Do not import from
anywhere else in the package, including sub-modules of api.
* If you are doing development work, please see the docs directory for
architectural decisions related to this app.
