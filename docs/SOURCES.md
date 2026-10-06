# Official references and third-party notices

The integration targets Apache Guacamole **1.6.0** and Django **5.2**.
The two Guacamole containers and the browser library must remain version-aligned.

- Guacamole encrypted JSON authentication:
  https://guacamole.apache.org/doc/1.6.0/gug/json-auth.html
- Guacamole Docker installation:
  https://guacamole.apache.org/doc/1.6.0/gug/guacamole-docker.html
- Guacamole connection parameters:
  https://guacamole.apache.org/doc/1.6.0/gug/configuring-guacamole.html
- Guacamole custom application guide:
  https://guacamole.apache.org/doc/1.6.0/gug/writing-you-own-guacamole-app.html
- Official client artifact used for static/vendor/all.min.js:
  https://repo.maven.apache.org/maven2/org/apache/guacamole/guacamole-common-js/1.6.0/guacamole-common-js-1.6.0.zip
- Guacamole source (token and tunnel adapter reference):
  https://github.com/apache/guacamole-client/tree/1.6.0
- Django deployment checklist:
  https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- Docker Desktop Windows setup:
  https://docs.docker.com/desktop/setup/install/windows-install/
- Microsoft Remote Desktop host setup and edition requirements:
  https://learn.microsoft.com/windows-server/remote/remote-desktop-services/remotepc/remote-desktop-allow-access
- VirtualBox documentation:
  https://www.virtualbox.org/manual/

The vendored Guacamole JavaScript is Apache Software Foundation software under
Apache License 2.0. Its upstream LICENSE and NOTICE are retained in static/vendor.
It is a dependency, not code authored by this project's team. Source comments
within the library are retained. Preserve those notices when redistributing it.
The original AnyAccess CSS optionally loads DM Sans from Google Fonts, with a
system-font fallback if that request is unavailable.
