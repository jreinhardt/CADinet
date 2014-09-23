CADinet
=======

CADinet is a web application that allows to upload 3D models via a REST API for
publishing on the web and in the [thingtracker network](https://thingtracker.net).
It is written in [python](http://python.org), using
[flask](http://flask.pocoo.org/) and [MongoDB](http://www.mongodb.org/) with
easy deployment on [OpenShift](https://www.openshift.com/) in mind. The
frontend is based on [bootstrap](http://getbootstrap.com/).

The name is a pun on cabinet, a piece of furniture used to showcase nice
things, and CAD.

It is licensed under the [AGPL3](http://www.gnu.org/licenses/agpl.html).

CADinet is not primarily intended to be used purely in the browser, but
integrated into CAD tools via its REST API. At the moment there is a
experimental [plugin](https://github.com/jreinhardt/CADinet-freecad) for
[FreeCAD](http://freecadweb.org/).

Get started
===========

Register for OpenShift
----------------------

Go to the [OpenShift website](https://www.openshift.com/) and create a new
account if you don't have one already. The free plan allows you to use up to 3
"gears". For a thingcollector instance we only need one.

Spin up a a OpenShift gear
--------------------------

This can be done via the web interface as well, but this is how to do it on the
command line. First install the [RHC client
tools](https://www.openshift.com/developers/rhc-client-tools-install) if you
have not already done so.

Create a new application:
-------------------------

    rhc app create cadinet python-2.7 mongodb-2.4

`cadinet` is the name of the application, and can be replaced by something else
if necessary.

Pull the cadinet code into your application repo
-------------------------------------------------------

    cd cadinet
    git remote add upstream -m master git://github.com/jreinhardt/cadinet.git
    git pull -s recursive -X theirs upstream master

Push your application repo to the gear
--------------------------------------

    git push


Configuration
-------------

The configuration options for cadinet reside outside the code repo, as they
contain a secret key that should not be made public.

Create a textfile with name `cadinet.cfg` in the $OPENSHIFT_DATA_DIR on your
gear and add a secret key and a uuid for the tracker that is published by this
collector, as well as name and contact information for the maintainer of this
collector:

    SECRET_KEY = "replace this by a proper secret key"
    MAINTAINER_NAME = "your name"
    MAINTAINER_EMAIL = "your.name@domain.com"

If you have a [Piwik](http://piwik.org/) instance running (e.g. on
[OpenShift](https://github.com/openshift/piwik-openshift-quickstart)) you can
get analytics enabled on the cadinet by specifying

    PIWIK_URL = "the url of your piwik instance without leading http(s)://"
    PIWIK_ID = "the site id of the thingcollector assigned in your piwik"

If you want to disable the possibility to register new users, add

    ENABLE_REGISTRATION = False

Test the app
------------

Now you should be able to access your cadinet instance at
`http://cadinet-yourdomain.rhcloud.com`. If you created your application with a
different name, its not `cadinet`, but whatever you used, when you created the
application.


Connect the cadinet to the thingtracker network
-----------------------------------------------

Submit the tracker of your cadinet to one or two
[thingcollectors](https://github.com/jreinhardt/thingcollector). This way the
collector can learn about all the things in this cadinet and can index them.

The tracker of your cadinet is available at
`http://cadinet-yourdomain.rhcloud.com/tracker`. If you created your
application with a different name, its not `cadinet`, but whatever you used,
when you created the application.

An instance of a thingcollector is running
[here](http://thingcollector-bolts.rhcloud.com).



Updating the cadinet code
---------------------------

You should check regularly if the cadinet code has been improved. You
can update your instance by pulling the changes from the upstream repo and
pushing them to your gear.

    git pull -s recursive -X theirs upstream master
    git push
