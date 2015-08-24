Bare simple Command Line Interface (CLI) for OVH.

 >>> ./ovh-eu domain
 Last update                Domain              Name server type    Offer     Transfer lock status    Owo supported
 -------------------------  ------------------  ------------------  --------  ----------------------  ---------------
 2014-04-15T10:44:32+02:00  yadutaf.net         hosted              gold      locked                  True
 2014-04-15T10:41:06+02:00  yadutaf.eu          hosted              gold      locked                  False
 2014-04-15T10:41:06+02:00  yadutaf.fr          hosted              gold      locked                  False
 2014-04-15T10:44:32+02:00  yadutaf.org         hosted              gold      locked                  True
 2014-04-15T10:44:26+02:00  yadutaf.com         hosted              gold      locked                  True

Highlights
==========

- **FULL** OVH-EU, OVH-CA, RunAbove-ca API support
- does not require *any* password
- pretty printing, as you would expect (tables, list, graphs, ...)
- ... but raw json output is still available

Installation
============

Even though this is quite feature complete, this code is still an alpha hence
it is only available via ``git clone`` for now.

Get the code:

.. code:: bash

  git clone https://github.com/yadutaf/ovh-cli
  cd ovh-cli
  # optional, but highly encouraged. See http://virtualenvwrapper.readthedocs.org for more informations
  # mkvirtualenv ovh-cli
  pip install -r requirements.txt

Configuration
=============

``ovh-cli`` is designed to interact with your account in a secure way. As such,
it will *never* ask you for a password. Instead, it fully relies on OVH's API
authentication mechanism.

Depending on the API you plan to use, you may use one of these URLs to grant
full script access to your account. Feel free to restrict accesses permissions
as required by your usage for a better security!

- `OVH Europe <https://eu.api.ovh.com/createToken/index.cgi?GET=/*&POST=/*&DELETE=/*&PUT=/*>`_
- `OVH North America <https://ca.api.ovh.com/createToken/index.cgi?GET=/*&POST=/*&DELETE=/*&PUT=/*>`_
- `Runabove <https://api.runabove.com/createApp>`_

For Runabove, you may use included ``create-consumer-key.py runabove-ca`` to generate your consumer key.

Then you should put your credentials in ``~/.ovh.conf`` like:

.. code:: ini

    [ovh-eu]
    ; configuration specific to 'ovh-eu' endpoint
    ; other supported endpoints includes 'ovh-ca' and 'runabove-ca'
    application_key=my_app_key
    application_secret=my_application_secret
    consumer_key=my_consumer_key

For more informations on configuration mechanism, please visit: 
https://github.com/ovh/python-ovh/blob/master/README.rst#configuration

Usage
=====

Depending on the API you will use, you may want to try:

- ``./ovh-eu --help``
- ``./ovh-ca --help``
- ``./runabove-ca --help``

Provided that necessary keys were installed.

Examples
========

Show you personal informations
------------------------------

.. code::

  >>> ./ovh-eu me # this is a shotcut for './ovh-eu me list'
  --------------------------------------  ----------------------
  Sex                                     male
  Legalform                               individual
  Ovh company                             ovh
  City                                    Paris
  Zip                                     75001
  Area
  Organisation
  State                                   complete
  Company national identification number  None
  Email                                   realmail@leading-provider.com
  Vat
  Spare email                             None
  Fax
  Firstname                               Jean-Tiare
  Phone                                   +33.123456789
  Birth city
  Address                                 12, Open Source Street
  Corporation type
  National identification number          None
  Name                                    LE BIGOT
  Language                                fr_FR
  Ovh subsidiary                          FR
  Country                                 FR
  Nichandle                               ab12345-ovh
  Birth day
  --------------------------------------  ----------------------

Get the list of available subcommands / actions for 'me'
--------------------------------------------------------

