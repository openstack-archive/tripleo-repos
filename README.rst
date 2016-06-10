dlrn-repo
=========

A tool for managing dlrn repos.

See: https://github.com/openstack-packages/DLRN

Also ensures yum-plugin-priorities is installed since the dlrn repos
require that to work sanely.

Examples
--------
Install current master dlrn repo and the deps repo::

    dlrn-repo current deps

Install the current-tripleo repo and deps::

    dlrn-repo current-tripleo deps

Install the mitaka dlrn repo and deps::

    dlrn-repo -b mitaka current deps

Write repos to a different path::

    dlrn-repo -o ~/test-repos current deps

Note that this is intended as a tool for bootstrapping the repo setup in
things like TripleO, so it should not have any runtime OpenStack dependencies
or we end up in a chicken-and-egg pickle, and let's be honest - no one wants a
chicken and egg pickle.
