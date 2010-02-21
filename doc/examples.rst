Examples
========

Here are a bunch of small example programs that use Eventlet.  All of these examples can be found in the ``examples`` directory of a source copy of Eventlet.

.. _web_crawler_example:

Web Crawler
------------
``examples/webcrawler.py``

.. literalinclude:: ../examples/webcrawler.py

.. _wsgi_server_example:

WSGI Server
------------
``examples/wsgi.py``

.. literalinclude:: ../examples/wsgi.py

.. _echo_server_example:

Echo Server
-----------
``examples/echoserver.py``

.. literalinclude:: ../examples/echoserver.py

.. _socket_connect_example:

Socket Connect
--------------
``examples/connect.py``

.. literalinclude:: ../examples/connect.py

.. _chat_server_example:

Multi-User Chat Server
-----------------------
``examples/chat_server.py``

This is a little different from the echo server, in that it broadcasts the 
messages to all participants, not just the sender.
        
.. literalinclude:: ../examples/chat_server.py

.. _feed_scraper_example:

Feed Scraper
-----------------------
``examples/feedscraper.py``

This example requires `Feedparser <http://www.feedparser.org/>`_ to be installed or on the PYTHONPATH.

.. literalinclude:: ../examples/feedscraper.py