.. code::

  >>> ./ovh-eu me --help
  Method 'me': Details about your OVH identifier

  Actions:
      update  Alter this object properties
      show    Get this object properties (default)

  Methods:
      refund                List the billing.Refund objects
      ovh-account           List the billing.OvhAccount objects
      access-restriction    
      password-recover      Request a password recover
      bill                  List the billing.Bill objects
      payment-mean          
      ip-organisation       List the nichandle.Ipv4Org objects
      order                 List the billing.Order objects
      subscription          List the nichandle.Subscription objects
      api                   
      ipxe-script           List the nichandle.ipxe objects
      installation-template List the dedicated.installationTemplate.Templates objects
      ssh-key               List the nichandle.sshKey objects
      change-password       changePassword operations
      agreements            List the agreements.ContractAgreement objects

List IPs associated with an XDSL line:
--------------------------------------

.. code::

  >>> ./ovh-eu xdsl xdsl-ab12345-1 ips
  ID                     Reverse             Ip                       Range  Version    Dns list                                         Monitoring enabled
  ---------------------  ------------------  ---------------------  -------  ---------  -----------------------------------------------  --------------------
  2001:41d0:xxxx:xx00::                      2001:41d0:xxxx:xx00::       56  v6         2001:41 d0:1:e2 b8::1, 2001:41 d0:3:163::1       False
  109.190.xxx.xxx        home.my-domain.fr.  109.190.xxx.xxx             32  v4         91.121.161.184, 91.121.164.227, 188.165.197.144  True

Manage your applications / credentials
--------------------------------------

List declared applications:

.. code::

  >>> ./ovh-eu me api application
  status    applicationKey      applicationId  name          description
  --------  ----------------  ---------------  ------------  -----------------------
  active    xxxxxxxxxxxxxxxx             1234  batchDomains  batch domain operations
  active    yyyyyyyyyyyyyyyy             5678  console       console

Delete an application: (all users will loose access)

.. code::

  >>> ./ovh-eu me api application 1234 delete
  Success
  >>> ./ovh-eu me api application 1234 delete
  The requested object (id = 1234) does not exist

The same logic works exactly identically for "credentials". Credentials are
access granted to your account to third party applications.

Get daily xdsl DL BandWidth statistics:
---------------------------------------

.. code::

  >>> ./ovh-eu xdsl xdsl-lj75593-1 statistics --period daily --type traffic:download
  19/09/2014 16:10 0.026 Mbps | 
  19/09/2014 16:50 0.027 Mbps | 
  19/09/2014 17:30 0.027 Mbps | 
  19/09/2014 18:10 0.026 Mbps | 
  19/09/2014 18:50 0.026 Mbps | 
  19/09/2014 19:30 0.022 Mbps | 
  19/09/2014 20:10 0.021 Mbps | 
  19/09/2014 20:50 0.021 Mbps | 
  19/09/2014 21:30 0.021 Mbps | 
  19/09/2014 22:10 0.021 Mbps | 
  19/09/2014 22:50 0.021 Mbps | 
  19/09/2014 23:30 0.021 Mbps | 
  20/09/2014 00:10 0.480 Mbps | ...............
  20/09/2014 00:50 0.308 Mbps | .........
  20/09/2014 01:30 0.477 Mbps | ...............
  20/09/2014 02:10 0.029 Mbps | 
  20/09/2014 02:50 0.051 Mbps | .
  20/09/2014 03:30 0.036 Mbps | .
  20/09/2014 04:10 0.022 Mbps | 
  20/09/2014 04:50 0.023 Mbps | 
  20/09/2014 05:30 0.023 Mbps | 
  20/09/2014 06:10 0.025 Mbps | 
  20/09/2014 06:50 0.027 Mbps | 
  20/09/2014 07:30 0.030 Mbps | 
  20/09/2014 08:10 0.030 Mbps | 
  20/09/2014 08:50 0.040 Mbps | .
  20/09/2014 09:30 0.032 Mbps | .
  20/09/2014 10:10 0.161 Mbps | .....
  20/09/2014 10:50 0.484 Mbps | ...............
  20/09/2014 11:30 0.550 Mbps | .................
  20/09/2014 12:10 0.559 Mbps | .................
  20/09/2014 12:50 0.303 Mbps | .........
  20/09/2014 13:30 0.858 Mbps | ...........................
  20/09/2014 14:10 0.854 Mbps | ..........................
  20/09/2014 14:50 1.011 Mbps | ...............................
  20/09/2014 15:30 0.889 Mbps | ............................
  20/09/2014 16:10 0.125 Mbps | ...
  20/09/2014 16:50 0.605 Mbps | ...................
  20/09/2014 17:30 0.924 Mbps | .............................
  20/09/2014 18:10 0.769 Mbps | ........................
  20/09/2014 18:50 0.842 Mbps | ..........................
  20/09/2014 19:30 0.733 Mbps | .......................
  20/09/2014 20:10 0.942 Mbps | .............................
  20/09/2014 20:50 0.780 Mbps | ........................
  20/09/2014 21:30 0.607 Mbps | ...................
  20/09/2014 22:10 0.641 Mbps | ....................
  20/09/2014 22:50 0.867 Mbps | ...........................
  20/09/2014 23:25 0.896 Mbps | ............................

... and so on. Feel free to explore using the 'console' (see below) or the almighty '--help'!

Supported APIs
==============

OVH Europe
----------

- **Documentation**: https://eu.api.ovh.com/
- **Community support**: api-subscribe@ml.ovh.net
- **Console**: https://eu.api.ovh.com/console
- **Create application credentials**: https://eu.api.ovh.com/createApp/
- **Create script credentials** (all keys at once): https://eu.api.ovh.com/createToken/

OVH North America
-----------------

- **Documentation**: https://ca.api.ovh.com/
- **Community support**: api-subscribe@ml.ovh.net
- **Console**: https://ca.api.ovh.com/console
- **Create application credentials**: https://ca.api.ovh.com/createApp/
- **Create script credentials** (all keys at once): https://ca.api.ovh.com/createToken/

So you Start Europe
-------------------

- **Documentation**: https://eu.api.soyoustart.com/
- **Community support**: api-subscribe@ml.ovh.net
- **Console**: https://eu.api.soyoustart.com/console/
- **Create application credentials**: https://eu.api.soyoustart.com/createApp/
- **Create script credentials** (all keys at once): https://eu.api.soyoustart.com/createToken/

So you Start North America
--------------------------

- **Documentation**: https://ca.api.soyoustart.com/
- **Community support**: api-subscribe@ml.ovh.net
- **Console**: https://ca.api.soyoustart.com/console/
- **Create application credentials**: https://ca.api.soyoustart.com/createApp/
- **Create script credentials** (all keys at once): https://ca.api.soyoustart.com/createToken/

Kimsufi Europe
--------------

- **Documentation**: https://eu.api.kimsufi.com/
- **Community support**: api-subscribe@ml.ovh.net
- **Console**: https://eu.api.kimsufi.com/console/
- **Create application credentials**: https://eu.api.kimsufi.com/createApp/
- **Create script credentials** (all keys at once): https://eu.api.kimsufi.com/createToken/

Kimsufi North America
---------------------

- **Documentation**: https://ca.api.kimsufi.com/
- **Community support**: api-subscribe@ml.ovh.net
- **Console**: https://ca.api.kimsufi.com/console/
- **Create application credentials**: https://ca.api.kimsufi.com/createApp/
- **Create script credentials** (all keys at once): https://ca.api.kimsufi.com/createToken/

Runabove
--------

- **Community support**: https://community.runabove.com/
- **Console**: https://api.runabove.com/console/
- **Create application credentials**: https://api.runabove.com/createApp/
- **High level SDK**: https://github.com/runabove/python-runabove
- **Create script credentials** (all keys at once): https://api.runabove.com/createToken/

Related links
=============

- **OVH official SDK**: https://github.com/ovh/python-ovh
- **contribute**: https://github.com/yadutaf/ovh-cli
- **Report bugs**: https://github.com/yadutaf/ovh-cli/issues

